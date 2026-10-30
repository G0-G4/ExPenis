"""Test-only fault Web bundle; own local servers and synthetic data only."""

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
STATE = Path("/private/tmp/expenis-observability-e2e")


def records(client):
    response = client.get(
        "http://127.0.0.1:19428/select/logsql/query",
        params={
            "query": "environment:=test origin:=client platform:=web "
            "code:in(client_framework, client_unhandled)",
        },
    )
    response.raise_for_status()
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def main():
    with httpx.Client(timeout=3, trust_env=False) as client:
        before = {row["event_id"] for row in records(client)}
        for port in (18000, 18081):
            try:
                client.get(f"http://127.0.0.1:{port}")
            except httpx.ConnectError:
                pass
            else:
                raise RuntimeError(
                    f"Port {port} occupied; refusing to touch another server"
                )
        with (STATE / "web-fault-server.log").open("w") as output:
            processes = []
            try:
                processes.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "deploy/monitoring/run_e2e_backend.py",
                            "--reuse",
                        ],
                        cwd=ROOT,
                        stdout=output,
                        stderr=subprocess.STDOUT,
                    )
                )
                processes.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "http.server",
                            "18081",
                            "--bind",
                            "127.0.0.1",
                            "--directory",
                            str(STATE / "fault-web"),
                        ],
                        stdout=output,
                        stderr=subprocess.STDOUT,
                    )
                )
                for _ in range(100):
                    try:
                        if (
                            client.get(
                                "http://127.0.0.1:18000/api/health/ready"
                            ).status_code
                            == 200
                        ):
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(0.1)
                else:
                    raise AssertionError("Temporary backend did not start")
                with sync_playwright() as p:
                    browser = p.chromium.launch(channel="chrome", headless=True)
                    page = browser.new_page()
                    page.goto("http://127.0.0.1:18081")
                    page.wait_for_timeout(20000)
                    page.screenshot(path=str(STATE / "web-faults.png"))
                    browser.close()
                for _ in range(20):
                    new = [
                        row for row in records(client) if row["event_id"] not in before
                    ]
                    if len(new) >= 2:
                        break
                    time.sleep(0.5)
                assert sorted(row["code"] for row in new) == [
                    "client_framework",
                    "client_unhandled",
                ], new
                encoded = json.dumps(new)
                assert "synthetic_framework" not in encoded
                assert "synthetic_unhandled" not in encoded
                assert "telemetrye2e" not in encoded and "testpass123" not in encoded
                report = {
                    "passed": True,
                    "errors": [
                        {"code": row["code"], "event_id": row["event_id"]}
                        for row in new
                    ],
                }
                (STATE / "web-fault-result.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
                print(json.dumps(report, indent=2))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.send_signal(signal.SIGINT)
                        process.wait(timeout=5)


if __name__ == "__main__":
    main()
