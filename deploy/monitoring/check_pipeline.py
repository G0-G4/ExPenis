"""Isolated compose.spike.yml end-to-end check. No production defaults/data."""

import asyncio
import secrets
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx
from fastapi import FastAPI
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    SpanKind,
    TraceFlags,
    set_span_in_context,
)

from src.expenis.observability import runtime
from src.expenis.observability.api import router
from src.expenis.observability.runtime import Telemetry
from src.expenis.observability.settings import TelemetrySettings


async def main():
    owner = Telemetry(
        TelemetrySettings(enabled=True, environment="test", endpoint="http://127.0.0.1:14318")
    )
    runtime.telemetry = owner
    trace_id = secrets.token_hex(16)
    client_id = secrets.token_hex(8)
    start_ns = time.time_ns()
    parent = set_span_in_context(
        NonRecordingSpan(SpanContext(int(trace_id, 16), int(client_id, 16), True, TraceFlags(1)))
    )
    with owner.tracer.start_as_current_span("api", context=parent, kind=SpanKind.SERVER):
        with owner.tracer.start_as_current_span("sqlite.read"):
            owner.event("application_event")
    timestamp = datetime.now(UTC).isoformat()
    records = [
        {
            "kind": "span",
            "event_id": str(uuid4()),
            "timestamp": timestamp,
            "trace_id": trace_id,
            "span_id": client_id,
            "operation": "api",
            "start_ns": start_ns,
            "end_ns": time.time_ns(),
            "status": 200,
            "outcome": "ok",
        },
        {
            "kind": "error",
            "event_id": str(uuid4()),
            "timestamp": timestamp,
            "trace_id": trace_id,
            "span_id": client_id,
            "code": "client_operation",
            "frames": [],
        },
    ]
    app = FastAPI()
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as api:
        response = await api.post(
            "/api/telemetry",
            json={
                "schema_version": 1,
                "platform": "web",
                "app_version": "0.0.0",
                "records": records,
            },
        )
        assert response.status_code == 202 and response.json()["accepted"] == 2, response.text
    await owner.start()
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            for _ in range(60):
                await asyncio.sleep(0.5)
                trace = await client.get(
                    f"http://127.0.0.1:13200/api/traces/{trace_id}",
                    headers={"Accept": "application/protobuf"},
                )
                logs = await client.get(
                    "http://127.0.0.1:19428/select/logsql/query",
                    params={"query": f'trace_id:"{trace_id}"'},
                )
                if trace.status_code != 200 or "client_operation" not in logs.text:
                    continue
                payload = ExportTraceServiceRequest.FromString(trace.content)
                spans = [
                    s for b in payload.resource_spans for ss in b.scope_spans for s in ss.spans
                ]
                if len(spans) != 3:
                    continue
                child = next(s for s in spans if s.name == "sqlite.read")
                server = next(s for s in spans if s.kind == 2)
                assert child.parent_span_id == server.span_id
                assert server.parent_span_id.hex() == client_id
                assert any(s.span_id.hex() == client_id for s in spans)
                print(
                    f"PASS ingestion → OTLP → logs/Tempo; client/server/DB parents; trace/log link: {trace_id}"
                )
                return
    finally:
        await owner.stop()
    raise RuntimeError("pipeline check timed out")


if __name__ == "__main__":
    asyncio.run(main())
