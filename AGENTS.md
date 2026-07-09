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
- `pyproject.toml` — dependencies, pytest settings, **and backend version** (see Releases below).
- `src/expenis/version.py` — helper that provides `__version__` (used by FastAPI and the OpenAPI spec).
- `justfile` — compose and lockfile commands (run via `just <recipe>`)
- `migrations/` — schema migrations as numbered SQL files `NNN_description.sql`. When modifying peewee models in `src/expenis/core/models/`, add a new migration file here; do not edit existing migrations.
- `migration.py` — one-off data migration script (transactions from legacy schema), not used for schema changes.
- `docs/openapi.json` — generated OpenAPI 3.1 spec (run `just openapi` after API changes). The `info.version` reflects the backend version from `pyproject.toml`.
- Long-lived tokens for agents: `just generate-agent-token` or `uv run -m src.expenis.server token --username llm-agent --days 365`. The user must already exist (the command will error if the username is not found).
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

### OpenAPI specification
- Generate (or regenerate) machine-readable API spec: `just openapi`
- Output: `docs/openapi.json` (committed)
- Used by agents/LLMs to build skills, clients, or tests for the backend service.
- All `operationId`, `summary`, `description` and tags are declared directly on the route decorators in `src/expenis/server/application.py` (using FastAPI `operation_id=...` / `summary=...` + a small `custom_openapi` hook for the security scheme). The generator is intentionally minimal.
- The spec includes grouped tags, friendly `operationId`s (e.g. `listTransactions`, `login`), Russian summaries for humans, and a documented `BearerAuth` JWT security scheme.
- `info.version` in the spec comes from `pyproject.toml` (backend version). Bump it only when the API contract changes.
### Releases and app auto-update

The frontend and backend use **independent versions**.

- **Frontend version** (`frontend/pubspec.yaml`, format `X.Y.Z+build`):
  - Drives Git tags (`vX.Y.Z`), GitHub Releases, APK/web artifact names.
  - Used by the mobile app for auto-update checks (via `package_info_plus` + GitHub releases).
  - This is the version that matters for end users and the release process.

- **Backend version** (`pyproject.toml`, e.g. `1.0.3`):
  - Used in the OpenAPI specification (`info.version`).
  - Exposed as `src.expenis.__version__` and in `FastAPI(version=...)`.
  - Reflects changes to the backend and API contract.

**You do not need to keep the versions in sync.**

It is normal for the versions to diverge. Example:
- `frontend/pubspec.yaml`: `1.2.0+5`
- `pyproject.toml`: `1.0.3`

The git tag `vX.Y.Z` is **always** taken from `pubspec.yaml` (the build number after `+` is ignored for the tag).

Before publishing a release — REQUIRED:
1. Bump `version:` in `frontend/pubspec.yaml` (major/minor/patch + build number).
2. (Optional) If the backend changed, bump `version = "..."` in `pyproject.toml`.
3. Commit the version bump(s).
4. Run `just release-tag` — parses the version from `pubspec.yaml`, creates git tag `vX.Y.Z`, and pushes it. Do not tag manually with a mismatched version.

The push triggers `.github/workflows/release.yml`: builds a release APK
(`ExPenis-X.Y.Z.apk`) and Flutter web zips (`ExPenis-X.Y.Z-web.zip` plus
stable `ExPenis-web.zip` for easy latest download), then creates a GitHub
Release with those assets and auto-generated notes.

**Note**: The release CI and auto-update logic only care about the frontend/pubspec version. The OpenAPI `info.version` will reflect whatever is currently in `pyproject.toml` when you last ran `just openapi`.
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
