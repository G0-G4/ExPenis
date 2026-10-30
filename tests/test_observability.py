import asyncio
import json
import logging
import time
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.expenis.core.logging_config import SafeFormatter
from src.expenis.core.models import User, db
from src.expenis.observability import runtime
from src.expenis.observability.runtime import Telemetry
from src.expenis.observability.settings import TelemetrySettings
from src.expenis.server.application import app


@pytest.fixture
async def observed(monkeypatch, request):
    owner = Telemetry(
        TelemetrySettings(
            enabled=True,
            environment="test",
            source_burst=100,
            global_burst=200,
            sample_rate=getattr(request, "param", 1),
        )
    )
    monkeypatch.setattr(runtime, "telemetry", owner)
    yield owner
    await owner.stop()


@pytest.fixture
async def client(observed):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=app, raise_app_exceptions=False, client=("10.0.0.2", 1234)
        ),
        base_url="http://test",
    ) as client:
        yield client


def batch(**record):
    return {
        "schema_version": 1,
        "platform": "web",
        "app_version": "1.1.0+9",
        "records": [
            {
                "kind": "error",
                "event_id": str(uuid4()),
                "timestamp": datetime.now(UTC).isoformat(),
                "code": "client_operation",
                **record,
            },
        ],
    }


@pytest.mark.asyncio
async def test_ingestion_before_login_and_retry_counted_once(client, observed):
    data = batch()
    first = await client.post("/api/telemetry", json=data)
    second = await client.post("/api/telemetry", json=data)
    assert first.status_code == 202 and first.json() == {"accepted": 1}
    assert second.json() == {"accepted": 0}
    assert len(observed.queue) == 1
    message = ExportLogsServiceRequest.FromString(observed.queue[0][1])
    record = message.resource_logs[0].scope_logs[0].log_records[0]
    assert record.body.string_value == "client_operation"
    assert any(a.key == "event_id" for a in record.attributes)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"code": "secret@example.com"},
        {"body": "sensitive"},
        {"trace_id": "0" * 32},
        {"timestamp": "2020-01-01T00:00:00Z"},
        {"frames": [{"file": "/private/token", "function": "oops", "line": 1}]},
    ],
)
async def test_rejected_inputs_never_echo_or_export(client, observed, change):
    response = await client.post("/api/telemetry", json=batch(**change))
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_schema"}
    assert not observed.queue


