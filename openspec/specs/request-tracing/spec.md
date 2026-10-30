# request-tracing Specification

## Purpose

Дать возможность проследить запрос Flutter Web или Android через backend и зависимости и перейти от трассы к связанным безопасным техническим логам.

## Requirements

### Requirement: First-party requests share a validated trace context

Instrumented Web and Android requests to the ExPenis API SHALL propagate W3C `traceparent`. The backend SHALL continue valid context and start a new trace when context is absent or malformed. It MUST NOT trust arbitrary baggage, external sampling flags or attribute values to bypass collection policy or limits. Each HTTP attempt SHALL have a distinct request/span identifier and expose a safe request identifier in its response. Older clients without tracing SHALL remain compatible.

#### Scenario: Client request reaches backend and database
- **WHEN** an instrumented client sends a valid first-party API request that reads SQLite
- **THEN** the trace contains the client attempt, child server span and database child spans with valid parent relationships
- **AND** associated logs carry the same trace ID and the attempt's request ID

#### Scenario: Context is absent or invalid
- **WHEN** an old client sends no trace context or a caller sends malformed identifiers
- **THEN** backend processing succeeds according to the existing API contract
- **AND** fresh valid context is generated without recording unsafe header contents

### Requirement: Refresh and retries preserve causality

An API operation that refreshes credentials and retries SHALL retain a common operation trace and SHALL record each original, refresh and retry HTTP attempt separately. Instrumentation MUST NOT cause recursive refresh, deadlock, duplicate HTTP attempts or changes to authentication behavior. HTTP outcomes SHALL include 4xx even when the client transport treats them as non-exceptions.

#### Scenario: Expired access token is refreshed
- **WHEN** an initial request receives `401`, refresh succeeds and the request is retried
- **THEN** one operation trace shows all three HTTP attempts in causal order with distinct spans and their actual statuses
- **AND** refresh/retry behavior remains unchanged

#### Scenario: Concurrent operation waits for a shared refresh
- **WHEN** another API operation or startup refresh already owns the single in-flight refresh
- **THEN** no duplicate refresh HTTP call is introduced
- **AND** the waiting operation links its trace to the owning refresh operation using trace/span identifiers, so the shared dependency can be followed across traces

#### Scenario: Expected login refusal
- **WHEN** login returns `401` for invalid credentials
- **THEN** its span records the HTTP outcome without initiating refresh or a technical-error alert

### Requirement: Dependencies are observable without payload capture

The backend SHALL trace awaited SQLite operations and outbound HTTP calls using safe operation names, durations and outcome/error codes. Raw SQL, query parameters, payloads, full URLs, credentials and unrestricted exception text MUST NOT be captured. External-service calls SHALL be visible as local outbound spans without propagating ExPenis trace headers or baggage to those services. Client update/version network calls SHALL record technical timing and outcome without injecting first-party context into third-party requests.

#### Scenario: Exchange-rate provider fails
- **WHEN** the backend calls an external exchange-rate provider and the call fails
- **THEN** the request trace includes an outbound span identifying the allowlisted provider and safe failure code
- **AND** provider requests carry no ExPenis trace headers and stored attributes contain no keys, query values or response data

### Requirement: Sampling and exclusions are explicit

The initial sampling rate SHALL be 100% of eligible first-party operations and SHALL be configurable consistently across client and backend. Server sampling decisions SHALL follow configured policy rather than client permission to exceed it. Readiness checks, metric scrapes and telemetry delivery SHALL be excluded from application tracing and business request/error metrics. Sampling and bounded delivery SHALL be documented as independent reasons why an individual trace can be incomplete.

#### Scenario: Collection observes its own delivery
- **WHEN** a client sends telemetry or monitoring polls readiness/metrics
- **THEN** those requests create no recursive application spans and do not change business HTTP error-rate calculations

### Requirement: Operators can correlate traces and logs

Grafana SHALL support opening a trace from an application log's trace ID and finding related application logs from a trace. Queries SHALL distinguish environment, backend/frontend component, supported platform and application version without using personal identifiers.

#### Scenario: Operator investigates a client failure
- **WHEN** an operator opens an ingested client error with a valid retained trace ID
- **THEN** the operator can inspect the related retained client/server/dependency spans and sanitized logs in Grafana
- **AND** absent or expired spans are shown as unavailable rather than implying a complete trace
