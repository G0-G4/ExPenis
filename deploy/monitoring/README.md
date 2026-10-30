# ExPenis observability

Application telemetry is technical only. No bodies, tokens, financial values,
user identifiers, full URLs/query strings or arbitrary exception text are exported.
Backend local file/console logs use the same allowlist; Collector does not tail
historical log files. Web/Android delivery is best effort and memory-only.

## Configuration

Backend production enables collection by default. Development/tests are disabled
unless `EXPENIS_TELEMETRY_ENABLED=true` is set explicitly. Use `EXPENIS_ENV=test`
for isolated tests; production alert queries filter `environment=production`.

| Variable | Default | Meaning |
| --- | --- | --- |
| EXPENIS_TELEMETRY_ENABLED | true in production | Master collection switch |
| EXPENIS_OTLP_ENDPOINT | http://127.0.0.1:4318 | Loopback Collector only |
| EXPENIS_TRACE_SAMPLE_RATE | 1 | Root sampling probability, 0–1 |
| EXPENIS_TELEMETRY_QUEUE_BYTES | 8388608 | Queue bytes, configurable downward |
| EXPENIS_TELEMETRY_SOURCE_RATE | 30 | Batches/minute/source, max 300 |
| EXPENIS_TELEMETRY_GLOBAL_RATE | 300 | Batches/minute/process, max 3000 |

The service uses one backend worker as in the existing deployment. Rate-limit and
dedup caches are bounded and process-local. Scaling workers requires revisiting
the shared ingestion limits; no distributed rate limiter is introduced.

Invalid exporter URLs, sampling values or numeric limit configuration disable
automatic collection instead of preventing application startup. The backend emits
one local `telemetry_config_invalid` warning on startup without configuration
values. Fix the environment and restart to resume collection.

Flutter release Web/Android collects by default. Override with
`--dart-define=EXPENIS_TELEMETRY_ENABLED=false`; debug opt-in uses `true`.
`--dart-define=EXPENIS_TRACE_SAMPLE_RATE=...` must match the backend rate.
iOS/desktop collection is always disabled. Defaults are build-time constants;
turning backend ingestion off immediately stops accepting new client data.

Client queue: at most 200 records/1 MiB; batches at most 50 records/~60 KiB.
Each record is at most 8 KiB. Flush every 5 seconds; at most 2 retries after the
initial attempt. No credentials or trace headers are attached to the delivery
transport. Delivery failure never initiates refresh, recursive reporting or UI.
Spans with backwards timestamps or durations over 15 minutes are dropped locally
before batching. A server schema rejection remains terminal for the whole batch;
there is no partial-ingestion response or 422 retry amplification.

`GET /api/health/ready` reads the configured existing SQLite schema within 1 second:
200 `{"status":"ready"}`, otherwise 503 `{"status":"not_ready"}`. Exporter failure
does not change readiness. `/metrics` is loopback-only and is not exposed by Caddy.
Business requests return `X-Request-ID` when telemetry is enabled.

`POST /api/telemetry` is public, supports JSON schema v1 (see `docs/openapi.json`),
rejects unknown fields, oversized/stale records and compressed bodies. Status 202
means accepted into a memory queue, not persistence. Status 204 means disabled.
400/413/415/422 are terminal; 429/503 include Retry-After. Do not put API tokens
or a shared ingestion secret into the Flutter release.

## Existing infrastructure

Keep shared Grafana/VictoriaMetrics/VictoriaLogs. Logs retain 30 days initially;
if aggregate storage measurements fail the budget, reducing shared log retention
to 14 days for all sources is authorized. Traces target 7 days; metrics keep
3 months. Resource limits take priority over completeness/retention.

Shared systemd/Collector/Tempo/storage configuration is in the private infra repo:
`monitoring/cloud/expenis-observability/`. Nothing here installs/reconfigures shared
services automatically. Grafana remains reachable through the existing SSH tunnel.

Pinned compatibility lab: Collector Contrib 0.140.0, Tempo 2.9.0, VictoriaLogs
1.52.0, Grafana 13.2.1, VictoriaLogs datasource plugin 0.33.1. Python versions are
locked by `uv.lock`. Tempo local storage has no HA/durability guarantee; object
storage, recommended by Tempo for production, is intentionally outside this small
self-hosted diagnostic budget.

## Project provisioning

- `scrape.yml` → `/etc/victoria-metrics/scrape.d/expenis.yml`.
- `dashboard-provider.yml` → Grafana dashboard provisioning root.
- `dashboard.json` → `/etc/grafana/provisioning/dashboards/expenis/dashboard.json`.
- `datasources.yml` → Grafana datasource provisioning; install the pinned
  VictoriaLogs plugin first. Uses stable UIDs `expenis-logs`/`expenis-traces`.
- `alerts.json` → `/etc/grafana/provisioning/alerting/expenis.yml` (JSON is valid YAML). Existing metrics UID
  `P4169E866C3094E38` must still refer to the shared VictoriaMetrics datasource.
- `generate_provisioning.py` regenerates dashboard/rules; thresholds are deliberately
  visible there and in generated config for review. No contact point credentials
  are stored in the project.

Readiness failure: 3 minutes. Backend 5xx: at least 5 AND at least 20% in the same
5-minute window (5/25 qualifies; 5/26 and 4/20 do not). Client errors: at least 3
distinct event IDs/fingerprint/platform/version in 10 minutes. Expected 4xx and
single errors do not page. Client signals are untrusted reports. Empty client
error groups mean no reported errors; datasource errors/scrape failure are shown
separately and do not imply healthy recovery.

Infra notification policy must group ExPenis client alerts by fingerprint,
platform and app_version, with the existing Telegram receiver/repeat/recovery.
No duplicate backups, contact points or monitoring stack are created.

## Rollout and rollback

1. Refresh resource/version baseline; validate the whole shared 30d log workload,
   data-volume hard caps, new service memory, query/compaction load and all
   additional binaries/plugin/venv/metrics/local-log growth within 1 GB RAM /
   2 GB additional disk. Passing small lab checks does not establish peak capacity.
2. Follow private infra storage migration instructions, retaining the original
   log store until verification. Provision Collector/Tempo/Grafana and verify
   loopback listeners, quotas, alert queries and trace/log links.
3. Deploy backend before Web/Android; regenerate OpenAPI for the backend version.
   Follow the repository release workflow for frontend version/notes/tag.
4. Validate Web AND Android, including 401→refresh→retry, handled/unhandled errors,
   SQLite outage, exporter outage, overflow, Telegram firing/recovery and budget.
5. Roll back by disabling collection, stopping only new services and removing only
   new project provisioning. Revert the VictoriaLogs storage override to its
   preserved original path when necessary. Do not touch domain data or backups.

When `/run/expenis-observability/paused` exists, backend export/admission is disabled
and metrics returns 503 to halt additional ExPenis metric ingestion. Readiness and
business operations continue. Inspect the guard/capacity, not business payloads;
clear the marker only after budget verification. Client reports can be lost while
paused. Never enlarge volumes/limits automatically or remove active Tempo WAL.

## Verification

Regression tests live in `tests/test_observability.py`,
`tests/test_monitoring_provisioning.py` and Flutter `test/telemetry_service_test.dart`.
Acceptance results are recorded in the OpenSpec change. One-off lab, fault and
native acceptance scripts are excluded from the maintained deployment files.
