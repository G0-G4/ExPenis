# Implementation verification — 2026-10-30

## Implemented locally

Backend: allowlisted local/OTLP logs, bounded delivery queue, ASGI request/trace context,
async SQLite and outbound HTTP spans, anonymous bounded telemetry intake, readiness,
Prometheus metrics (backend and explicitly sampled client observations). API schemas,
operation IDs, correlation header documentation and backend version were updated.

Web/Android: opt-in/out initialization, framework/runtime error capture, bounded
memory-only delivery, HTTP attempts and logical-operation spans, refresh/retry
causality and coalesced-refresh span links. Existing UI strings and auth flow remain.
No automatic iOS/desktop collection or product analytics were added.

Prepared project Grafana dashboard, alert/scrape/datasource provisioning, private
infra units/storage guard/migration instructions and frontend release notes.
Version preparation: backend 1.2.0; frontend 1.2.0+10. No commit, tag, GitHub release
or production deployment was performed.

## Evidence

- Backend full suite: 74 tests passed (8 warnings); final output:
  `/private/tmp/expenis-observability-final-pytest.txt`.
- Flutter full suite: 58 tests passed; analyzer reported no issues. Includes sampling,
  safe stack locations, queue bounds, successful/failed refresh and coalescing.
- New Python observability/logging modules: targeted mypy passed with dependency
  imports followed silently and missing third-party stubs ignored.
- Full `mypy src`: 10 errors (Peewee stubs and duplicate package names). The same
  10 errors were reproduced from an isolated archive of original `HEAD`; baseline
  output: `/private/tmp/expenis-mypy-baseline.txt`. No unrelated typing refactor made.
- Web release compilation succeeded. Android unsigned release compilation succeeded
  with installed JDK 17; signed local build could not validate the configured missing
  keystore. Existing release CI uses its own signing secrets; they were not read.
- Real local OTLP pipeline: client batch → API → Collector 0.140.0 → VictoriaLogs
  1.52.0 / Tempo 2.9.0. Client/server/DB parent IDs and trace/log correlation verified.
- Disposable Grafana 13.2.1 with VictoriaLogs plugin 0.33.1: datasource health,
  dashboard import, client grouping by platform/version/fingerprint and counts
  1 → 2 → 3 verified. No production contact point or Telegram notification triggered.
- Headless Chrome UI: synthetic login, first-party trace headers, expired-token
  refresh/retry, handled 500, SQLite readiness failure and sanitized error delivery
  passed against a dedicated temporary SQLite/backend.
- Android: separate `ru.g0g4.expenis.telemetrytest` app in `emulator-5580` with temporary
  userdata; login, refresh/retry and controlled DB failure passed. A separate test-only
  entrypoint exercised actual framework and unhandled error delivery. The connected
  unauthorized physical phone was not used. No debug hooks were added to normal main.
- Screenshots of synthetic UI: `/private/tmp/expenis-observability-e2e/web.png` and
  `/private/tmp/expenis-observability-e2e/android.png` (temporary, not release assets).
- Fixed-size ext4 image test in an unprivileged disposable Linux container returned
  allocation failure and retained exactly 64,000,000 bytes. This proves image capacity,
  not production mount/compaction safety or a sustained whole-host resource profile.
- Private infra budget guard: two standard-library tests passed, covering early
  admission pause and fail-closed behavior when baseline is missing.

## Follow-up acceptance checks — 2026-10-30 20:25–20:45 UTC

- Real Collector stop: 40 concurrent database-backed business requests returned 200
  in 0.249 s; readiness stayed 200. A 4 KiB queue dropped 68 records and counted
  3 export failures. 100 malformed batches returned five 422 and ninety-five 429;
  the privacy canary was absent from responses and local logs. DB fault returned
  readiness 503, recovery returned 200. Shutdown took 0.345 s; restart was ready.
  Reproducer: `deploy/monitoring/check_resilience.py`; report:
  `/private/tmp/expenis-observability-e2e/resilience-result.json`.
- Actual VictoriaMetrics/Grafana evaluator: 5/25 → 1, 5/26 → 0, 4/20 → 0,
  recovery 0/25 → 0. The unchanged production expression ignored the test series.
  Reproducer: `check_alerts.py`; report: `alerts-result.json` in the same temp dir.
- Actual headless Chrome Grafana navigation: log → Tempo → related logs, exact
  environment/trace filters and missing-trace message passed. Added the missing
  reverse link to the disposable datasource config and environment to both configs.
  Reproducer: `check_navigation.py <pipeline-trace-id>`; screenshots:
  `grafana-trace.png`, `grafana-related-logs.png`, `grafana-missing-trace.png`.
  Synthetic pipeline trace: `7b6c89e2cc8b0611f728356bfd58b223`.
