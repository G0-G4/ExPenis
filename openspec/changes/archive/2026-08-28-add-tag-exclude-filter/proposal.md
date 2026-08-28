## Why

On the analytics income/expense screens, a tag chip is either off or inclusive: tapping it shows only transactions that have that tag. There is no way to hide transactions that carry a tag (for example exclude shared-split labels) without also dropping everything else. A third chip state fills that gap.

## What Changes

- Tag filter chips on analytics become three-state instead of two-state:
  1. **Idle** (default): the tag does not constrain the list.
  2. **Include** (existing): only transactions that have this tag (or another included tag) are shown.
  3. **Exclude** (new): transactions that have this tag are hidden.
- Tapping a chip cycles idle → include → exclude → idle.
- An excluded chip shows the tag name with strikethrough text.
- Include and exclude may be mixed across different tags on the same screen. Both apply at once: include is a whitelist, exclude punches holes, and a row with both an included tag and an excluded tag is hidden. Category filters, APIs, and tag editing are unchanged.

## Capabilities

### New Capabilities

- `analytics-tag-filter`: Tag filtering on analytics income/expense views, including idle, include, and exclude chip states and how they combine.

### Modified Capabilities

- (none — `openspec/specs/` has no existing capabilities)

## Impact

- Flutter analytics UI: `frontend/lib/widgets/analytics_filters_card.dart`
- Filter matching and tag selection state: `frontend/lib/screens/transaction_stats_screen.dart`
- Possibly `frontend/lib/utils/selection_utils.dart` / `frontend/lib/utils/tag_utils.dart` for tri-state helpers
- Frontend unit tests for matching and chip cycling
- No backend, OpenAPI, or database changes
- Applies to both income and expense tag filters (shared widget and matching logic)
