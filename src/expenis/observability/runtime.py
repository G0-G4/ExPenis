import asyncio
import json
import os
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Callable, Iterator

import httpx
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.logs.v1.logs_pb2 import (
    LogRecord,
    ResourceLogs,
    ScopeLogs,
    SeverityNumber,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import SpanKind, Status, StatusCode
from starlette.routing import BaseRoute
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    ProcessCollector,
)

from .safety import EVENT_CODES, fingerprint, request_id, request_scope, route_name
from .settings import TelemetrySettings
from ..version import __version__


class QueueSpanProcessor(SpanProcessor):
    def __init__(self, owner: "Telemetry") -> None:
        self.owner = owner

    def on_start(self, span: Span, parent_context=None) -> None:
        pass

    def on_end(self, span: ReadableSpan) -> None:
        self.owner.enqueue("traces", encode_spans([span]).SerializeToString())


class Telemetry:
    def __init__(self, settings: TelemetrySettings) -> None:
        self.settings = settings
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "expenis_http_requests",
            "Business HTTP responses",
            ["environment", "route", "method", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "expenis_http_request_duration_seconds",
            "Business HTTP duration",
            ["environment", "route", "method"],
            registry=self.registry,
        )
        self.inflight = Gauge(
            "expenis_http_inflight", "Active business requests", registry=self.registry
        )
        self.dependency = Histogram(
            "expenis_dependency_duration_seconds",
            "Awaited dependency duration",
            ["operation", "outcome"],
            registry=self.registry,
        )
        self.delivery = Counter(
            "expenis_telemetry_records",
            "Delivery records",
            ["result"],
            registry=self.registry,
        )
        self.ready = Gauge(
            "expenis_ready", "Last database readiness result", registry=self.registry
        )
        self.client_requests = Counter(
            "expenis_client_http_requests",
            "Accepted sampled client attempts (not active clients)",
            ["environment", "platform", "operation", "status"],
            registry=self.registry,
        )
        self.client_latency = Histogram(
            "expenis_client_operation_duration_seconds",
            "Accepted sampled client operation duration",
            ["environment", "platform", "operation"],
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1,
                2.5,
                5,
                10,
                30,
                60,
                300,
                900,
            ),
            registry=self.registry,
        )
        self.client_errors = Counter(
            "expenis_client_errors",
            "Distinct accepted technical client errors",
            ["environment", "platform", "code"],
            registry=self.registry,
        )
        ProcessCollector(registry=self.registry)
        self.provider = TracerProvider(
            resource=SDKResource(
                {
                    "service.name": "expenis-backend",
                    "service.version": __version__,
                    "environment": settings.environment,
                    "origin": "server",
                }
            ),
            sampler=TraceIdRatioBased(settings.sample_rate),
            shutdown_on_exit=False,
        )
        self.provider.add_span_processor(QueueSpanProcessor(self))
        self.tracer = self.provider.get_tracer("expenis")
        self.queue: deque[tuple[str, bytes]] = deque()
        self.bytes = 0
        self.lock = threading.Lock()
        self.worker: asyncio.Task | None = None
        self.client: httpx.AsyncClient | None = None
        self.dedup: dict[tuple[str, str], float] = {}
        self.sources: dict[str, tuple[float, float]] = {}
        self.global_bucket = (float(settings.global_burst), time.monotonic())
        self.admission_enabled = True
        self.ingest_inflight = 0

    def initialize_http_metrics(self, routes: list[BaseRoute]) -> None:
        pairs = {
            (getattr(route, "path", "unknown"), method)
            for route in routes
            for method in getattr(route, "methods", set())
            if getattr(route, "path", "")
            not in {"/api/telemetry", "/api/health/ready", "/metrics"}
        }
        pairs.update(
            ("unknown", method)
            for method in (
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "PATCH",
                "HEAD",
                "OPTIONS",
                "OTHER",
            )
        )
        for path, method in pairs:
            for status in ("1xx", "2xx", "3xx", "4xx", "5xx"):
                self.requests.labels(self.settings.environment, path, method, status)
            self.latency.labels(self.settings.environment, path, method)
        for result in (
            "accepted",
            "rejected",
            "dropped",
            "exported",
            "export_failed",
            "sampled_out",
        ):
            self.delivery.labels(result)

    def accepting(self) -> bool:
        return self.admission_enabled and not os.path.exists(self.settings.paused_file)

    def enqueue(self, kind: str, payload: bytes) -> bool:
        if not self.settings.enabled:
            return False
        with self.lock:
            if len(payload) > self.settings.queue_bytes or not self.accepting():
                self.delivery.labels("dropped").inc()
                return False
            while self.queue and (
                self.bytes + len(payload) > self.settings.queue_bytes
                or len(self.queue) >= self.settings.queue_records
            ):
                _, removed = self.queue.popleft()
                self.bytes -= len(removed)
                self.delivery.labels("dropped").inc()
            self.queue.append((kind, payload))
            self.bytes += len(payload)
        return True

    def event(
        self,
        code: str,
        *,
        frames=None,
        platform: str | None = None,
        version: str | None = None,
        event_id: str = "",
        trace_id: str = "",
        span_id: str = "",
        req_id: str = "",
        severity: int = 9,
    ) -> dict:
        code = code if code in EVENT_CODES else "application_event"
        scope = request_scope.get()
        route = (
            getattr(scope.get("route"), "path", "unknown")
            if scope
            else route_name.get()
        )
        attrs = {"code": code, "request_id": req_id or request_id.get(), "route": route}
        if frames:
            attrs["frames"] = json.dumps(frames, separators=(",", ":"))
        attrs["fingerprint"] = fingerprint(code, frames or [])
        if version:
            attrs["app_version"] = version
        if event_id:
            attrs["event_id"] = event_id
        context = trace.get_current_span().get_span_context()
        trace_id = trace_id or (
            format(context.trace_id, "032x") if context.is_valid else ""
        )
        span_id = span_id or (
            format(context.span_id, "016x") if context.is_valid else ""
        )
        attrs.update({"trace_id": trace_id, "span_id": span_id})
        resource = {
            "service.name": "expenis-client" if platform else "expenis-backend",
            "service.version": version or __version__,
            "environment": self.settings.environment,
            "origin": "client" if platform else "server",
        }
        if platform:
            resource["platform"] = platform
        record = LogRecord(
            time_unix_nano=time.time_ns(),
            observed_time_unix_nano=time.time_ns(),
            severity_number=SeverityNumber.Value(
                {
                    5: "SEVERITY_NUMBER_DEBUG",
                    9: "SEVERITY_NUMBER_INFO",
                    13: "SEVERITY_NUMBER_WARN",
                    17: "SEVERITY_NUMBER_ERROR",
                    21: "SEVERITY_NUMBER_FATAL",
                }.get(severity, "SEVERITY_NUMBER_INFO")
            ),
            body=AnyValue(string_value=code),
            trace_id=bytes.fromhex(trace_id) if trace_id else b"",
            span_id=bytes.fromhex(span_id) if span_id else b"",
            attributes=[
                KeyValue(key=k, value=AnyValue(string_value=v))
                for k, v in attrs.items()
                if v
            ],
        )
        payload = ExportLogsServiceRequest(
            resource_logs=[
                ResourceLogs(
                    resource=Resource(
                        attributes=[
                            KeyValue(key=k, value=AnyValue(string_value=v))
                            for k, v in resource.items()
                        ]
                    ),
                    scope_logs=[ScopeLogs(log_records=[record])],
                )
            ]
        ).SerializeToString()
        self.enqueue("logs", payload)
        return {
            "timestamp": time.time(),
            "severity": {
                5: "debug",
                9: "info",
                13: "warning",
                17: "error",
                21: "fatal",
            }.get(severity, "info"),
            "code": code,
            **resource,
            **attrs,
        }

    async def start(self) -> None:
        if self.settings.enabled and self.worker is None:
            self.client = httpx.AsyncClient(
                timeout=self.settings.timeout, trust_env=False
            )
            self.worker = asyncio.create_task(self._deliver())

    async def stop(self) -> None:
        if self.worker:
            self.worker.cancel()
            try:
                await self.worker
            except asyncio.CancelledError:
                pass
            self.worker = None
        if self.client:
            await self.client.aclose()
            self.client = None
        with self.lock:
            self.delivery.labels("dropped").inc(len(self.queue))
            self.queue.clear()
            self.bytes = 0

    async def _deliver(self) -> None:
        while True:
            item = None
            with self.lock:
                if self.queue:
                    item = self.queue.popleft()
                    self.bytes -= len(item[1])
            if item is None:
                await asyncio.sleep(0.1)
                continue
            kind, data = item
            for attempt in range(3):
                try:
                    response = await self.client.post(  # type: ignore[union-attr]
                        f"{self.settings.endpoint}/v1/{kind}",
                        content=data,
                        headers={"Content-Type": "application/x-protobuf"},
                    )
                    if response.is_success:
                        self.delivery.labels("exported").inc()
                        break
                    if response.status_code not in {429, 502, 503, 504}:
                        self.delivery.labels("export_failed").inc()
                        break
                except httpx.HTTPError:
                    pass
                if attempt == 2:
                    self.delivery.labels("export_failed").inc()
                else:
                    await asyncio.sleep(0.1 * (attempt + 1))


telemetry = Telemetry(TelemetrySettings.from_env())


@contextmanager
def operation(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    *,
    failed: Callable[[], bool] | None = None,
) -> Iterator[trace.Span | None]:
    owner = telemetry
    if (
        not owner.settings.enabled
        or not trace.get_current_span().get_span_context().is_valid
    ):
        yield None
        return
    start = time.monotonic()
    outcome = "ok"
    with owner.tracer.start_as_current_span(
        name, kind=kind, record_exception=False, set_status_on_exception=False
    ) as span:
        span.set_attribute("operation", name)
        try:
            yield span
        except BaseException:
            outcome = "error"
            span.set_status(Status(StatusCode.ERROR))
            raise
        finally:
            if failed is not None and failed():
                outcome = "error"
            owner.dependency.labels(name, outcome).observe(time.monotonic() - start)
