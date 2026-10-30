## Purpose

Обеспечить безопасный сбор технических событий и метрик backend, Flutter Web и Android без влияния отказов наблюдаемости на работу приложения.

## ADDED Requirements

### Requirement: Technical telemetry follows an allowlist

The system SHALL export only approved technical fields: event code/type, sanitized stack frames, severity, timestamp, environment, component, application version, platform, normalized route/operation, HTTP method/status, duration, random event/request/trace/span identifiers and bounded retry metadata. It MUST NOT export financial values, account/category/tag names, transaction descriptions, request/response bodies, query strings, SQL statements/parameters, credentials, cookies, personal identifiers, client IP addresses or arbitrary exception messages. These restrictions SHALL also apply to existing application, access and dependency logs, both local and exported.

#### Scenario: Existing sensitive logging is removed
- **WHEN** authentication fails, DTO validation fails or a transaction operation is logged
- **THEN** local and exported records contain no username, user ID, Telegram ID, submitted values, amounts, secrets or query strings
- **AND** a stable technical error code and sanitized stack frames remain available when appropriate

#### Scenario: Unknown fields or text contain private data
- **WHEN** telemetry contains undeclared fields or exception text embeds a token, email or transaction description
- **THEN** the receiver rejects undeclared fields and permitted output never includes the unsafe text

### Requirement: Backend provides bounded technical metrics

The backend SHALL expose request counts, response status classes, duration histograms, in-flight requests, dependency operation duration/errors, readiness, process health, and telemetry accepted/rejected/dropped/export-failure counts. Labels SHALL use bounded operation/route/status/environment/platform categories; individual identifiers, raw URLs, stack traces, arbitrary versions and error fingerprints MUST NOT become unbounded metric labels. Client-reported observations SHALL be distinguishable from backend observations.

#### Scenario: Requests address many individual resources
- **WHEN** requests target different transaction IDs or unknown URLs
- **THEN** metrics use a route template or one fixed unknown-route label
- **AND** request, trace and resource IDs do not create new time series

### Requirement: Client errors are captured once on supported platforms

Web and Android SHALL capture unhandled framework/runtime errors and handled technical failures of API operations. Each error occurrence SHALL have one random event identifier and SHALL be counted once across HTTP, service and global handlers. Expected business responses such as invalid credentials SHALL be recorded as HTTP outcomes without becoming repeated-client-error alerts. No user action history, screen contents or persistent device identity SHALL be collected.

#### Scenario: Error reaches multiple handlers
- **WHEN** one failed API operation is observed by HTTP, service and global error handling
- **THEN** one error occurrence is delivered and counted
- **AND** related spans remain available without duplicating the error count

#### Scenario: Failure happens before login
- **WHEN** Web or Android encounters a technical error before authentication
- **THEN** the event can be submitted without an account or embedded shared secret

### Requirement: Client ingestion has a documented bounded contract

`POST /api/telemetry` SHALL accept a versioned JSON batch of allowlisted error and completed span records without JWT authentication. It SHALL validate schema, sizes, identifier formats, timestamps and record counts before enqueueing, enforce global and transient per-source rate limits, and never persist source addresses. Unknown fields SHALL be rejected. Accepted batches SHALL return `202` with accepted record count; acceptance MUST NOT imply durable delivery. Invalid JSON SHALL return `400`, invalid schema `422`, oversized bodies `413`, unsupported media `415`, throttling `429` with `Retry-After`, and exhausted server capacity `503` with `Retry-After`. When collection is disabled, this endpoint SHALL return `204` without storing the batch. Public callers MUST NOT reach monitoring storage or arbitrary OTLP forwarding interfaces.

#### Scenario: Client submits a valid batch
- **WHEN** an unauthenticated client submits an in-limit supported batch while collection is enabled
- **THEN** it receives `202` and the count accepted into the bounded queue
- **AND** subsequent exporter failure does not change that response into a persistence guarantee

#### Scenario: Abusive or malformed submission
- **WHEN** a submission exceeds the body limit, contains unknown fields or exceeds its rate limit
- **THEN** it receives respectively `413`, `422` or `429`
- **AND** no rejected record is forwarded or logged with its submitted values

### Requirement: Telemetry delivery is bounded and independent of business work

Telemetry SHALL use bounded memory queues, bounded retry counts and short network/shutdown timeouts. Business requests and client startup MUST NOT await exporter delivery. Client queues SHALL be memory-only; oldest records SHALL be discarded on overflow. Delivery failures SHALL not recursively generate telemetry. Queue loss and exporter failure SHALL be visible in backend metrics; loss of client events SHALL be acknowledged as possible, including on process termination.

#### Scenario: Exporter remains unavailable
- **WHEN** ingestion storage is unavailable and queues fill
- **THEN** business operations still complete with their ordinary outcomes
- **AND** memory use remains bounded, oldest queued data is dropped, and backend drop/failure metrics increase

### Requirement: Collection is isolated by environment and platform

Automatic collection SHALL be enabled by default only in production for backend, Web and Android. Local/test collection SHALL require explicit configuration and a separate environment label and alert scope. iOS and desktop SHALL have no automatic collection under this change.

#### Scenario: Development or unsupported platform starts
- **WHEN** a development build starts without explicit opt-in, or an iOS/desktop build starts
- **THEN** no automatic telemetry is exported
- **AND** business functionality remains usable
