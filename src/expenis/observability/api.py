import asyncio
import ipaddress
import json
import time
from pathlib import Path

from opentelemetry.context import Context
from opentelemetry.trace import SpanKind
from fastapi import APIRouter, Request, Response
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span,
    Status,
)
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import ValidationError
from starlette.responses import JSONResponse

from . import runtime
from .dto import (
    ErrorRecord,
    ReadinessResponse,
    TelemetryAcceptedResponse,
    TelemetryBatch,
)

router = APIRouter()


def _error(code: str, status: int) -> JSONResponse:
    runtime.telemetry.delivery.labels("rejected").inc()
    headers = {"Retry-After": "5"} if status in {429, 503} else {}
    return JSONResponse({"code": code}, status_code=status, headers=headers)


def _take(
    bucket: tuple[float, float], rate: int, burst: int, now: float
) -> tuple[bool, tuple[float, float]]:
    tokens = min(float(burst), bucket[0] + max(0.0, now - bucket[1]) * rate / 60)
    allowed = tokens >= 1
    return allowed, (tokens - 1 if allowed else tokens, now)


@router.post(
    "/api/telemetry",
    operation_id="submitTelemetry",
    tags=["observability"],
    summary="Отправить техническую телеметрию",
    description="Публичный bounded JSON ingestion без JWT. 64 KiB/batch, 50 records, extra fields запрещены. 202 означает очередь, не сохранение. Повторы 429/503 ограничены Retry-After.",
    response_model=TelemetryAcceptedResponse,
    status_code=202,
    responses={
        s: {"description": d}
        for s, d in {
            204: "Сбор выключен",
            400: "Неверный JSON",
            408: "Таймаут чтения batch",
            413: "Превышен размер",
            415: "Неподдерживаемый media type",
            422: "Неверная схема",
            429: "Rate limit; Retry-After",
            503: "Недостаточно capacity; Retry-After",
        }.items()
    },
    openapi_extra={
        "security": [],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/TelemetryBatch"}
                }
            },
        },
    },
)
async def submit_telemetry(request: Request) -> Response:
    owner = runtime.telemetry
    if not owner.settings.enabled:
        return Response(status_code=204)
    if request.headers.get("content-type", "").split(";", 1)[
        0
    ].strip() != "application/json" or request.headers.get("content-encoding"):
        return _error("unsupported_media", 415)
    now = time.monotonic()
    owner.sources = {k: v for k, v in owner.sources.items() if now - v[1] < 120}
    source = request.client.host if request.client else "unknown"
    # Only the loopback proxy may supply the end client's address; use Caddy's
    # last-hop header value, never a caller-prepended entry.
    if source in {"127.0.0.1", "::1"}:
        candidate = request.headers.get("x-forwarded-for", "").split(",")[-1].strip()
        try:
            source = str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    if (
        source not in owner.sources
        and len(owner.sources) >= owner.settings.cache_records
    ):
        return _error("capacity_exhausted", 503)
    allowed, source_bucket = _take(
        owner.sources.get(source, (float(owner.settings.source_burst), now)),
        owner.settings.source_per_minute,
        owner.settings.source_burst,
        now,
    )
    if not allowed:
        owner.sources[source] = source_bucket
        return _error("rate_limited", 429)
    allowed, owner.global_bucket = _take(
        owner.global_bucket,
        owner.settings.global_per_minute,
        owner.settings.global_burst,
        now,
    )
    if not allowed:
        return _error("rate_limited", 429)
    owner.sources[source] = source_bucket
    if owner.ingest_inflight >= 16:
        return _error("capacity_exhausted", 503)
    owner.ingest_inflight += 1
    body = bytearray()
    try:
        async with asyncio.timeout(2):
            async for chunk in request.stream():
                if len(body) + len(chunk) > owner.settings.body_bytes:
                    return _error("body_too_large", 413)
                body.extend(chunk)
    except TimeoutError:
        return _error("body_timeout", 408)
    finally:
        owner.ingest_inflight -= 1
    try:
        parsed = json.loads(body)
    except (ValueError, UnicodeError):
        return _error("invalid_json", 400)
    try:
        batch = TelemetryBatch.model_validate(parsed)
    except ValidationError:
        return _error("invalid_schema", 422)
    owner.dedup = {k: v for k, v in owner.dedup.items() if now - v < 900}
    records = {
        str(r.event_id): r
        for r in batch.records
        if (batch.platform, str(r.event_id)) not in owner.dedup
    }
    if (
        len(owner.dedup) + len(records) > owner.settings.cache_records
        or not owner.accepting()
    ):
        return _error("capacity_exhausted", 503)
    accepted = 0
    for key, record in records.items():
        if isinstance(record, ErrorRecord):
            owner.client_errors.labels(
                owner.settings.environment, batch.platform, record.code
            ).inc()
            owner.event(
                record.code,
                frames=[f.model_dump() for f in record.frames],
                platform=batch.platform,
                version=batch.app_version,
                event_id=key,
                trace_id=record.trace_id or "",
                span_id=record.span_id or "",
                req_id=record.request_id or "",
                severity=17,
            )
        else:
            if not owner.provider.sampler.should_sample(
                Context(),
                int(record.trace_id, 16),
                "client",
                kind=SpanKind.CLIENT,
            ).decision.is_sampled():
                owner.delivery.labels("sampled_out").inc()
                owner.dedup[(batch.platform, key)] = now
                continue
            if record.parent_span_id:
                status_class = (
                    "network" if record.status == 0 else f"{record.status // 100}xx"
                )
                owner.client_requests.labels(
                    owner.settings.environment,
                    batch.platform,
                    record.operation,
                    status_class,
                ).inc()
            else:
                owner.client_latency.labels(
                    owner.settings.environment, batch.platform, record.operation
                ).observe((record.end_ns - record.start_ns) / 1e9)
            resource = {
                "service.name": "expenis-client",
                "service.version": batch.app_version,
                "platform": batch.platform,
                "environment": owner.settings.environment,
                "origin": "client",
            }
            span = Span(
                trace_id=bytes.fromhex(record.trace_id),
                span_id=bytes.fromhex(record.span_id),
                parent_span_id=bytes.fromhex(record.parent_span_id)
                if record.parent_span_id
                else b"",
                links=[
                    Span.Link(
                        trace_id=bytes.fromhex(link.trace_id),
                        span_id=bytes.fromhex(link.span_id),
                    )
                    for link in record.links
                ],
                name=record.operation,
                kind=Span.SPAN_KIND_CLIENT,
                start_time_unix_nano=record.start_ns,
                end_time_unix_nano=record.end_ns,
                status=Status(
                    code=Status.STATUS_CODE_ERROR
                    if record.outcome == "error"
                    else Status.STATUS_CODE_UNSET
                ),
                attributes=[
                    KeyValue(key="status", value=AnyValue(int_value=record.status))
                ],
            )
            owner.enqueue(
                "traces",
                ExportTraceServiceRequest(
                    resource_spans=[
                        ResourceSpans(
                            resource=Resource(
                                attributes=[
                                    KeyValue(key=k, value=AnyValue(string_value=v))
                                    for k, v in resource.items()
                                ]
                            ),
                            scope_spans=[ScopeSpans(spans=[span])],
                        )
                    ]
                ).SerializeToString(),
            )
        owner.dedup[(batch.platform, key)] = now
        accepted += 1
    owner.delivery.labels("accepted").inc(accepted)
    return JSONResponse({"accepted": accepted}, status_code=202)


@router.get(
    "/api/health/ready",
    operation_id="getReadiness",
    tags=["observability"],
    summary="Проверить готовность приложения и SQLite",
    description="Bounded read существующей таблицы. Не зависит от exporter, не меняет данные, не раскрывает внутренние ошибки.",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "SQLite недоступна"}},
    openapi_extra={"security": []},
)
async def readiness() -> JSONResponse:
    from ..core.models import User, db

    ready = False
    try:
        if not Path(db.database).is_file():
            raise FileNotFoundError
        async with asyncio.timeout(1):
            # A missing DB/schema must fail, including when sqlite could create a file.
            await db.run(lambda: User.select(User.id).limit(1).tuples().execute())
            ready = True
    except Exception:
        pass
    runtime.telemetry.ready.set(int(ready))
    return JSONResponse(
        {"status": "ready" if ready else "not_ready"}, status_code=200 if ready else 503
    )


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
        return Response(status_code=404)
    if not runtime.telemetry.accepting():
        return Response(status_code=503)
    return Response(
        generate_latest(runtime.telemetry.registry),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
