"""Authorized Telegram delivery check using disposable Grafana and existing bot.

Credentials are read over SSH into memory and never printed or written to files.
Only the synthetic local Grafana database temporarily holds the receiver.
"""

import json
import subprocess
import time
from uuid import uuid4

import httpx
from prometheus_client.parser import text_string_to_metric_families

REMOTE = """from pathlib import Path
import json,re,shlex
env = Path('/etc/grafana/secrets/alerting.env').read_text()
line = next(line for line in env.splitlines() if line.startswith('TELEGRAM_BOT_TOKEN='))
token = shlex.split(line.split('=', 1)[1])[0]
config = Path('/etc/grafana/provisioning/alerting/contact-points.yml').read_text()
chat = re.search(r'(?m)^\\s*chatid:\\s*["\\\']?(-?\\d+)', config).group(1)
print(json.dumps({'token': token, 'chat': chat}))
"""


def metrics(client):
    response = client.get("/metrics")
    response.raise_for_status()
    counts = {"sent": 0, "failed": 0}
    for family in text_string_to_metric_families(response.text):
        for sample in family.samples:
            if sample.labels.get("integration") != "telegram":
                continue
            if sample.name == "grafana_alerting_notifications_total":
                counts["sent"] += sample.value
            if sample.name == "grafana_alerting_notifications_failed_total":
                counts["failed"] += sample.value
    return counts


def main():
    loaded = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "cloud",
            "sudo -n python3 -",
        ],
        input=REMOTE,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if loaded.returncode:
        raise RuntimeError("Cannot load existing Telegram configuration over SSH")
    secret = json.loads(loaded.stdout)
    loaded = None
    name = "expenis-acceptance-" + uuid4().hex[:8]
    uid = name
    with httpx.Client(
        base_url="http://127.0.0.1:13000",
        trust_env=False,
        auth=("admin", "expenis-spike-only"),
        timeout=15,
    ) as client:
        response = client.post(
            "/api/v1/provisioning/contact-points",
            json={
                "uid": uid,
                "name": name,
                "type": "telegram",
                "disableResolveMessage": False,
                "settings": {
                    "chatid": secret["chat"],
                    "bottoken": secret["token"],
                    "disable_web_page_preview": True,
                    "message": "{{ range .Alerts }}{{ .Status }}: {{ .Annotations.summary }}\n{{ end }}",
                },
            },
        )
        secret.clear()
        if response.status_code not in (200, 201, 202):
            raise RuntimeError(
                "Cannot create isolated test receiver; response body suppressed"
            )
        baseline = metrics(client)
        response = client.put(
            "/api/v1/provisioning/policies",
            json={
                "receiver": name,
                "group_by": [
                    "alertname",
                    "fingerprint",
                    "platform",
                    "app_version",
                    "instance",
                ],
                "group_wait": "1s",
                "group_interval": "5s",
                "repeat_interval": "4h",
            },
        )
        response.raise_for_status()
        now = int(time.time())
        lines = [
            f'expenis_acceptance_alert{{test_run="{name}",fingerprint="acceptance-only",'
            f'platform="{platform}",app_version="0.0.0",instance="isolated-lab",'
            f'test_member="{member}"}} 1 {now * 1000}'
            for platform, member in [("web", "a"), ("web", "b"), ("android", "a")]
        ]
        response = httpx.post(
            "http://127.0.0.1:18428/api/v1/import/prometheus",
            content="\n".join(lines) + "\n",
            trust_env=False,
        )
        response.raise_for_status()
        query = f'last_over_time(expenis_acceptance_alert{{test_run="{name}"}}[5m])'
        for _ in range(60):
            response = httpx.get(
                "http://127.0.0.1:18428/api/v1/query",
                params={"query": query, "nocache": 1},
                trust_env=False,
            )
            if len(response.json()["data"]["result"]) == 3:
                break
            time.sleep(0.5)
        else:
            raise AssertionError("Test series were not indexed")
        response = client.post("/api/folders", json={"uid": name, "title": name})
        response.raise_for_status()
        rule = {
            "uid": uid,
            "title": name,
            "condition": "C",
            "folderUID": name,
            "ruleGroup": name,
            "for": "0s",
            "noDataState": "OK",
            "execErrState": "Error",
            "labels": {"project": "expenis", "environment": "test"},
            "annotations": {
                "summary": "Проверка ExPenis: тестовый алерт, действий не требуется"
            },
            "data": [
                {
                    "refId": "A",
                    "datasourceUid": "P4169E866C3094E38",
                    "relativeTimeRange": {"from": 300, "to": 0},
                    "model": {
                        "refId": "A",
                        "expr": query,
                        "instant": True,
                        "range": False,
                    },
                },
                {
                    "refId": "C",
                    "datasourceUid": "__expr__",
                    "model": {
                        "refId": "C",
                        "type": "threshold",
                        "expression": "A",
                        "conditions": [{"evaluator": {"type": "gt", "params": [0.5]}}],
                    },
                },
            ],
        }
        try:
            response = client.put(
                f"/api/v1/provisioning/folder/{name}/rule-groups/{name}",
                json={
                    "title": name,
                    "folderUid": name,
                    "interval": 10,
                    "rules": [rule],
                },
            )
            response.raise_for_status()
            for _ in range(45):
                current = metrics(client)
                if current["sent"] >= baseline["sent"] + 2:
                    break
                time.sleep(1)
            else:
                raise AssertionError("Telegram firing notifications did not finish")
            assert current["failed"] == baseline["failed"], "Telegram delivery failed"
            assert current["sent"] == baseline["sent"] + 2, (
                "Grouping did not produce two notifications"
            )
            groups = client.get("/api/alertmanager/grafana/api/v2/alerts/groups")
            groups.raise_for_status()
            own = [
                group for group in groups.json() if group["receiver"]["name"] == name
            ]
            assert sorted(len(group["alerts"]) for group in own) == [1, 2], (
                "Unexpected alert groups"
            )
            rule["data"][0]["model"]["expr"] = "0 * " + query
            response = client.put("/api/v1/provisioning/alert-rules/" + uid, json=rule)
            response.raise_for_status()
            for _ in range(45):
                current = metrics(client)
                if current["sent"] >= baseline["sent"] + 4:
                    break
                time.sleep(1)
            else:
                raise AssertionError("Telegram recovery notifications did not finish")
            assert current["failed"] == baseline["failed"], (
                "Telegram recovery delivery failed"
            )
            print(
                "PASS existing Telegram bot: 3 test alerts grouped into 2 firing + 2 recovery notifications"
            )
        finally:
            client.delete("/api/v1/provisioning/alert-rules/" + uid)
            client.delete("/api/folders/" + name)
            client.delete("/api/v1/provisioning/policies")
            client.delete("/api/v1/provisioning/contact-points/" + uid)


if __name__ == "__main__":
    main()
