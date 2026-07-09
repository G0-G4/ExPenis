# AGENTS Guide for `expenis`
This file gives coding agents practical commands and style conventions for this repository.
## 1) Project Snapshot
- Language/runtime: Python 3.13+
- Dependency manager: `uv`
- Main components:
  - FastAPI backend in `src/expenis/server`
  - Core domain/services in `src/expenis/core`
  - Flutter app in `frontend/` (web/iOS/Android/desktop)
  - Async SQLite access via `playhouse.pwasyncio`
  - DTOs with Pydantic
- Tests: `pytest`, `pytest-asyncio`
- Infra helpers: `docker-compose`, `just`
Key paths:
- `src/expenis/core/` — models, services, helpers, domain errors
- `src/expenis/server/` — FastAPI app + API DTOs
- `frontend/` — Flutter app: `lib/`, `pubspec.yaml`, platform dirs. See `frontend/AGENTS.md` for Flutter conventions.
- `flutter_web/` — built web bundle (gitignored, produced via `just flutter-build`).
- `tests/` — async tests and shared fixtures
- `pyproject.toml` — dependencies and pytest settings
- `justfile` — compose and lockfile commands (run via `just <recipe>`)
- `migrations/` — schema migrations as numbered SQL files `NNN_description.sql`. When modifying peewee models in `src/expenis/core/models/`, add a new migration file here; do not edit existing migrations.
- `migration.py` — one-off data migration script (transactions from legacy schema), not used for schema changes.
### Clients
- Flutter app lives in `frontend/`. Built web bundle is produced by `just flutter-build` into `flutter_web/` (gitignored) and deployed via `Dockerfile.frontend` + nginx.
## 2) Setup / Build / Run
Run commands from repo root.
### Environment setup
- Install/sync dependencies: `uv sync`
### Local app startup
- Run FastAPI server: `uv run -m src.expenis.server`
- Run Flutter app (debug): `cd frontend && flutter run`
- Build Flutter web bundle into `flutter_web/`: `just flutter-build`
### Docker helpers
- Start services: `just up`
- Stop services: `just down`
- Build images: `just build`
- Follow logs: `just logs`
### Lockfile maintenance
- Rebuild lockfile: `just lock`
### Releases and app auto-update
- App version lives in `frontend/pubspec.yaml` (`version: X.Y.Z+build`). The git
  tag `vX.Y.Z` (semver, no leading `v` in `pubspec`) marks a release and MUST
  match the `pubspec.yaml` version. The build number (`+build`) is not part of
  the tag.
Before publishing a release — REQUIRED:
1. Bump `version:` in `frontend/pubspec.yaml` (major/minor/patch + build
   number, e.g. `1.0.0+1` → `1.0.1+2`). This is the single source of truth the
   app reads via `package_info_plus` on the device.
2. Commit the version bump.
3. Run `just release-tag` — parses the version from `pubspec.yaml`, creates git
   tag `vX.Y.Z`, and pushes it. Do not tag manually with a mismatched version.
4. The push triggers `.github/workflows/release.yml`: builds a release APK
   (`ExPenis-X.Y.Z.apk`) and Flutter web zips (`ExPenis-X.Y.Z-web.zip` plus
   stable `ExPenis-web.zip` for easy latest download), then creates a GitHub
   Release with those assets and auto-generated notes.
Never forget step 1 — bumping `pubspec.yaml` version before tagging. A tag that
does not match the installed version breaks semver comparison in `UpdateService`
and the app will not detect the update.
### Deploy web from GitHub Release (server, no Flutter SDK)
Public repo — no auth. On the server after a release is published:
```bash
just flutter-fetch-deploy
```
This curls the stable latest asset, unpacks into `flutter_web/`, and
rebuilds/restarts the nginx frontend container. Equivalent manual steps
(`curl` + `unzip`):
```bash
curl -fsSL -o /tmp/expenis-web.zip \
  https://github.com/G0-G4/ExPenis/releases/latest/download/ExPenis-web.zip
rm -rf flutter_web && mkdir -p flutter_web
unzip -o /tmp/expenis-web.zip -d flutter_web/
docker-compose build frontend && docker-compose up -d frontend
```
Local build remains available: `just flutter-build` / `just flutter-deploy`.
Auto-update behavior (Android): on startup in release mode, `UpdateService`
fetches `/releases/latest` from GitHub and compares semver with the installed
version; if newer, `UpdateDialog` offers to download the `.apk` asset and
launches the Android package installer via a MethodChannel. Non-Android
platforms get an "Open" button that opens the release page via `url_launcher`.
No GitHub API tokens are used (public repo API, 60 req/hr per IP — sufficient
for a startup check).
Key paths:
- `frontend/lib/service/update_service.dart` — release check + APK download/install
- `frontend/lib/widgets/update_dialog.dart` — update prompt UI
- `frontend/android/app/src/main/kotlin/ru/g0g4/expenis/MainActivity.kt` —
  MethodChannel `expenis/installer` (`installApk` method)
