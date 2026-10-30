"""Safe stopped-writer reset and service-restart checks for the owned native lab."""

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from uuid import uuid4
from pathlib import Path

ROOT = Path("/var/lib/expenis-obs-acceptance-20261030")
sys.path.insert(0, str(ROOT / "app"))

import httpx
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.trace import SpanKind
from src.expenis.observability.runtime import Telemetry
from src.expenis.observability.settings import TelemetrySettings


def control(action, *names):
    subprocess.run(
        [
            "systemctl",
            action,
            *["expenis-acceptance-" + name + ".service" for name in names],
        ],
        check=True,
    )


async def ready(client, url):
    for _ in range(120):
        try:
            if (await client.get(url)).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    raise AssertionError("Owned service did not recover: " + url)


async def main():
    assert os.geteuid() == 0
    report = {}
    control("start", "logs", "metrics")
    database = ROOT / "state/database.sqlite"
    before = hashlib.file_digest(database.open("rb"), "sha256").hexdigest()
    assert os.path.ismount(ROOT / "data/traces")
    assert (ROOT / "data/traces.ext4").stat().st_size == 400_000_000
    control("stop", "collector", "tempo")
    try:
        state = subprocess.check_output(
            [
                "systemctl",
                "show",
                "expenis-acceptance-tempo.service",
                "-p",
                "ActiveState",
                "--value",
            ],
            text=True,
        ).strip()
        assert state == "inactive", "Writer must be stopped before trace reset"
        for name in ("wal", "blocks"):
            target = ROOT / "data/traces" / name
            assert not target.is_symlink()
            if target.exists():
                shutil.rmtree(target)
        # Use the same home protection as the prepared production core units.
        for name in ("collector", "tempo"):
            path = Path("/run/systemd/system") / (
                "expenis-acceptance-" + name + ".service"
            )
            path.write_text(
                path.read_text().replace("ProtectHome=read-only", "ProtectHome=true")
            )
        subprocess.run(["systemctl", "daemon-reload"], check=True)
    finally:
        control("start", "tempo", "collector")
    report["safe_stopped_trace_reset"] = (
        hashlib.file_digest(database.open("rb"), "sha256").hexdigest() == before
    )
    assert report["safe_stopped_trace_reset"]
    async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
        await ready(client, "http://127.0.0.1:29428/health")
        await ready(client, "http://127.0.0.1:23200/ready")
        login = await client.post(
            "http://127.0.0.1:28000/api/login",
            json={"username": "native-acceptance", "password": "synthetic-testpass123"},
        )
        assert login.status_code == 200
        auth = {"Authorization": "Bearer " + login.json()["access_token"]}
        canary = str(uuid4())
        response = await client.post(
            "http://127.0.0.1:29428/insert/jsonline",
            content=json.dumps(
                {
                    "_time": datetime.now(UTC).isoformat(),
                    "_msg": "application_event",
                    "environment": "test",
                    "event_id": canary,
                }
            )
            + "\n",
        )
        response.raise_for_status()
        response = await client.post("http://127.0.0.1:29428/internal/force_flush")
        response.raise_for_status()
        (ROOT / "state/db-unavailable").touch()
        try:
            assert (
                await client.get("http://127.0.0.1:28000/api/health/ready")
            ).status_code == 503
            assert (
                await client.get("http://127.0.0.1:28000/api/accounts", headers=auth)
            ).status_code == 500
        finally:
            (ROOT / "state/db-unavailable").unlink(missing_ok=True)
        await ready(client, "http://127.0.0.1:28000/api/health/ready")
        report["native_database_fault_recovery"] = True
        control("restart", "guard")
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "native_pressure", Path(__file__).with_name("check.py")
        )
        pressure = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pressure)
        for name in ("logs", "traces"):
            await pressure.volume_pressure(client, auth, name)
            if name == "logs":
                control("start", "logs")
                await ready(client, "http://127.0.0.1:29428/health")
                retained = await client.get(
                    "http://127.0.0.1:29428/select/logsql/query",
                    params={"query": f'event_id:="{canary}"'},
                )
                assert canary in retained.text, (
                    "Previously flushed log was lost during quota recovery"
                )
                report["flushed_log_survived_enospc_restart"] = True
        report["final_guard_pressure_and_recovery"] = True
        budget_file = ROOT / "state/metrics/.acceptance-budget-pressure"
        assert not budget_file.exists()
        try:
            with budget_file.open("wb") as output:
                os.posix_fallocate(output.fileno(), 0, 220_000_000)
            for _ in range(30):
                if (ROOT / "state/paused").exists():
                    break
                await asyncio.sleep(0.5)
            assert (ROOT / "state/paused").exists(), (
                "Aggregate disk budget did not pause ingestion"
            )
            assert (
                await client.get("http://127.0.0.1:28000/metrics")
            ).status_code == 503
            assert (
                await client.post(
                    "http://127.0.0.1:28000/api/telemetry",
                    json={
                        "schema_version": 1,
                        "platform": "web",
                        "app_version": "0.0.0",
                        "records": [
                            {
                                "kind": "error",
                                "event_id": str(uuid4()),
                                "timestamp": datetime.now(UTC).isoformat(),
                                "code": "client_network",
                                "frames": [],
                            }
                        ],
                    },
                )
            ).status_code == 503
            assert (
                await client.get("http://127.0.0.1:28000/api/accounts", headers=auth)
            ).status_code == 200
            report["aggregate_pressure_disk_bytes"] = int(
                pressure.command("du", "-sxB1", "--exclude=paused", str(ROOT)).split()[
                    0
                ]
            )
            stat = os.statvfs(ROOT)
            report["host_free_disk_under_pressure"] = stat.f_bavail * stat.f_frsize
            assert report["aggregate_pressure_disk_bytes"] < 2_000_000_000
        finally:
            budget_file.unlink(missing_ok=True)
        await ready(client, "http://127.0.0.1:28000/metrics")
        report["aggregate_budget_pause_and_resume"] = True
        control("stop", "collector")
        try:
            for _ in range(20):
                assert (
                    await client.get(
                        "http://127.0.0.1:28000/api/accounts", headers=auth
                    )
                ).status_code == 200
            assert (
                await client.get("http://127.0.0.1:28000/api/health/ready")
            ).status_code == 200
            report["native_collector_outage_business_ready"] = True
        finally:
            control("start", "collector")
        owner = Telemetry(
            TelemetrySettings(
                enabled=True, environment="test", endpoint="http://127.0.0.1:24318"
            )
        )
        await owner.start()
        try:
            with owner.tracer.start_as_current_span(
                "api", kind=SpanKind.CLIENT
            ) as root:
                trace_id = format(root.get_span_context().trace_id, "032x")
                span_id = format(root.get_span_context().span_id, "016x")
                response = await client.get(
                    "http://127.0.0.1:28000/api/accounts",
                    headers={**auth, "traceparent": f"00-{trace_id}-{span_id}-01"},
                )
                assert response.status_code == 200
                owner.event("application_event")
            for _ in range(60):
                response = await client.get(
                    "http://127.0.0.1:23200/api/traces/" + trace_id,
                    headers={"Accept": "application/protobuf"},
                )
                if response.status_code == 200:
                    payload = ExportTraceServiceRequest.FromString(response.content)
                    spans = [
                        s
                        for b in payload.resource_spans
                        for ss in b.scope_spans
                        for s in ss.spans
                    ]
                    if any(s.kind == 3 for s in spans) and any(
                        s.name == "sqlite.read" for s in spans
                    ):
                        ids = {s.span_id for s in spans}
                        assert all(
                            not s.parent_span_id or s.parent_span_id in ids
                            for s in spans
                        )
                        logs = await client.get(
                            "http://127.0.0.1:29428/select/logsql/query",
                            params={
                                "query": f'environment:=test trace_id:="{trace_id}"'
                            },
                        )
                        if "application_event" in logs.text:
                            report["recovered_trace_id"] = trace_id
                            report["recovered_parent_tree"] = True
                            report["recovered_log_correlation"] = True
                            break
                await asyncio.sleep(0.5)
            else:
                raise AssertionError("Trace pipeline failed after reset/restart")
        finally:
            await owner.stop()
        assert (
            await client.get("http://127.0.0.1:8000/openapi.json")
        ).status_code == 200
    report["passed"] = True
    (ROOT / "state/recovery-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
