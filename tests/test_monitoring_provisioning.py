import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "deploy/monitoring"


def test_error_alert_thresholds_match_approved_boundaries():
    rules = json.loads((ROOT / "alerts.json").read_text())["groups"][0]["rules"]
    server = next(rule for rule in rules if rule["uid"] == "expenis-server-errors")
    expression = server["data"][0]["model"]["expr"]
    assert ">= bool 5" in expression and ">= bool 0.20" in expression
    client = next(rule for rule in rules if rule["uid"] == "expenis-client-errors")
    threshold = client["data"][1]["model"]["conditions"][0]["evaluator"]
    assert threshold["type"] == "gt"
    assert [count > threshold["params"][0] for count in (1, 2, 3)] == [False, False, True]
    assert "count_uniq(event_id)" in client["data"][0]["model"]["expr"]
    assert "platform" in client["data"][0]["model"]["expr"]
    assert "app_version" in client["data"][0]["model"]["expr"]


def test_project_provisioning_is_versioned_and_bounded():
    dashboard = json.loads((ROOT / "dashboard.json").read_text())
    assert dashboard["uid"] == "expenis-overview"
    assert dashboard["templating"]["list"][0]["current"]["value"] == "production"
    assert any(
        "expenis_client_operation_duration" in target.get("expr", "")
        for panel in dashboard["panels"]
        for target in panel["targets"]
    )
    assert any(panel["type"] == "logs" for panel in dashboard["panels"])