- `.github/workflows/release.yml` — release CI (APK + web zip)
- `justfile` recipes `release-tag`, `flutter-fetch-deploy`
## 3) Test Commands (Use These)
Pytest settings (from `pyproject.toml`):
- `asyncio_mode = "auto"`
- `asyncio_default_fixture_loop_scope = "function"`
### Run full test suite
- `uv run pytest`
### Run one test file
- `uv run pytest tests/test_account_service.py`
### Run one test function (most important)
- `uv run pytest tests/test_account_service.py::test_basic_crud`
- Examples:
  - `uv run pytest tests/session_service_test.py::test_create_session`
  - `uv run pytest tests/transaction_service_test.py::test_get_transactions_for_period`
### Filter tests by keyword
- `uv run pytest -k session`
- `uv run pytest -k "basic_crud and not category"`
### Useful pytest flags
- Verbose: `uv run pytest -v`
- Stop on first failure: `uv run pytest -x`
- Show stdout/logs: `uv run pytest -s`
### Test isolation notes
- `tests/conftest.py` truncates core tables before each test via an autouse fixture.
- Async tests should use `@pytest.mark.asyncio`.
- Keep tests deterministic and order-independent.
## 4) Lint / Type / Quality Checks
No repository-level linter/formatter config was found (`ruff`, `black`, `isort`, `flake8`).
Recommended checks after edits:
- Type-check source: `uv run mypy src`
- Run tests: `uv run pytest`
If introducing tooling, keep it aligned with current style and avoid broad format-only diffs.
## 5) Code Style Guidelines
Follow existing local patterns first. Prefer minimal, focused diffs.
### Imports
- Order imports as: stdlib -> third-party -> local package imports.
- Remove unused imports in touched files.
- Use multiline imports when they improve readability.
### Formatting
- Use 4-space indentation.
- Keep lines readable (target roughly 88-100 chars unless file style differs).
- Prefer trailing commas in multiline structures/calls.
- Add comments only for non-obvious logic.
- Preserve language/style of existing user-facing strings in touched files.
### Types and annotations
- Keep explicit parameter and return type hints on public functions.
- Prefer concrete types (`list[Transaction]`, `dict[int, AccountDto]`).
- Use `Literal[...]` for closed value sets (e.g., category/session status).
- Avoid `Any` unless unavoidable.
### Naming
- Functions/variables/modules: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- API DTO naming convention: `*CreateRequest`, `*UpdateRequest`, `*Response`, `*Dto`
### Async + database usage
- Keep DB interactions async (`await db.run(...)`, `await db.list(...)`).
- Use `async with db.atomic():` for related writes requiring consistency.
- Keep peewee queries readable; split long chains when needed.
- Prefer timezone-aware timestamps via `datetime.now(UTC)`.
### Error handling
- Use domain exceptions in core/service layer (e.g., `NotFoundException`).
- Convert to API-facing errors at FastAPI boundary (`HTTPException` as needed).
- Validate input early (DTO validators and explicit checks).
- Do not swallow exceptions silently.
### API/server conventions
- Keep route handlers thin; delegate business logic to services.
- Keep conversion helpers deterministic and side-effect free.
- Ensure user-scoped operations consistently filter by `user_id`.
### Tests
- Use clear arrange/act/assert structure.
- Reuse fixtures for setup.
- Add/update tests alongside behavior changes.
- Prefer precise test names that describe expected behavior.
## 6) Agent Working Agreements
- Do not include unrelated refactors in functional changes.
- Do not rename files/modules without a clear need.
- Do not add dependencies without strong justification.
- Keep edits architecture-consistent with existing layers.
- Run targeted tests for local changes; run full suite for broad changes.
## 7) Cursor / Copilot Rule Check
At generation time, these rule files were not found:
- `.cursorrules`
- `.cursor/rules/`
- `.github/copilot-instructions.md`
If they appear later, treat them as higher-priority instructions and update this guide.

## 8) Practical Agent Workflow

Use this checklist when implementing changes:

1. Read the touched service/module and nearest tests before editing.
2. Make the smallest change that solves the requested behavior.
3. Keep business logic in `src/expenis/core/service`, not in API handlers.
4. Update/extend tests with behavior changes.
5. Run the narrowest meaningful test command first.
6. Run broader tests if core/shared logic changed.

Suggested progression:

- Single function change: run one test function first.
- One service file change: run related test file.
- Shared model/service change: run full suite.

## 9) Service-Layer Guardrails

- Keep user scoping explicit (`user_id`) in read/update/delete operations.
- Prefer helper functions for repeated query shapes.
- Use UTC timestamps consistently for create/update operations.
- Avoid mixing transport concerns (HTTP, Telegram payload shape) into core services.
- Keep return values stable and typed so callers remain predictable.

## 10) API and DTO Guardrails

- Validate request data in DTOs where possible.
- Keep endpoint conversion helpers pure and deterministic.
- Return consistent response models from each route.
- Do not perform unrelated persistence side effects in conversion helpers.

## 11) Test Authoring Patterns

- Name tests for behavior, not implementation details.
- Prefer explicit values over random data unless randomness is required.
- Assert both happy path and failure path for new behavior.
- Keep fixtures lightweight and reusable.
- Do not rely on existing DB state across tests.
