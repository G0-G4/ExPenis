# application-monitoring Specification

## Purpose

Обеспечить проверяемую готовность ExPenis, отдельный dashboard и полезные алерты в существующем стеке с ограниченным потреблением ресурсов общего сервера.

## Requirements

### Requirement: Readiness includes database availability

`GET /api/health/ready` SHALL return `200` with `{"status":"ready"}` only after a bounded read against the configured SQLite database succeeds. On failed or timed-out access it SHALL return `503` with `{"status":"not_ready"}`. It SHALL require no user authentication, write no domain data, disclose no paths/errors/credentials and remain independent of exporter availability. The monitoring system SHALL probe this endpoint in addition to existing external HTTP checks.

#### Scenario: HTTP works but SQLite is unavailable
- **WHEN** the web server accepts HTTP but the database read fails or times out
- **THEN** readiness returns `503` with only the generic readiness response
- **AND** the readiness alert can activate without depending on business traffic

#### Scenario: Monitoring storage is unavailable
- **WHEN** SQLite is usable but the telemetry exporter is unavailable
- **THEN** readiness remains `200`
- **AND** exporter failure is exposed separately

### Requirement: Dashboard reuses existing infrastructure

An ExPenis dashboard SHALL use the existing Grafana, VictoriaMetrics and VictoriaLogs plus a self-hosted trace store. It SHALL show backend/readiness status, request rate, 5xx count/ratio, latency percentiles, dependency timing/errors, backend process health, client error groups by platform/version, telemetry delivery health and trace/log navigation. It SHALL distinguish missing/stale collection from a healthy zero-error interval. No external SaaS or duplicate backup dashboards/alerts SHALL be introduced. Grafana SHALL retain existing SSH-tunnel access; metric/collector/storage listeners SHALL be loopback-only and not publicly proxied.

#### Scenario: No traffic differs from missing monitoring
- **WHEN** a time window contains no business requests but successful fresh scrapes
- **THEN** the dashboard shows zero request activity without a false 5xx alarm
- **AND** failed or stale scrapes show a separate unavailable/no-data state

### Requirement: Alerts are actionable and scoped

Production alerts SHALL use the existing Grafana Telegram contact point, grouping, repeat suppression and recovery notifications. An availability/readiness alert SHALL fire after continuous failure for 3 minutes. A backend error alert SHALL fire when the same rolling 5-minute window contains at least 5 business responses with status 5xx and a 5xx ratio of at least 20%. A repeated-client-error alert SHALL fire at 3 distinct ingested occurrences of the same technical fingerprint/platform/version in a rolling 10-minute window. These thresholds SHALL be configurable. Expected 4xx and single client errors SHALL not trigger these error alerts. No-data conditions SHALL not be presented as recovery or a healthy application.

#### Scenario: Backend error count and ratio thresholds
- **WHEN** the 5-minute window contains 5 server errors out of 25 business responses
- **THEN** the backend error alert activates
- **AND** 4 errors, or 5 errors out of 26 responses, do not satisfy both thresholds

#### Scenario: Repeated client failure
- **WHEN** three distinct error occurrences with the same fingerprint, platform and version are accepted within 10 minutes
- **THEN** one grouped client-error notification is eligible
- **AND** retries of the same event identifier do not increase the count

#### Scenario: Recovery and development isolation
- **WHEN** a production alert clears or a matching error occurs only in a development environment
- **THEN** the first case produces a grouped recovery notification and the second produces no production error alert

### Requirement: Retention respects a fixed resource budget

Target retention SHALL be the existing shared 30 days for logs, 7 days for traces and the existing 3 months for metrics. If resource verification shows that 30-day shared log retention cannot fit, the shared log retention SHALL be reduced to 14 days for all log sources. New components SHALL consume at most 1 GB RAM in aggregate and all additional observability disk usage SHALL stay within 2 GB including trace data, application log growth, metric growth and temporary/queue files. Resource limits SHALL take priority over retention and completeness; older diagnostic data can be discarded early. Actual host capacity and enforcement of the limits SHALL be verified before rollout; limits MUST NOT be increased automatically. Unrelated metric and trace data/retention MUST NOT be deleted or shortened to satisfy the ExPenis budget. Shared log retention can be reduced from 30 to 14 days as explicitly authorized; bounded shared log storage can expire older logs early.

#### Scenario: Data volume exceeds the budget
- **WHEN** observability data approaches its configured disk or memory bound
- **THEN** bounded ingestion and eviction/drop mechanisms keep use within the approved budget, allowing earlier loss of diagnostic data
- **AND** application availability and unrelated metric/trace data are preserved; shared logs follow the authorized common retention policy

#### Scenario: Host cannot accommodate the deployment
- **WHEN** pre-deployment checks cannot demonstrate spare capacity and effective budget enforcement
- **THEN** rollout is stopped for a revised design rather than silently expanding resources

### Requirement: Rollout is verifiable and reversible

Deployment SHALL include verification on Web and Android of an end-to-end request, auth refresh/retry, a sanitized error, database readiness failure, Telegram activation/recovery and bounded behavior during exporter failure. Operators SHALL have instructions to disable collection, remove only new provisioning and stop new components without a domain-data migration or changes to existing backups.

#### Scenario: Observability must be rolled back
- **WHEN** an operator disables collection and rolls back the new monitoring provisioning
- **THEN** existing API and client operations remain usable and existing infra monitoring/backups continue operating
