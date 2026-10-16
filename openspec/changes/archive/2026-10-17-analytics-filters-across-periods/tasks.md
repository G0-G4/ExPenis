## 1. Backend: tag periods

- [x] 1.1 Add `get_user_tag_periods(user_id)` in `src/expenis/core/service/transaction_service.py` (one grouped query, MIN/MAX `created_at` per tag name and category type, scoped by `user_id`); verify with new tests in `tests/transaction_service_test.py` covering expense-only, both types, unused tag, and another user's transactions — `uv run pytest tests/transaction_service_test.py`
- [x] 1.2 Add `TagPeriodDto` and `tag_periods` to `UserTagsResponse` in `src/expenis/server/dto.py` and fill it in the `/api/tags` handler; verify `uv run pytest` and `uv run mypy src` pass
- [x] 1.3 Bump backend version in `pyproject.toml` and run `just openapi`; verify `docs/openapi.json` shows `tag_periods` and the new version

## 2. Frontend: data and helpers

- [x] 2.1 Add a `TagPeriod` model and `fetchTagPeriods()` (or extend the tags fetch) in `frontend/lib/service/transaction_service.dart` without changing `fetchTags()`; verify edit-transaction autocomplete still compiles and `flutter analyze` is clean
- [x] 2.2 Add `combinedTagPeriod(includedKeys, periods)` to `frontend/lib/utils/tag_utils.dart` (local months, includes only); verify unit tests in `frontend/test/tag_utils_test.dart` for single tag, union of two tags, unknown key, and empty includes
- [x] 2.3 Add category-filter helpers in `frontend/lib/utils/selection_utils.dart` for all/explicit mode (effective selection for a period, toggle from all mode, select all, clear all); verify unit tests in `frontend/test/selection_utils_test.dart` for the four category spec scenarios

## 3. Frontend: analytics screen state

- [x] 3.1 Replace category selection state with nullable explicit sets per view and remove `_resetFiltersForReload()` and `intersectOrAll` trimming from `_loadData()`; verify by navigating months in the running app that category and tag selections persist and income/expense stay independent
- [x] 3.2 Load tag periods once on screen open and build per-view chip lists as in-period ∪ out-of-period tags of that type; verify a tag from an earlier month appears dimmed on the matching view only
- [x] 3.3 Show the empty state "No transactions match the selected filters" when filters exclude everything in the period; verify by selecting a category absent from a month

## 4. Frontend: UI

- [x] 4.1 Extend `AnalyticsFiltersCard` with out-of-period tag keys: dimmed chips after in-period ones, collapsed under "N more", selected ones always visible; Select all includes in-period tags only and clears excludes, Clear all idles everything; verify visually in the running web app
- [x] 4.2 Add the period hint (tag names + combined period + "Show period") above the analytics content when the combined period exceeds the range, and wire "Show period" to switch mode and range per the spec; verify the three tag-hint scenarios (single tag, widening second tag, exclude-only) in the running app

## 5. Quality checks

- [x] 5.1 Run `flutter test` and `flutter analyze` in `frontend/` and confirm both pass
- [x] 5.2 Run `uv run pytest` and `uv run mypy src` and confirm both pass
- [x] 5.3 Run `just e2e` against the local dev stack and confirm existing smokes still pass
