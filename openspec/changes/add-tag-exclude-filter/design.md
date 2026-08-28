## Context

See proposal.md for motivation. Analytics already loads the period’s transactions client-side and filters them in `TransactionStatsScreen`. Tag chips live in `AnalyticsFiltersCard` and are currently a boolean set (`selectedTagKeys`): empty means no tag constraint; non-empty means OR-include. Income and expense keep separate copies of that set. Category chips stay two-state.

`FilterChip.selected` is boolean, so exclude cannot reuse the selected flag. Matching currently lives as `_matchesTagFilter` on the screen and is not unit-tested.

## Goals / Non-Goals

**Goals:**

- Represent per-tag include vs exclude without putting a tag in both states.
- Keep matching a pure function so include/exclude combinations can be unit-tested.
- Reuse the existing chip widget with an extra visual treatment for exclude (strikethrough).
- Preserve Select all / Clear all, date-range reset, and independent income/expense filter state.

**Non-Goals:**

- Backend query parameters for tags.
- Exclude/include on category chips or on the main transaction list screen.
- Persisting filter state across sessions or date-range changes.

## Decisions

### Both filters always apply; exclude wins on overlap

Include and exclude are independent conditions, not alternative modes. If any tag is include, the transaction must have at least one included tag. If any tag is exclude, the transaction must have none of the excluded tags. A transaction that carries both an included tag and an excluded tag is hidden.

**Why:** expense tags stack on one row (`еда` + `работа`, `отпуск` + `еда`). The mixed query that is worth having is “show this slice, minus the rows that also carry a dropped tag.” Treating both chips as live is the only model that can express that. Include is a whitelist; exclude punches holes in whatever the current set is (the whole period, or that whitelist).

**Alternatives rejected:**

- *Include mode ignores excludes.* Simpler, and leftover exclude chips would not change an include slice. It forbids the stacked-tag query, and an exclude chip would lie while any include is active.
- *Exclusive modes* (setting include clears all excludes, and the reverse). No conflict and no priority question, but it also forbids mixing and is more restrictive than the user needs.

**Trade-off accepted:** a leftover exclude chip can hide part of an include slice (the `еда` + `работа` row disappears even though `еда` is selected). That is the rule, not a bug. The collapsed summary must show exclude counts so this is visible without expanding the tile.

### Two sets instead of a single selected set

Keep `includedTagKeys` (today’s `selectedTagKeys`) and add `excludedTagKeys`. A tag key is in at most one set. Cycle:

- idle (in neither) → add to included
- included → move from included to excluded
- excluded → remove from excluded (idle)

**Why this over `Map<String, TagFilterMode>`:** the current screen, widget, and date-range intersection already speak in sets (`intersection` with available keys). Two sets is the smallest change and still encodes “not both”. A helper `cycleTagFilter(included, excluded, key)` belongs next to `toggledSetValue`.

**Alternative considered:** one map of enum states. Cleaner domain model, more churn through `AnalyticsFiltersCard` and the four income/expense setters. Not worth it for two mutually exclusive sets.

### Extract matching to a pure helper

Move tag matching out of the screen into `frontend/lib/utils/tag_utils.dart` (or a sibling util):

```
matchesTagFilter(tags, includedKeys, excludedKeys) -> bool
```

Rules (see spec and the overlap decision above): if `includedKeys` is non-empty, require at least one included tag; if `excludedKeys` is non-empty, reject any excluded tag; empty/empty passes. Normalize with `normalizeTagKey`.

**Why:** combinations (include+exclude, untagged, multi-tag) are easy to get wrong if they stay as private widget methods. Existing frontend tests are plain Dart unit tests, which fits.

**Alternative considered:** widget tests of `AnalyticsFiltersCard`. Useful later for strikethrough, but they do not cover matching of charts/totals. Matching tests come first.

### Exclude appearance: unselected chip + strikethrough label

Keep `FilterChip`. `selected: true` only for include (current accent treatment). For exclude: `selected: false`, label `TextDecoration.lineThrough`, slightly muted or error-tinted foreground so it is not identical to idle. Do not show a checkmark.

**Why:** matches the requested “перечеркнутый текст” and does not fight `FilterChip`’s boolean selected state. Users already know selected = include.

**Alternative considered:** a custom three-state chip or `ChoiceChip` with a third color. More code, same information.

### Bulk actions and summary

- Select all: `included = all keys`, `excluded = {}`.
- Clear all: both sets empty. Enable Clear all when either set is non-empty.
- Subtitle: include and exclude counts, e.g. `2 included · 1 excluded` when any are active, otherwise `0/N selected` or `None`. Exact copy can follow existing English UI strings.
- On date-range reload, both sets still reset (same as today’s `_resetFiltersForReload`). After load, drop keys that are no longer in the available map, independently for include and exclude.

### Shared widget for income and expense

Pass `includedTagKeys` + `excludedTagKeys` + `onCycleTag` (replacing `onToggleTag`) into `AnalyticsFiltersCard`. Both tabs and both month/range layouts get exclude without duplicating chip UI. Category callbacks stay as they are.

## Risks / Trade-offs

- [Idle and exclude both look unselected except for strikethrough] → Use strikethrough plus a distinct label color (muted or expense-red) so exclude is readable at a glance, including on the collapsed summary counts.
- [Include+exclude can yield an empty list] → Expected; empty states already exist (`No expenses in selected categories`, empty transaction sections).
- [Leftover exclude hides overlapping include rows] → Accepted product rule. Mitigate with include+exclude counts in the collapsed summary, not by ignoring excludes.
- [Select all includes every tag, which with current OR-include is almost “show tagged only” and hides untagged] → Same as today; do not change Select all semantics.

## Migration Plan

Frontend-only. Ship with the Flutter app; no schema, API, or stored-state migration. Rollback is a revert of the widget and screen filter state.

## Open Questions

None. Combination rules, cycle order, and visuals are fixed in the spec.
