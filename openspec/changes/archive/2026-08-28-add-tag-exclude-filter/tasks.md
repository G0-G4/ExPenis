## 1. Tag filter helpers

- [x] 1.1 Add `cycleTagFilter` (idle → include → exclude → idle) in `frontend/lib/utils/selection_utils.dart` and verify with a Dart unit test that a key moves between the two sets and never sits in both
- [x] 1.2 Add `matchesTagFilter(tags, includedKeys, excludedKeys)` in `frontend/lib/utils/tag_utils.dart` using normalized keys, and verify unit tests cover: no filters, single include, single exclude, multiple includes (OR), multiple excludes, include+exclude, untagged with only excludes, untagged with includes

## 2. Filter chip UI

- [x] 2.1 Update `AnalyticsFiltersCard` to take `includedTagKeys` and `excludedTagKeys`, cycle via `onCycleTag`, render exclude chips with strikethrough (unselected), keep include chips selected without strikethrough, and verify `flutter analyze` is clean for the widget
- [x] 2.2 Update the tag filter subtitle and bulk actions so Select all includes every tag and clears excludes, Clear all idles both sets (enabled when either set is non-empty), and the collapsed summary shows include and exclude counts; verify by reading the widget that category chips still have only two states

## 3. Analytics screen wiring

- [x] 3.1 Replace `_selectedIncomeTagKeys` / `_selectedExpenseTagKeys` on `TransactionStatsScreen` with include+exclude sets, cycle on chip tap, reset both sets on date-range reload, and intersect stale keys after load; verify income and expense state stay independent in the screen code
- [x] 3.2 Route list, chart, and total filtering through `matchesTagFilter` and remove `_matchesTagFilter`; verify every previous `_matchesTagFilter` call site now passes both include and exclude sets

## 4. Quality checks

- [x] 4.1 Run `flutter test` from `frontend/` for the new helper tests and confirm they pass
- [x] 4.2 Run `flutter analyze` in `frontend/` and confirm no new issues in the touched files
