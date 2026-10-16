## Why

Analytics tag and category filters only see the loaded date range: tag chips are built from transactions in that range, and every period change resets all filters. A tag that lives outside the current month (a past trip, a renovation) cannot be selected at all, and there is no way to look at a tag over its whole lifetime or to keep a hand-picked set of categories while flipping through months.

## What Changes

- Tag and category filter selections survive period changes (month navigation, month picker, grouped range edits, toggling group-by-month) for as long as the analytics screen is open. Income and expense filters stay independent.
- Category filter gets two modes: **all** (default; categories that newly appear in another period are selected automatically) and **explicit set** (after any manual toggle; the set is kept as-is and new categories are not added). Select all returns to the all mode.
- No silent fallback to "all categories" when none of the selected categories exist in the new period: the view shows an empty state and keeps the selection.
- Tag filter shows every tag the user ever used on that view's type (income or expense). Tags present in the current period come first; tags absent from it are dimmed and collapsed under "N more".
- When included tags have transactions outside the current range, a hint appears with the tags' combined period and a "Show period" action. The action sets the range to exactly that combined period, switching to single-month mode when it is one month and to group-by-month mode otherwise. Exclude-state tags never trigger the hint. The hint has no dismiss button and disappears once the combined period fits in the range.
- `GET /api/tags` additionally returns, per tag and per transaction type, the timestamps of the first and last tagged transaction. The existing `tags` field is unchanged.

## Capabilities

### New Capabilities

- `analytics-category-filter`: Category filtering on analytics income/expense views — all vs explicit-set modes, persistence across period changes, and the empty state when nothing matches.
- `tag-periods-api`: The tags endpoint reports when each tag was first and last used, split by income and expense.

### Modified Capabilities

- `analytics-tag-filter`: Tag states no longer reset on period change; tags outside the current period are listed; a hint offers to switch the range to the included tags' combined period.

## Impact

- Backend: `src/expenis/core/service/transaction_service.py` (tag period aggregation), `src/expenis/server/dto.py` (`UserTagsResponse`), `src/expenis/server/application.py` (`/api/tags`), `tests/transaction_service_test.py`, regenerated `docs/openapi.json`, backend version bump in `pyproject.toml`. No schema migration.
- Frontend: `frontend/lib/screens/transaction_stats_screen.dart` (filter state, reload, range switch), `frontend/lib/widgets/analytics_filters_card.dart` (out-of-period tags, hint), `frontend/lib/service/transaction_service.dart` + a model for tag periods, `frontend/lib/utils/selection_utils.dart` / `tag_utils.dart` helpers and their tests.
- `fetchTags()` callers (edit transaction screen autocomplete) keep working unchanged.
