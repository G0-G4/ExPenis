"""Generate ExPenis provisioning; shared contact points remain owned by infra."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METRICS = "P4169E866C3094E38"  # Existing infra VictoriaMetrics datasource UID.
LOGS = "expenis-logs"
TEMPO = "expenis-traces"


def query_panel(title, expr, index, *, ds=METRICS, kind="timeseries", query_type=None):
    target = {"refId": "A", "expr": expr, "datasource": {"uid": ds}, "range": True}
    if query_type:
        target["queryType"] = query_type
    return {
        "id": index,
        "title": title,
        "type": kind,
        "datasource": {"uid": ds},
        "gridPos": {"x": ((index - 1) % 2) * 12, "y": ((index - 1) // 2) * 8, "w": 12, "h": 8},
        "targets": [target],
        "fieldConfig": {"defaults": {"noValue": "Нет данных"}, "overrides": []},
        "options": {},
    }


panels = [
    query_panel("Backend scrape / readiness (нет данных ≠ OK)", 'up{job="expenis"}', 1),
    query_panel("Готовность SQLite", 'expenis_ready{job="expenis"}', 2),
    query_panel(
        "Запросы / сек",
        'sum by (route) (rate(expenis_http_requests_total{environment="$environment"}[5m]))',
        3,
    ),
    query_panel(
        "5xx / 5 минут",
        'sum(increase(expenis_http_requests_total{environment="$environment",status=~"5.."}[5m]))',
        4,
    ),
    query_panel(
        "Доля 5xx",
        'sum(rate(expenis_http_requests_total{environment="$environment",status=~"5.."}[5m])) / sum(rate(expenis_http_requests_total{environment="$environment"}[5m]))',
        5,
    ),
    query_panel(
        "Latency p50/p95/p99",
        'histogram_quantile({0.50,0.95,0.99}, sum by (le) (rate(expenis_http_request_duration_seconds_bucket{environment="$environment"}[5m])))',
        6,
    ),
    query_panel(
        "Время зависимостей p95",
        'histogram_quantile(0.95, sum by (le, operation, outcome) (rate(expenis_dependency_duration_seconds_bucket{job="expenis"}[5m])))',
        7,
    ),
    query_panel("Память backend", 'process_resident_memory_bytes{job="expenis"}', 8),
    query_panel(
        "Потери / ошибки отправки",
        'sum by (result) (rate(expenis_telemetry_records_total{job="expenis"}[5m]))',
        9,
    ),
    query_panel(
        "Клиентские ошибки по версии и платформе",
        'environment:="$environment" origin:=client | stats by (fingerprint, platform, app_version) count() as errors | sort by (errors desc) | limit 100',
        10,
        ds=LOGS,
        kind="table",
        query_type="instant",
    ),
    query_panel(
        "Технические логи и переход к trace",
        'environment:="$environment"',
        11,
        ds=LOGS,
        kind="logs",
        query_type="instant",
    ),
    query_panel("In-flight запросы", 'expenis_http_inflight{job="expenis"}', 12),
]
panels.extend(
    [
        query_panel(
            "Клиентские HTTP попытки (доставленная выборка)",
            'sum by (platform, operation, status) (rate(expenis_client_http_requests_total{environment="$environment"}[5m]))',
            13,
        ),
        query_panel(
            "Клиентская latency p95 (доставленная выборка)",
            'histogram_quantile(0.95, sum by (le, platform) (rate(expenis_client_operation_duration_seconds_bucket{environment="$environment"}[5m])))',
            14,
        ),
        query_panel(
            "Принятые ошибки клиентов",
            'sum by (platform, code) (increase(expenis_client_errors_total{environment="$environment"}[10m]))',
            15,
        ),
    ]
)
# PromQL accepts one quantile; keep explicit targets rather than a nonstandard expression.
panels[5]["targets"] = [
    {
        "refId": ref,
        "expr": f'histogram_quantile({q}, sum by (le) (rate(expenis_http_request_duration_seconds_bucket{{environment="$environment"}}[5m])))',
        "legendFormat": label,
    }
    for ref, q, label in [("A", 0.5, "p50"), ("B", 0.95, "p95"), ("C", 0.99, "p99")]
]
dashboard = {
    "uid": "expenis-overview",
    "title": "ExPenis — состояние приложения",
    "schemaVersion": 39,
    "version": 1,
    "refresh": "30s",
    "time": {"from": "now-1h", "to": "now"},
    "tags": ["expenis"],
    "templating": {
        "list": [
            {
                "name": "environment",
                "type": "custom",
                "query": "production,development,test",
                "current": {"text": "production", "value": "production"},
            }
        ]
    },
    "panels": panels,
}
(ROOT / "dashboard.json").write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n")


def alert(uid, title, expr, threshold, *, ds=METRICS, duration="0s", window=300, query_type=None):
    model = {"refId": "A", "expr": expr, "instant": True, "range": False}
    if query_type:
        model["queryType"] = query_type
    return {
        "uid": uid,
        "title": title,
        "condition": "C",
        "for": duration,
        "noDataState": "NoData",
        "execErrState": "Error",
        "labels": {"project": "expenis", "environment": "production"},
        "annotations": {"summary": title},
        "data": [
            {
                "refId": "A",
                "relativeTimeRange": {"from": window, "to": 0},
                "datasourceUid": ds,
                "model": model,
            },
            {
                "refId": "C",
                "datasourceUid": "__expr__",
                "model": {
                    "refId": "C",
                    "type": "threshold",
                    "expression": "A",
                    "conditions": [{"evaluator": {"type": "gt", "params": [threshold]}}],
                },
            },
        ],
    }


errors = '(sum(increase(expenis_http_requests_total{environment="production",status=~"5.."}[5m])) or vector(0))'
all_requests = (
    '(sum(increase(expenis_http_requests_total{environment="production"}[5m])) or vector(0))'
)
rules = [
    alert(
        "expenis-not-ready",
        "ExPenis: backend/SQLite недоступен",
        '1 - probe_success{job="expenis-readiness"}',
        0.5,
        duration="3m",
    ),
    alert(
        "expenis-server-errors",
        "ExPenis: повторяющиеся 5xx",
        f"(({errors} >= bool 5) * (({errors} / clamp_min({all_requests}, 1)) >= bool 0.20))",
        0.5,
    ),
    alert(
        "expenis-client-errors",
        "ExPenis: повторяющаяся клиентская ошибка",
        'environment:=production origin:=client code:~"client_.*" | stats by (fingerprint, platform, app_version) count_uniq(event_id) as errors | sort by (errors desc) | limit 100',
        2.5,
        ds=LOGS,
        window=600,
        query_type="stats",
    ),
    alert(
        "expenis-scrape-missing",
        "ExPenis: метрики недоступны",
        '1 - up{job="expenis"}',
        0.5,
        duration="3m",
    ),
]
# Empty error groups mean no client errors; storage/scrape failure has its own alert.
rules[2]["noDataState"] = "OK"
(ROOT / "alerts.json").write_text(
    json.dumps(
        {
            "apiVersion": 1,
            "groups": [
                {
                    "orgId": 1,
                    "name": "expenis",
                    "folder": "ExPenis",
                    "interval": "30s",
                    "rules": rules,
                }
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
