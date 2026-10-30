"""Real Collector outage against only the disposable compose/API lab."""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from prometheus_client.parser import text_string_to_metric_families

ROOT = Path(__file__).resolve().parents[2]
STATE = Path("/private/tmp/expenis-observability-e2e")
COMPOSE = [
    "docker",
    "compose",
    "-p",
    "expenis-observability-spike",
    "-f",
    str(ROOT / "deploy/monitoring/compose.spike.yml"),
]
API = "http://127.0.0.1:18000"


def run():
    result = {}
    with httpx.Client(timeout=2, trust_env=False) as client:
        try:
            client.get(API + "/api/health/ready")
        except httpx.ConnectError:
            pass
        else:
            raise RuntimeError(
                "Port 18000 is occupied; refusing to touch another process"
            )
    (STATE / "database-unavailable").unlink(missing_ok=True)
    (STATE / "paused").unlink(missing_ok=True)
    with (STATE / "resilience-server.log").open("w") as output:
        process = subprocess.Popen(
            [sys.executable, "deploy/monitoring/run_e2e_backend.py", "--reuse"],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            env={**os.environ, "EXPENIS_TELEMETRY_QUEUE_BYTES": "4096"},
        )
        try:
            with httpx.Client(base_url=API, timeout=3, trust_env=False) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError(
                            "Isolated backend failed to start; see lab log"
                        )
                    try:
                        if client.get("/api/health/ready").status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Backend startup timed out")
                subprocess.run(COMPOSE + ["stop", "collector"], check=True, timeout=30)
                # Real database-backed authentication while the exporter is unreachable.
                started = time.monotonic()
                login = client.post(
                    "/api/login",
                    json={
                        "username": "telemetrye2e",
                        "password": "testpass123",
                    },
                )
                assert login.status_code == 200, login.status_code
                auth = {"Authorization": "Bearer " + login.json()["access_token"]}
                with ThreadPoolExecutor(max_workers=10) as pool:
                    responses = list(
                        pool.map(
                            lambda _: client.get("/api/accounts", headers=auth),
                            range(40),
                        )
                    )
                assert all(r.status_code == 200 for r in responses)
                result["40_business_requests_seconds"] = round(
                    time.monotonic() - started, 3
                )
                assert client.get("/api/health/ready").status_code == 200
                canary = "PRIVATE_RESILIENCE_CANARY_398127"
                with ThreadPoolExecutor(max_workers=10) as pool:
                    rejected = list(
                        pool.map(
                            lambda _: client.post(
                                "/api/telemetry", json={"unknown": canary}
                            ),
                            range(100),
                        )
                    )
                assert all(r.status_code in (422, 429) for r in rejected)
                assert any(r.status_code == 429 for r in rejected)
                assert all(canary not in r.text for r in rejected)
                result["100_invalid_batches"] = {
                    str(status): sum(r.status_code == status for r in rejected)
                    for status in (422, 429)
                }
                time.sleep(1)
                metrics = client.get("/metrics")
                assert metrics.status_code == 200
                counters = {
                    s.labels["result"]: s.value
                    for family in text_string_to_metric_families(metrics.text)
                    for s in family.samples
                    if s.name == "expenis_telemetry_records_total"
                }
                assert counters["export_failed"] > 0, counters
                assert counters["dropped"] > 0, counters
                result["delivery_counters_during_outage"] = counters
                (STATE / "database-unavailable").touch()
                try:
                    assert client.get("/api/health/ready").status_code == 503
                finally:
                    (STATE / "database-unavailable").unlink(missing_ok=True)
                assert client.get("/api/health/ready").status_code == 200
                started = time.monotonic()
                process.send_signal(signal.SIGINT)
                assert process.wait(timeout=5) == 0
                result["shutdown_seconds"] = round(time.monotonic() - started, 3)
                assert canary not in (STATE / "resilience-server.log").read_text()
                assert canary not in (STATE / "logs/technical.log").read_text()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            subprocess.run(COMPOSE + ["start", "collector"], check=True, timeout=30)
            (STATE / "database-unavailable").unlink(missing_ok=True)
        # Restart the same owned backend/database after bounded shutdown.
        restarted = subprocess.Popen(
            [sys.executable, "deploy/monitoring/run_e2e_backend.py", "--reuse"],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(base_url=API, timeout=2, trust_env=False) as client:
                for _ in range(100):
                    try:
                        if client.get("/api/health/ready").status_code == 200:
                            result["restart_ready"] = True
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(0.1)
                else:
                    raise AssertionError("Restart did not become ready")
        finally:
            restarted.send_signal(signal.SIGINT)
            restarted.wait(timeout=5)
    result["passed"] = True
    (STATE / "resilience-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
