## Context

`TransactionStatsScreen` (`frontend/lib/screens/transaction_stats_screen.dart`) loads transactions for the current range in `_loadData()` and derives the available categories and tag chips from that slice only. Every range change calls `_resetFiltersForReload()`, which wipes category selections and tag include/exclude sets; after load, categories are re-seeded to "all" and stale selections are trimmed with `intersectOrAll` (falls back to all when the intersection is empty). `GET /api/tags` returns only names (`UserTagsResponse.tags`), used by the edit-transaction autocomplete. Transaction type comes from `Category.type`; transaction time is `Transaction.created_at` (UTC).

See proposal.md for motivation and specs for the required behavior.

## Goals / Non-Goals

**Goals:**
- One filter-state model per view that is independent of the loaded range.
- Tag period data from a single cheap backend query, loaded once per analytics screen.

**Non-Goals:**
- Persisting filters beyond the lifetime of the analytics screen (no local storage).
- Entry points into tag analytics from other screens (e.g. tapping a tag on a transaction).
- An "all time" period option.

## Decisions

### Category filter state: nullable explicit set

Represent each view's category filter as `Set<int>? explicitCategoryIds`: `null` = all mode, non-null = explicit set (possibly empty). The effective selection for a loaded period is `available` when `null`, otherwise `explicit ∩ available` for chip rendering, while matching uses the explicit set directly. Toggling a chip from all mode materializes `available` minus/plus the toggled id. Select all sets `null`; Clear all sets `{}`.

Alternative considered: storing deselected ids ("exclusion set"). Rejected after discussion — users who pick 3 categories expect new categories to stay out.

`intersectOrAll` stops being used for categories in this screen; remove it if it has no other callers.

### Tag state: unchanged sets, no trimming

Keep `_included*/ _excluded*TagKeys` as is but stop clearing them on reload and stop intersecting with the period's tags (tags outside the period are now legitimate selections). `_resetFiltersForReload()` is removed; range-change handlers just call `_loadData()`.

### Tag list: union of period tags and tag periods

The chip list for a view = tags from loaded transactions (in-period, normal) ∪ tags from tag periods of that type that are not in-period (dimmed). Keys use `normalizeTagKey`. The widget gets an extra `outOfPeriodTagKeys` set and renders those after the in-period chips inside a collapsible "N more" section; selected out-of-period chips are always rendered.

### Tag periods API

Extend `UserTagsResponse` with `tag_periods: list[TagPeriodDto]` where `TagPeriodDto = {name, type: Literal["income","expense"], first_at: datetime, last_at: datetime}`. Service function `get_user_tag_periods(user_id)` runs one grouped query: `TransactionTag` ⨝ `Tag` ⨝ `Transaction` ⨝ `Category`, filtered by `Tag.user_id`, grouped by `Tag.name, Category.type`, selecting `MIN/MAX(Transaction.created_at)`. Keeping `tags` intact keeps `fetchTags()` and old app versions working.

Alternative considered: a separate `/api/tags/periods` endpoint. Rejected — the user agreed to extend `/api/tags`, and one call serves both needs.

The analytics screen fetches tag periods once in `initState` in parallel with the first load and does not refetch on range change (tags created elsewhere appear next time the screen opens).

### Hint and range switch

Pure helper `combinedTagPeriod(includedKeys, periodsByKey) -> (DateTime firstMonth, DateTime lastMonth)?` in `tag_utils.dart`, computed from `first_at`/`last_at` exactly as parsed, the same way the screen buckets transactions by `createdAt` into months, so the hint and the charts agree. The hint is shown when the result is non-null and `firstMonth < rangeStartMonth || lastMonth > rangeEndMonth`. "Show period" reuses existing range setters: one month → `_groupByMonth = false` + `_applyMonthRange`; otherwise `_groupByMonth = true`, set `_startDate`/`_endDate` (end clamped to today), `_rebuildMonths()`, then `_loadData()`. Hint copy follows the screen's existing English strings, e.g. `repair, trip: transactions in Mar 2024 – Apr 2025 · Show period`. The hint sits below the filters card: inserting it above shifted the card in the list and collapsed its expansion tiles.

## Risks / Trade-offs

- [Out-of-period tag list can be long] → collapsed by default behind "N more"; only selected ones are pinned visible.
- [Tag periods go stale while the screen is open after editing a transaction elsewhere] → acceptable; reopening analytics refetches. Hint may be slightly off until then.
- [Timezone edges: UTC `created_at` near month boundaries] → months are taken the same way as transaction grouping on the screen, so a boundary transaction lands in the same month in both.
- [Empty state may confuse when filters are persisted invisibly] → empty-state text explicitly mentions the selected filters; category summary keeps showing counts.

## Migration Plan

Backend first (additive field, no DB migration), bump `pyproject.toml` version, `just openapi`. Then frontend release; old app versions ignore the new field.