- Retained actual UI traces have complete parent trees and a single error occurrence:
  Web error `7d2eb9f3a897388d50e50711b381c89c`, refresh/SQLite
  `9b786d19e2f939df51e2ee71d7cb31b2`; Android refresh/retry/error/SQLite
  `f397d52e753b1b7ee2dc7106f7ba294b`. Reproducer: `check_ui_correlation.py`;
  report: `ui-correlation-result.json` in the temp dir.
- Separate fault Web bundle delivered exactly one framework and one guarded-zone
  unhandled error, without exception messages or account credentials. The first
  test entrypoint scheduled a timer outside the application zone; corrected the
  test to create timers inside its frame callback. Normal application main was
  not changed. Reproducer: `check_web_faults.py`; report `web-fault-result.json`.
- Existing Telegram bot/chat loaded over SSH into memory, used by disposable
  Grafana, never printed or committed. Its evaluator produced three synthetic
  alerts grouped into two firing and two recovery notifications; Telegram failure
  counter did not increase. Test rules/folder/policy/receiver were deleted. The
  first checker used obsolete metric names; corrected for Grafana 13 and reran
  successfully with explicit verification of group sizes 1 and 2. Initial and
  final runs both sent test notifications. Reproducer: `check_telegram.py`.
- Real mounted 400,000,000-byte ext4 image: overflow returned ENOSPC, size stayed
  fixed, filesystem check passed, outside canary survived. The first container
  exited with signal 137 under a 128 MiB limit; a direct-I/O repeat with 640 MiB
  passed. Reproducer: `check_storage.sh` in a disposable Linux container with
  mount/loop privileges and an empty owned `/work` bind directory. This is a
  filesystem test, not application compaction or aggregate RAM acceptance.
- Test Grafana exhausted its initial 512 MiB cgroup with plugin/database tmpfs;
  disposable UI lab limit raised to 1 GiB. That lab-only change does not change
  production budgets or prove Grafana plugin memory growth fits them. Observed
  lab usage included Tempo ~100 MiB and Collector ~35 MiB; no peak guarantee.
- Cloud read-only refresh at 20:31 UTC: available RAM 2,800,410,624 bytes; free
  root disk 12,222,664,704 bytes. Backend/metrics/logs listen on loopback; new ports
  4318/4319/3200 remain unused. No production services/configuration were changed.
- Native `systemd-analyze verify` against temporary copies could not fully pass:
  planned Collector/Tempo executables are not installed. It also reported unrelated
  host unit warnings. Effective production cgroups were not tested.

## Remaining gates — not complete

OpenSpec progress: 27/31. Tasks 1.3, 6.3, 7.4 and 7.5 remain open. Telegram and
filesystem component checks passed, but full tasks include application compaction,
aggregate disk accounting/peak RAM, native units/effective cgroups and rollout.
A successful fixed-size image test does not establish the whole 2 GB budget.

Complete the native resource gate in an isolated Linux staging layout before
migrating the common log store or enabling production collection. In particular,
verify installed amd64 binary/plugin/dependency sizes, shared metrics/log growth,
compaction and recovery under the combined limits. Shared log retention remains
30d, with the authorized 14d fallback only if aggregate measurements require it.
No release/tag, native service installation, shared storage migration or production
rollout was performed. Existing backups remain unchanged.

## Permission review and cleanup

The earlier usage-limit failure was resolved after the user authorized continuing:
Docker/SSH checks ran successfully. The real Collector-stop test is now complete.
All owned temporary backend/Web processes ended. The disposable compose lab,
including its tmpfs Grafana database with temporary encrypted Telegram settings,
was removed successfully. Storage test mounts/containers/images were cleaned up.
Synthetic reports/screenshots remain in `/private/tmp/expenis-observability-e2e`.

## Native acceptance — 2026-10-31 Europe/Moscow

The subsequently authorized native cloud staging passed resource, compaction,
retention, quota/admission, stopped-writer reset and restart checks. Progress is
now 30/31; only release/rollout task 7.5 remains. Earlier remaining-gate notes
above describe the preceding checkpoint. See [native-acceptance.md](native-acceptance.md)
for measurements, fixes, limitations, durable evidence and confirmed cleanup.

## Review follow-up — 2026-10-31

See [review-resolution.md](review-resolution.md) for each finding and its disposition.
Latest local suites: backend 106 passed; Flutter 60 passed; Flutter analyzer clean;
targeted observability/logging mypy clean. Full mypy retains its 10 baseline errors.
No release or production deployment was performed during review fixes.