@pytest.mark.asyncio
async def test_ingestion_body_media_json_and_disabled(client, observed):
    response = await client.post(
        "/api/telemetry",
        content=b"x" * 65537,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert (
        await client.post(
            "/api/telemetry", content="{", headers={"content-type": "application/json"}
        )
    ).status_code == 400
    assert (await client.post("/api/telemetry", content="hello")).status_code == 415
    observed.settings = replace(observed.settings, enabled=False)
    assert (await client.post("/api/telemetry", json=batch())).status_code == 204
    assert not observed.queue


@pytest.mark.asyncio
async def test_global_source_capacity_and_retry_after(client, observed):
    observed.settings = replace(observed.settings, source_burst=1, source_per_minute=0)
    assert (await client.post("/api/telemetry", json=batch())).status_code == 202
    rejected = await client.post(
        "/api/telemetry", json=batch(), headers={"x-forwarded-for": "1.2.3.4"}
    )
    assert rejected.status_code == 429
    assert rejected.headers["retry-after"] == "5"
    assert (
        len(observed.sources) == 1
    )  # spoofing headers from a non-proxy cannot bypass it
    observed.settings = replace(
        observed.settings, source_burst=100, source_per_minute=100, cache_records=1
    )
    observed.sources.clear()
    rejected = await client.post("/api/telemetry", json=batch())
    assert rejected.status_code == 503


@pytest.mark.asyncio
async def test_completed_client_span_preserves_context(client, observed):
    now = time.time_ns()
    data = batch()
    data["records"] = [
        {
            "kind": "span",
            "event_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "trace_id": "1" * 32,
            "span_id": "2" * 16,
            "parent_span_id": "3" * 16,
            "links": [{"trace_id": "4" * 32, "span_id": "5" * 16}],
            "operation": "api",
            "start_ns": now - 1000000,
            "end_ns": now,
            "status": 200,
            "outcome": "ok",
        }
    ]
    response = await client.post("/api/telemetry", json=data)
    assert response.status_code == 202
    trace = ExportTraceServiceRequest.FromString(observed.queue[0][1])
    span = trace.resource_spans[0].scope_spans[0].spans[0]
    assert span.trace_id.hex() == "1" * 32
    assert span.span_id.hex() == "2" * 16
    assert span.parent_span_id.hex() == "3" * 16
    assert span.links[0].trace_id.hex() == "4" * 32


@pytest.mark.asyncio
async def test_readiness_reads_existing_schema_not_exporter(
    client, observed, monkeypatch
):
    assert (await client.get("/api/health/ready")).json() == {"status": "ready"}

    async def fail(*args, **kwargs):
        raise RuntimeError("private/database/path secret")

    monkeypatch.setattr(db, "run", fail)
    response = await client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert not observed.queue


@pytest.mark.asyncio
async def test_server_and_async_db_spans_do_not_capture_sql(client, observed):
    exporter = InMemorySpanExporter()
    observed.provider.add_span_processor(SimpleSpanProcessor(exporter))
    with observed.tracer.start_as_current_span("api"):
        await db.run(
            lambda: User.get_or_none(User.username == "private-email@example.com")
        )
    spans = exporter.get_finished_spans()
    child = next(s for s in spans if s.name == "sqlite.read")
    parent = next(s for s in spans if s.name == "api")
    assert child.parent.span_id == parent.context.span_id
    assert "private-email" not in str([s.attributes for s in spans])
    assert "SELECT" not in str([s.attributes for s in spans])
    response = await client.get(
        "/api/currency/codes",
        headers={"traceparent": "00-" + "1" * 32 + "-" + "2" * 16 + "-00"},
    )
    assert response.status_code == 200
    assert len(response.headers["x-request-id"]) == 32
    server = exporter.get_finished_spans()[-1]
    assert server.context.trace_id == int("1" * 32, 16)
    assert server.parent.span_id == int("2" * 16, 16)
    assert dict(server.attributes)["route"] == "/api/currency/codes"


@pytest.mark.asyncio
async def test_trace_sampling_and_health_exclusion(client, observed):
    await client.get("/api/health/ready")
    await client.post("/api/telemetry", json=batch())
    assert not any(kind == "traces" for kind, _ in observed.queue)
    observed.queue.clear()
    observed.bytes = 0
    requests = await asyncio.gather(
        *[
            client.get("/api/currency/codes", headers={"traceparent": "broken"})
            for _ in range(3)
        ]
    )
    assert len({r.headers["x-request-id"] for r in requests}) == 3
    assert observed.inflight._value.get() == 0


def test_logging_sanitizes_file_console_and_exception(observed):
    record = logging.LogRecord(
        "src.expenis",
        logging.ERROR,
        __file__,
        1,
        "secret=%s",
        ("password@example.com",),
        None,
    )
    formatter = SafeFormatter()
    rendered = formatter.format(record)
    assert "password" not in rendered and "secret=" not in rendered
    assert json.loads(rendered)["code"] == "application_event"
    assert len(observed.queue) == 1
    assert formatter.format(record) == rendered
    assert len(observed.queue) == 1


@pytest.mark.asyncio
async def test_export_failure_is_bounded_and_does_not_recurse(observed):
    observed.settings = replace(observed.settings, queue_bytes=16, queue_records=2)
    assert observed.enqueue("logs", b"first")
    assert observed.enqueue("logs", b"second")
    assert observed.enqueue("logs", b"third")
    assert list(observed.queue) == [("logs", b"second"), ("logs", b"third")]
    assert observed.bytes <= 16
    assert not observed.enqueue("logs", b"x" * 17)

    async def unavailable(request):
        raise httpx.ConnectError("private-url-key", request=request)

    observed.client = httpx.AsyncClient(transport=httpx.MockTransport(unavailable))
    observed.worker = asyncio.create_task(observed._deliver())
    await asyncio.sleep(0.8)
    assert observed.bytes <= 16 and len(observed.queue) <= 2
    assert observed.delivery.labels("export_failed")._value.get() >= 1
    assert not any(b"private" in data for _, data in observed.queue)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 302, 429, 503])
@pytest.mark.parametrize("observed", [0, 1], indirect=True)
async def test_provider_outcomes_and_metrics_send_no_context(observed, status):
    from src.expenis.core.service.exchage_rate_service import _observed_get

    sampling = observed.settings.sample_rate
    exporter = InMemorySpanExporter()
    observed.provider.add_span_processor(SimpleSpanProcessor(exporter))

    async def respond(request):
        assert "traceparent" not in request.headers and "baggage" not in request.headers
        return httpx.Response(status)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with observed.tracer.start_as_current_span("api"):
            await _observed_get(
                client,
                "https://www.alphavantage.co/query",
                params={"apikey": "canary-private"},
            )
    outcome = "ok" if 200 <= status < 300 else "error"
    assert (
        observed.registry.get_sample_value(
            "expenis_dependency_duration_seconds_count",
            {"operation": "http.alphavantage", "outcome": outcome},
        )
        == 1
    )
    if sampling:
        span = exporter.get_finished_spans()[0]
        assert span.name == "http.alphavantage"
        assert span.status.status_code.name == ("UNSET" if outcome == "ok" else "ERROR")
        assert "canary-private" not in str(span.attributes)
    else:
        assert not exporter.get_finished_spans()


