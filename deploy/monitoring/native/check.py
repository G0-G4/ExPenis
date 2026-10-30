"""Bounded native acceptance load, compaction and quota/admission checks."""

import asyncio
import errno
import json
import os
import secrets
import shutil
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from prometheus_client.parser import text_string_to_metric_families

ROOT = Path("/var/lib/expenis-obs-acceptance-20261030")
sys.path.insert(0, str(ROOT / "app"))
from src.expenis.observability.runtime import Telemetry
from src.expenis.observability.settings import TelemetrySettings

CORE = Path("/sys/fs/cgroup/expenisacceptance.slice")
AUX = Path("/sys/fs/cgroup/expenisacceptanceaux.slice")
REPORT = {"started_utc": datetime.now(UTC).isoformat(), "samples": [], "checks": {}}
LATENCIES = []
STOP = asyncio.Event()


def command(*args):
    for _ in range(3):
        result = subprocess.run(args, text=True, capture_output=True)
        if result.returncode == 0:
            return result.stdout.strip()
        time.sleep(0.02)
    result.check_returncode()


def metrics(text):
    return {
        sample.name: sum(s.value for s in family.samples if s.name == sample.name)
        for family in text_string_to_metric_families(text)
        for sample in family.samples
    }


def save():
    (ROOT / "state/acceptance-report.json").write_text(
        json.dumps(REPORT, indent=2) + "\n"
    )


