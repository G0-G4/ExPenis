"""Isolated Web smoke: local bundle/backend and synthetic account only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
from playwright.sync_api import sync_playwright
from e2e.helpers import login_via_ui, expect_transactions_screen, open_section

STATE = Path("/private/tmp/expenis-observability-e2e")


def main():
    statuses = []
    contexts = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 850})

        def observe(response):
            if "/api/" in response.url and "/telemetry" not in response.url:
                statuses.append((response.url.split("?")[0].rsplit("/", 1)[-1], response.status))
                header = response.request.headers.get("traceparent")
                if header:
                    contexts.append(header)

        page.on("response", observe)
        page.goto("http://127.0.0.1:18080")
        page.locator("flt-semantics-placeholder").wait_for(state="attached", timeout=30000)
        page.evaluate("() => document.querySelector('flt-semantics-placeholder').click()")
        login_via_ui(page, "telemetrye2e", "testpass123")
        expect_transactions_screen(page)
        page.wait_for_timeout(4000)
        open_section(page, "Accounts")
        page.wait_for_timeout(2000)
        assert any(path == "refresh" and status == 200 for path, status in statuses), statuses
        (STATE / "database-unavailable").touch()
        try:
            open_section(page, "Categories")
            page.wait_for_timeout(2000)
            assert (
                httpx.get("http://127.0.0.1:18000/api/health/ready", trust_env=False).status_code
                == 503
            )
        finally:
            (STATE / "database-unavailable").unlink(missing_ok=True)
        page.wait_for_timeout(7000)
        assert contexts, "No first-party trace headers observed"
        assert any(status >= 500 for _, status in statuses), statuses
        page.screenshot(path=str(STATE / "web.png"))
        browser.close()
    response = httpx.get(
        "http://127.0.0.1:19428/select/logsql/query",
        params={"query": "environment:=test origin:=client platform:=web code:=client_http"},
        trust_env=False,
        timeout=5,
    )
    assert response.text.strip(), "Web errors not found in log storage"
    assert "testpass123" not in response.text and "telemetrye2e" not in response.text
    print(
        "PASS Web UI login, trace headers, refresh/retry, handled 500, database readiness, error delivery and privacy canaries"
    )


if __name__ == "__main__":
    main()