def test_real_logging_sinks_do_not_interpolate_private_values(
    observed, monkeypatch, tmp_path
):
    from src.expenis.core import logging_config

    monkeypatch.setattr(logging_config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(logging_config, "LOG_FILE", tmp_path / "test.log")
    original_handlers = logging.root.handlers[:]
    try:
        logging_config.setup_logging()
        logger = logging.getLogger("src.expenis.core.service.auth_service")
        logger.warning("auth_bad_password", "private-secret@example.com")
        logger.error("token=%s amount=%s", "private-secret@example.com", "987654")
        for handler in logging.root.handlers:
            handler.flush()
        contents = (tmp_path / "test.log").read_text()
        assert "auth_bad_password" in contents
        assert "private-secret" not in contents and "987654" not in contents
    finally:
        for handler in logging.root.handlers:
            handler.close()
        logging.root.handlers = original_handlers


@pytest.mark.asyncio
async def test_global_limit_and_metrics_are_isolated(client, observed):
    observed.global_bucket = (0.0, time.monotonic())
    assert (await client.post("/api/telemetry", json=batch())).status_code == 429
    await client.get("/not-a-route/private-email@example.com")
    assert (await client.get("/metrics")).status_code == 404
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 100)),
        base_url="http://test",
    ) as local:
        response = await local.get("/metrics")
        assert response.status_code == 200
        assert 'route="unknown"' in response.text
        assert "private-email" not in response.text
        observed.admission_enabled = False
        assert (await local.get("/metrics")).status_code == 503