async def wait_ready(client, url, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return response
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    raise AssertionError("Acceptance service did not become ready: " + url)


async def monitor(client):
    while not STOP.is_set():
        available = (
            int(
                next(
                    line.split()[1]
                    for line in Path("/proc/meminfo").read_text().splitlines()
                    if line.startswith("MemAvailable:")
                )
            )
            * 1024
        )
        disk = os.statvfs(ROOT)
        physical = int(command("du", "-sxB1", "--exclude=paused", str(ROOT)).split()[0])
        started = time.monotonic()
        response = await client.get("http://127.0.0.1:8000/openapi.json")
        sample = {
            "elapsed": round(time.monotonic() - REPORT["_start"], 2),
            "core_memory": int((CORE / "memory.current").read_text()),
            "aux_memory": int((AUX / "memory.current").read_text()),
            "host_available": available,
            "stage_disk": physical,
            "host_free_disk": disk.f_bavail * disk.f_frsize,
            "production_probe_seconds": round(time.monotonic() - started, 4),
            "production_probe_status": response.status_code,
        }
        REPORT["samples"].append(sample)
        save()
        assert response.status_code == 200, "Production probe changed; stopping test"
        assert available >= 1_000_000_000, "Host memory safety reserve exhausted"
        assert sample["host_free_disk"] >= 8_000_000_000, (
            "Host disk safety reserve exhausted"
        )
        assert physical < 1_950_000_000, "Stage approached the 2 GB ceiling"
        assert sample["core_memory"] <= 1_000_000_000
        await asyncio.sleep(1)


async def business(client, auth):
    while not STOP.is_set():
        started = time.monotonic()
        response = await client.get("http://127.0.0.1:28000/api/accounts", headers=auth)
        assert response.status_code == 200, "Synthetic business request failed"
        LATENCIES.append(time.monotonic() - started)
        await asyncio.sleep(0.2)


async def load(owner, rate, duration):
    end = time.monotonic() + duration
    count = 0
    next_tick = time.monotonic()
    while time.monotonic() < end:
        with owner.tracer.start_as_current_span("api"):
            with owner.tracer.start_as_current_span("sqlite.read"):
                owner.event(
                    "application_event",
                    frames=[
                        {
                            "file": "lib/acceptance.dart",
                            "function": "synthetic_" + secrets.token_hex(16),
                            "line": 10 + i,
                        }
                        for i in range(20)
                    ],
                )
        count += 1
        next_tick += 1 / rate
        await asyncio.sleep(max(0, next_tick - time.monotonic()))
    REPORT["checks"].setdefault("load", []).append(
        {"target_per_second": rate, "seconds": duration, "records": count}
    )
    print("Finished load phase", rate, duration, count, flush=True)


async def volume_pressure(client, auth, name):
    target = ROOT / "data" / name
    pressure = target / ".acceptance-pressure"
    assert not pressure.exists()
    before = (ROOT / "state/database.sqlite").stat().st_size
    try:
        with pressure.open("wb") as output:
            free = os.statvfs(target)
            os.posix_fallocate(
                output.fileno(), 0, free.f_bavail * free.f_frsize - 40_000_000
            )
            try:
                os.posix_fallocate(output.fileno(), 0, 500_000_000)
            except OSError as error:
                assert error.errno == errno.ENOSPC
            else:
                raise AssertionError("Fixed-volume overflow did not fail")
        for _ in range(20):
            if (ROOT / "state/paused").exists():
                break
            await asyncio.sleep(0.5)
        assert (ROOT / "state/paused").exists(), "Guard did not pause admission"
        assert (await client.get("http://127.0.0.1:28000/metrics")).status_code == 503
        assert (
            await client.get("http://127.0.0.1:28000/api/health/ready")
        ).status_code == 200
        assert (
            await client.get("http://127.0.0.1:28000/api/accounts", headers=auth)
        ).status_code == 200
        assert (ROOT / "data" / (name + ".ext4")).stat().st_size == 400_000_000
        assert (ROOT / "state/database.sqlite").stat().st_size == before
    finally:
        pressure.unlink(missing_ok=True)
    await wait_ready(client, "http://127.0.0.1:28000/metrics", 15)
    REPORT["checks"][name + "_quota_guard"] = True
    print("Quota/admission/recovery passed:", name, flush=True)


async def run():
    prior_elapsed = 0
    if "--resume" in sys.argv:
        previous = json.loads((ROOT / "state/acceptance-report.json").read_text())
        shutil.copyfile(
            ROOT / "state/acceptance-report.json",
            ROOT / "state/acceptance-report-first.json",
        )
        REPORT.update(previous)
        REPORT.setdefault("measurement_interruptions", []).append(
            REPORT.pop("failure", "interrupted")
        )
        prior_elapsed = REPORT.get("elapsed_seconds", 0)
    REPORT["_start"] = time.monotonic() - prior_elapsed
    REPORT["core_memory_max"] = int((CORE / "memory.max").read_text())
    assert REPORT["core_memory_max"] <= 1_000_000_000
    REPORT["events_before"] = {
        name: (path / "memory.events").read_text()
        for name, path in [("core", CORE), ("aux", AUX)]
    }
    owner = Telemetry(
        TelemetrySettings(
            enabled=True,
            environment="test",
            endpoint="http://127.0.0.1:24318",
            paused_file=str(ROOT / "state/paused"),
        )
    )
    await owner.start()
    async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
        await wait_ready(client, "http://127.0.0.1:23200/ready")
        await wait_ready(client, "http://127.0.0.1:28000/api/health/ready")
        login = await client.post(
            "http://127.0.0.1:28000/api/login",
            json={"username": "native-acceptance", "password": "synthetic-testpass123"},
        )
        assert login.status_code == 200
        auth = {"Authorization": "Bearer " + login.json()["access_token"]}
        monitor_task = asyncio.create_task(monitor(client))
        business_task = asyncio.create_task(business(client, auth))
        try:
            # Test the actual 30-day log policy with past synthetic timestamps.
            old_id, expired_id = str(uuid4()), str(uuid4())
            lines = [
                json.dumps(
                    {
                        "_time": (datetime.now(UTC) - timedelta(days=age)).isoformat(),
                        "_msg": "application_event",
                        "environment": "test",
                        "event_id": event,
                    }
                )
                for age, event in [(20, old_id), (31, expired_id)]
            ]
            response = await client.post(
                "http://127.0.0.1:29428/insert/jsonline",
                content="\n".join(lines) + "\n",
            )
            response.raise_for_status()
            await asyncio.sleep(3)
            old = await client.get(
                "http://127.0.0.1:29428/select/logsql/query",
                params={"query": f'event_id:="{old_id}"'},
            )
            expired = await client.get(
                "http://127.0.0.1:29428/select/logsql/query",
                params={"query": f'event_id:="{expired_id}"'},
            )
            assert old_id in old.text and expired_id not in expired.text, (
                "30d log retention boundary failed"
            )
            REPORT["checks"]["logs_30d_boundary"] = True
            phases = (
                []
                if "--resume" in sys.argv
                else [(25, 10), (100, 30), (250, 90), (500, 90)]
            )
            for rate, duration in phases:
                task = asyncio.create_task(load(owner, rate, duration))
                done, _ = await asyncio.wait(
                    [task, monitor_task, business_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for ended in done:
                    ended.result()
                assert task in done
            response = await client.post(
                "http://127.0.0.1:29428/internal/force_merge",
                params={"partition_prefix": datetime.now(UTC).strftime("%Y%m%d")},
            )
            response.raise_for_status()
            # Allow default Tempo blocklist polling and normal compaction to run.
            for _ in range(180):
                response = await client.get("http://127.0.0.1:23200/metrics")
                values = metrics(response.text)
                compaction = {
                    k: v for k, v in values.items() if "compact" in k and v > 0
                }
                if any(
                    "compacted_blocks_total" in k or "compaction_blocks_total" in k
                    for k in compaction
                ):
                    REPORT["checks"]["tempo_compaction_metrics"] = compaction
                    break
                monitor_task.result() if monitor_task.done() else None
                business_task.result() if business_task.done() else None
                await asyncio.sleep(1)
            else:
                REPORT["checks"]["tempo_compaction_metrics"] = compaction
                raise AssertionError("No completed Tempo compaction observed")
            for name in ("logs", "traces"):
                await volume_pressure(client, auth, name)
            REPORT["checks"]["business_requests"] = len(LATENCIES)
            REPORT["checks"]["business_latency_p95_seconds"] = statistics.quantiles(
                LATENCIES, n=20
            )[18]
            REPORT["events_after"] = {
                name: (path / "memory.events").read_text()
                for name, path in [("core", CORE), ("aux", AUX)]
            }
            for name in ("core", "aux"):
                assert REPORT["events_before"][name] == REPORT["events_after"][name], (
                    "Cgroup memory pressure/OOM occurred"
                )
            REPORT["passed"] = True
        finally:
            STOP.set()
            for task in (monitor_task, business_task):
                task.cancel()
            await asyncio.gather(monitor_task, business_task, return_exceptions=True)
            await owner.stop()
            REPORT["elapsed_seconds"] = round(time.monotonic() - REPORT["_start"], 2)
            REPORT["peaks"] = {
                key: max(s[key] for s in REPORT["samples"])
                for key in (
                    "core_memory",
                    "aux_memory",
                    "stage_disk",
                    "production_probe_seconds",
                )
            }
            save()
            print(
                json.dumps(
                    {k: v for k, v in REPORT.items() if k not in ("samples", "_start")},
                    indent=2,
                ),
                flush=True,
            )


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except BaseException as error:
        REPORT["failure"] = type(error).__name__ + ": " + str(error)
        save()
        raise
