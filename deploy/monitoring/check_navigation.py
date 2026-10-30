"""Real Grafana navigation for a trace emitted by check_pipeline.py; lab only."""

import json
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from playwright.sync_api import expect, sync_playwright


def explore_url(datasource, query):
    panes = {
        "a": {
            "datasource": datasource,
            "queries": [query],
            "range": {"from": "now-1h", "to": "now"},
        }
    }
    return "http://127.0.0.1:13000/explore?" + urlencode(
        {
            "schemaVersion": 1,
            "panes": json.dumps(panes),
            "orgId": 1,
        }
    )


def main(trace_id):
    if not re.fullmatch("[0-9a-f]{32}", trace_id):
        raise ValueError("Expected the synthetic pipeline trace ID")
    state = Path("/private/tmp/expenis-observability-e2e")
    state.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        login = context.request.post(
            "http://127.0.0.1:13000/login",
            data={
                "user": "admin",
                "password": "expenis-spike-only",
            },
        )
        assert login.status == 200
        page = context.new_page()
        page.goto(
            explore_url(
                "expenis-logs",
                {
                    "refId": "A",
                    "datasource": {
                        "uid": "expenis-logs",
                        "type": "victoriametrics-logs-datasource",
                    },
                    "expr": f'environment:=test trace_id:="{trace_id}"',
                    "queryType": "instant",
                },
            )
        )
        page.get_by_text("client_operation", exact=True).first.click(timeout=30000)
        page.get_by_role("link", name="Tempo", exact=True).click()
        expect(page.get_by_text("3 spans", exact=True)).to_be_visible(timeout=30000)
        page.get_by_text(re.compile(r"^expenis-backend api")).first.click()
        related = page.get_by_role("link", name="Related logs", exact=True)
        expect(related).to_be_visible()
        target = related.get_attribute("href")
        left = json.loads(parse_qs(urlparse(target).query)["left"][0])
        assert left["datasource"] == "expenis-logs"
        assert (
            left["queries"][0]["expr"] == f'environment:="test" trace_id:="{trace_id}"'
        )
        page.screenshot(path=str(state / "grafana-trace.png"))
        related.click()
        expect(page.get_by_text("client_operation", exact=True).first).to_be_visible(
            timeout=30000
        )
        expect(page.get_by_text("application_event", exact=True).first).to_be_visible()
        page.screenshot(path=str(state / "grafana-related-logs.png"))
        missing = secrets.token_hex(16)
        page.goto(
            explore_url(
                "expenis-traces",
                {
                    "refId": "A",
                    "datasource": {"uid": "expenis-traces", "type": "tempo"},
                    "query": missing,
                    "queryType": "traceql",
                },
            )
        )
        expect(
            page.get_by_text(
                re.compile(r"trace.*not found|No traces? found", re.I)
            ).first
        ).to_be_visible(timeout=30000)
        page.screenshot(path=str(state / "grafana-missing-trace.png"))
        browser.close()
    print(
        "PASS real log→trace→logs links, environment filter and missing-trace UI:",
        trace_id,
    )


if __name__ == "__main__":
    main(sys.argv[1])