@pytest.mark.asyncio
async def test_readiness_timeout_is_bounded(client, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(10)

    monkeypatch.setattr(db, "run", slow)
    start = time.monotonic()
    assert (await client.get("/api/health/ready")).status_code == 503
    assert time.monotonic() - start < 2


def test_openapi_ingestion_schema_refs_resolve():
    spec = app.openapi()
    schemas = spec["components"]["schemas"]

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "$ref" and item.startswith("#/components/schemas/"):
                    assert item.rsplit("/", 1)[-1] in schemas
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(spec)
    assert spec["paths"]["/api/telemetry"]["post"]["security"] == []
    assert "X-Request-ID" not in schemas  # header is not a domain DTO


@pytest.mark.asyncio
async def test_sampling_zero_keeps_counts_without_spans(monkeypatch):
    owner = Telemetry(
        TelemetrySettings(enabled=True, environment="test", sample_rate=0)
    )
    monkeypatch.setattr(runtime, "telemetry", owner)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/currency/codes")).status_code == 200
    with owner.tracer.start_as_current_span("api"):
        await db.run(lambda: User.select(User.id).limit(1).execute())
    assert not any(kind == "traces" for kind, _ in owner.queue)
    assert (
        owner.requests.labels("test", "/api/currency/codes", "GET", "2xx")._value.get()
        == 1
    )


@pytest.mark.asyncio
async def test_async_sqlite_write_and_failure_remain_private(observed):
    exporter = InMemorySpanExporter()
    observed.provider.add_span_processor(SimpleSpanProcessor(exporter))
    with observed.tracer.start_as_current_span("api"):
        await db.run(
            lambda: db.execute_sql("CREATE TEMP TABLE telemetry_canary (value TEXT)")
        )
        await db.run(
            lambda: db.execute_sql(
                "INSERT INTO telemetry_canary VALUES (?)", ["private-canary"]
            )
        )
        with pytest.raises(Exception):
            await db.run(lambda: db.execute_sql("SELECT * FROM missing_canary_table"))
    spans = exporter.get_finished_spans()
    assert any(s.name == "sqlite.write" for s in spans)
    assert any(
        s.name == "sqlite.read" and s.status.status_code.name == "ERROR" for s in spans
    )
    assert "private-canary" not in str([s.attributes for s in spans])
    assert "missing_canary_table" not in str([s.attributes for s in spans])


@pytest.mark.asyncio
async def test_imported_client_spans_cannot_override_zero_sampling(client, observed):
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    observed.provider.sampler = TraceIdRatioBased(0)
    now = time.time_ns()
    data = batch()
    data["records"] = [
        {
            "kind": "span",
            "event_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "trace_id": "1" * 32,
            "span_id": "2" * 16,
            "operation": "api",
            "start_ns": now - 1000,
            "end_ns": now,
            "status": 200,
            "outcome": "ok",
        }
    ]
    response = await client.post("/api/telemetry", json=data)
    assert response.status_code == 202 and response.json()["accepted"] == 0
    assert not observed.queue


@pytest.mark.asyncio
async def test_ingestion_capacity_does_not_wait_for_slow_peers(client, observed):
    observed.ingest_inflight = 16
    response = await client.post("/api/telemetry", json=batch())
    assert response.status_code == 503
    assert observed.ingest_inflight == 16


def test_error_counters_exist_before_first_failure(observed):
    observed.initialize_http_metrics(app.routes)
    from prometheus_client import generate_latest

    metrics = generate_latest(observed.registry).decode()
    assert (
        'expenis_http_requests_total{environment="test",method="GET",route="/api/transactions",status="5xx"} 0.0'
        in metrics
    )
    assert 'status="2xx"' in metrics


def test_documented_settings_are_read_and_bounded(monkeypatch):
    monkeypatch.setenv("EXPENIS_TELEMETRY_QUEUE_BYTES", "1024")
    monkeypatch.setenv("EXPENIS_TELEMETRY_SOURCE_RATE", "45")
    monkeypatch.setenv("EXPENIS_TELEMETRY_GLOBAL_RATE", "600")
    settings = TelemetrySettings.from_env()
    assert settings.queue_bytes == 1024
    assert settings.source_per_minute == 45
    assert settings.global_per_minute == 600
    monkeypatch.setenv("EXPENIS_OTLP_ENDPOINT", "http://private:secret@127.0.0.1:4318")
    settings = TelemetrySettings.from_env()
    assert not settings.enabled and settings.configuration_invalid


@pytest.fixture
def safe_local_logs(observed):
    import io

    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(SafeFormatter())
    handler.addFilter(logging.Filter("src.expenis.server"))
    logging.root.addHandler(handler)
    try:
        yield output
    finally:
        logging.root.removeHandler(handler)
        handler.close()


@pytest.mark.asyncio
async def test_request_logs_use_route_template(observed, safe_local_logs):
    from fastapi import FastAPI
    from src.expenis.observability.middleware import ObservabilityMiddleware

    test_app = FastAPI()
    test_app.add_middleware(ObservabilityMiddleware)

    @test_app.get("/review/{item}")
    async def endpoint(item: str):
        logging.getLogger("src.expenis.server.review").warning("application_event")
        return {"ok": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        assert (
            await client.get("/review/private-canary?secret=hidden")
        ).status_code == 200
    local = json.loads(safe_local_logs.getvalue())
    assert local["route"] == "/review/{item}"
    payload = next(data for kind, data in observed.queue if kind == "logs")
    record = (
        ExportLogsServiceRequest.FromString(payload)
        .resource_logs[0]
        .scope_logs[0]
        .log_records[0]
    )
    assert (
        next(a.value.string_value for a in record.attributes if a.key == "route")
        == "/review/{item}"
    )
    assert "private-canary" not in str(local) and "hidden" not in str(local)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/review/failure", "/api/telemetry", "/api/health/ready", "/metrics", "/stream"],
)
@pytest.mark.parametrize("enabled", [True, False])
async def test_unhandled_error_is_local_and_exported_once(
    observed, safe_local_logs, path, enabled
):
    from fastapi import FastAPI
    from starlette.responses import StreamingResponse
    from src.expenis.observability.middleware import ObservabilityMiddleware
    from src.expenis.server.application import unhandled_exception_handler

    observed.settings = replace(observed.settings, enabled=enabled)
    test_app = FastAPI(exception_handlers={Exception: unhandled_exception_handler})
    test_app.add_middleware(ObservabilityMiddleware)

    async def failure():
        raise RuntimeError("private-exception-canary")

    for route in ["/review/failure", "/api/telemetry", "/api/health/ready", "/metrics"]:
        test_app.add_api_route(route, failure)

    @test_app.get("/stream")
    async def stream():
        async def body():
            yield b"started"
            raise RuntimeError("private-exception-canary")

        return StreamingResponse(body())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(path)
    assert response.status_code == (200 if path == "/stream" else 500)
    records = [json.loads(line) for line in safe_local_logs.getvalue().splitlines()]
    assert len(records) == 1 and records[0]["code"] == "unhandled_error"
    assert "private-exception-canary" not in safe_local_logs.getvalue()
    exported = [data for kind, data in observed.queue if kind == "logs"]
    assert len(exported) == (1 if enabled else 0)
    if exported:
        assert b"private-exception-canary" not in exported[0]


def test_bucket_denials_preserve_fractional_refill():
    from src.expenis.observability.api import _take

    bucket = (0.0, 0.0)
    for tick in range(1, 4):
        allowed, bucket = _take(bucket, 30, 1, tick * 0.5)
        assert not allowed
    allowed, bucket = _take(bucket, 30, 1, 2.0)
    assert allowed and bucket == (0.0, 2.0)


@pytest.mark.asyncio
async def test_throttled_source_cannot_spend_global_tokens(observed):
    observed.settings = replace(
        observed.settings,
        source_burst=1,
        source_per_minute=0,
        global_burst=2,
        global_per_minute=0,
    )
    observed.global_bucket = (2.0, time.monotonic())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("10.0.0.2", 10)),
        base_url="http://test",
    ) as first:
        assert (await first.post("/api/telemetry", json=batch())).status_code == 202
        for _ in range(10):
            assert (await first.post("/api/telemetry", json=batch())).status_code == 429
    assert observed.global_bucket[0] == 1
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("10.0.0.3", 10)),
        base_url="http://test",
    ) as second:
        assert (await second.post("/api/telemetry", json=batch())).status_code == 202


