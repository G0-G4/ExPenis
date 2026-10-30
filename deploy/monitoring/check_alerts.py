"""Evaluate the real alert expressions in the disposable metrics/Grafana lab."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parent


def main():
    rules = json.loads((ROOT / "alerts.json").read_text())["groups"][0]["rules"]
    results = []
    with (
        httpx.Client(
            base_url="http://127.0.0.1:18428", timeout=5, trust_env=False
        ) as vm,
        httpx.Client(
            base_url="http://127.0.0.1:13000",
            timeout=10,
            trust_env=False,
            auth=("admin", "expenis-spike-only"),
        ) as grafana,
    ):
        for _ in range(120):
            try:
                if grafana.get("/api/health").status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.5)
        else:
            raise AssertionError("Test Grafana did not become ready")
        now = int(time.time())
        for name, errors, total, expected in [
            ("boundary", 5, 25, 1),
            ("below_ratio", 5, 26, 0),
            ("below_count", 4, 20, 0),
            ("recovered", 0, 25, 0),
        ]:
            environment = "test_" + uuid4().hex
            lines = []
            for status, count in [("5xx", errors), ("2xx", total - errors)]:
                for offset, value in [
                    (-330, 0),
                    (-300, 0),
                    (-180, 0),
                    (-120, count),
                    (-15, count),
                ]:
                    lines.append(
                        f'expenis_http_requests_total{{environment="{environment}",'
                        f'route="/api/test",status="{status}"}} {value} {(now + offset) * 1000}'
                    )
            response = vm.post(
                "/api/v1/import/prometheus", content="\n".join(lines) + "\n"
            )
            response.raise_for_status()
            # Import is buffered. Require actual series, never accept vector(0) as data.
            for _ in range(60):
                response = vm.get(
                    "/api/v1/query",
                    params={
                        "query": f'expenis_http_requests_total{{environment="{environment}"}}',
                        "time": now,
                        "nocache": 1,
                    },
                )
                response.raise_for_status()
                if len(response.json()["data"]["result"]) == 2:
                    break
                time.sleep(0.5)
            else:
                raise AssertionError("Synthetic metrics were not indexed")
            data = json.loads(
                json.dumps(rules[1]["data"]).replace("production", environment)
            )
            response = grafana.post(
                "/api/v1/eval",
                json={
                    "condition": "C",
                    "data": data,
                    "now": datetime.fromtimestamp(now, UTC).isoformat(),
                },
            )
            response.raise_for_status()
            evaluated = response.json()["results"]
            assert not evaluated["A"].get("error"), evaluated
            assert not evaluated["C"].get("error"), evaluated
            value = evaluated["C"]["frames"][0]["data"]["values"][0][0]
            assert value == expected, (name, value, expected)
            results.append(
                {"case": name, "errors": errors, "total": total, "condition": value}
            )
        # The actual configured production expression ignores all synthetic environments.
        response = grafana.post(
            "/api/v1/eval",
            json={
                "condition": "C",
                "data": rules[1]["data"],
                "now": datetime.fromtimestamp(now, UTC).isoformat(),
            },
        )
        response.raise_for_status()
        assert response.json()["results"]["C"]["frames"][0]["data"]["values"][0][0] == 0
        assert rules[0]["for"] == "3m"
        assert rules[2]["data"][0]["relativeTimeRange"]["from"] == 600
        assert rules[2]["noDataState"] == "OK"
    report = {"cases": results, "production_ignores_test": True, "passed": True}
    Path("/private/tmp/expenis-observability-e2e/alerts-result.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
