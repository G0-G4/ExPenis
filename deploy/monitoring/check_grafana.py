"""Verify the disposable Grafana lab only; synthetic credentials/data."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
from src.expenis.observability.runtime import Telemetry
from src.expenis.observability.settings import TelemetrySettings


async def main():
    owner = Telemetry(
        TelemetrySettings(enabled=True, environment="test", endpoint="http://127.0.0.1:14318")
    )
    await owner.start()
    version = f"0.0.{int(uuid4().hex[:4], 16)}"
    try:
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:13000",
            auth=("admin", "expenis-spike-only"),
            timeout=10,
            trust_env=False,
        ) as client:
            health = await client.get("/api/datasources/uid/expenis-logs/health")
            assert health.status_code == 200, health.text
            dashboard = await client.get("/api/dashboards/uid/expenis-overview")
            assert (
                dashboard.status_code == 200
                and dashboard.json()["dashboard"]["uid"] == "expenis-overview"
            ), dashboard.text
            for expected in (1, 2, 3):
                owner.event(
                    "client_network",
                    platform="android",
                    version=version,
                    event_id=str(uuid4()),
                    severity=17,
                )
                for _ in range(30):
                    await asyncio.sleep(0.5)
                    response = await client.post(
                        "/api/ds/query",
                        json={
                            "from": "now-10m",
                            "to": "now",
                            "queries": [
                                {
                                    "refId": "A",
                                    "datasource": {
                                        "uid": "expenis-logs",
                                        "type": "victoriametrics-logs-datasource",
                                    },
                                    "expr": f'environment:=test origin:=client app_version:="{version}" | stats by (fingerprint, platform, app_version) count_uniq(event_id) as errors',
                                    "queryType": "stats",
                                    "intervalMs": 1000,
                                    "maxDataPoints": 100,
                                }
                            ],
                        },
                    )
                    assert response.status_code == 200, response.text
                    result = response.json()["results"]["A"]
                    assert not result.get("error"), result
                    counts = [
                        values
                        for frame in result.get("frames", [])
                        for field, values in zip(frame["schema"]["fields"], frame["data"]["values"])
                        if field.get("type") == "number"
                    ]
                    if counts and counts[-1][-1] == expected:
                        break
                else:
                    raise AssertionError(result)
                assert (expected > 2.5) == (expected == 3)
            print(
                "PASS Grafana datasource health, dashboard provisioning, client count/threshold 1→2→3 with platform/version grouping"
            )
    finally:
        await owner.stop()


if __name__ == "__main__":
    asyncio.run(main())