@pytest.mark.asyncio
async def test_global_denial_does_not_spend_source_tokens(client, observed):
    observed.settings = replace(
        observed.settings, source_burst=1, source_per_minute=0, global_per_minute=0
    )
    observed.sources["10.0.0.2"] = (1.0, time.monotonic())
    observed.global_bucket = (0.0, time.monotonic())
    assert (await client.post("/api/telemetry", json=batch())).status_code == 429
    assert observed.sources["10.0.0.2"][0] == 1
    observed.global_bucket = (1.0, time.monotonic())
    assert (await client.post("/api/telemetry", json=batch())).status_code == 202


@pytest.mark.asyncio
async def test_source_capacity_denial_does_not_spend_global_tokens(client, observed):
    observed.settings = replace(observed.settings, cache_records=0)
    before = observed.global_bucket
    assert (await client.post("/api/telemetry", json=batch())).status_code == 503
    assert observed.global_bucket == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,value",
    [
        ("EXPENIS_OTLP_ENDPOINT", "http://private:secret@remote.example:4318"),
        ("EXPENIS_OTLP_ENDPOINT", "http://[bad"),
        ("EXPENIS_OTLP_ENDPOINT", "http://127.0.0.1:99999"),
        ("EXPENIS_TRACE_SAMPLE_RATE", "private-bad-number"),
        ("EXPENIS_TRACE_SAMPLE_RATE", "nan"),
        ("EXPENIS_TRACE_SAMPLE_RATE", "2"),
        ("EXPENIS_TELEMETRY_QUEUE_BYTES", "invalid"),
        ("EXPENIS_TELEMETRY_SOURCE_RATE", "invalid"),
        ("EXPENIS_TELEMETRY_GLOBAL_RATE", "invalid"),
    ],
)
async def test_invalid_telemetry_config_does_not_stop_business(
    client, observed, monkeypatch, name, value
):
    monkeypatch.setenv("EXPENIS_ENV", "production")
    monkeypatch.setenv(name, value)
    settings = TelemetrySettings.from_env()
    assert not settings.enabled and settings.configuration_invalid
    assert settings.endpoint == "http://127.0.0.1:4318"
    if value.startswith(("http", "private")):
        assert value not in repr(settings)
    observed.settings = settings
    assert (await client.get("/api/currency/codes")).status_code == 200
    assert (await client.get("/api/health/ready")).status_code == 200


@pytest.mark.asyncio
async def test_invalid_configuration_reports_safe_local_warning(
    observed, safe_local_logs, monkeypatch
):
    monkeypatch.setenv("EXPENIS_OTLP_ENDPOINT", "http://private-secret@remote.example")
    observed.settings = TelemetrySettings.from_env()
    async with app.router.lifespan_context(app):
        pass
    records = [json.loads(line) for line in safe_local_logs.getvalue().splitlines()]
    assert [record["code"] for record in records] == ["telemetry_config_invalid"]
    assert "private-secret" not in safe_local_logs.getvalue()
    assert not observed.queue
