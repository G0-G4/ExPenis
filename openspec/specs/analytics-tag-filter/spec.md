# analytics-tag-filter Specification

## Purpose

Lets users include or exclude tags when filtering analytics income and expense transactions, charts, and totals.

## Requirements

### Requirement: Tag chips have idle, include, and exclude states

The analytics tag filter SHALL represent each tag with exactly one of three states: idle, include, or exclude. Idle SHALL be the default for every tag. The same three-state filter SHALL apply independently on the income and expense analytics views.

#### Scenario: Default state does not filter by tag

- **WHEN** the user opens analytics and has not tapped any tag chip
- **THEN** every tag chip is idle
- **AND** tag membership does not constrain which transactions are shown

#### Scenario: Include shows only tagged transactions

- **WHEN** the user sets tag A to include and leaves all other tags idle
- **THEN** only transactions that have tag A are shown on that analytics view

#### Scenario: Exclude hides tagged transactions

- **WHEN** the user sets tag A to exclude and leaves all other tags idle
- **THEN** transactions that have tag A are hidden
- **AND** transactions that do not have tag A remain visible, including untagged transactions

#### Scenario: Income and expense tag filters are independent

- **WHEN** the user excludes a tag on the expense view
- **THEN** the income view tag states are unchanged
- **AND** income transactions are not filtered by that expense exclude

### Requirement: Tapping a tag chip cycles its three states

Tapping a tag chip SHALL cycle that tag through idle → include → exclude → idle. Tapping SHALL change only the tapped tag.

#### Scenario: Cycle from idle to include

- **WHEN** the user taps an idle tag chip
- **THEN** that tag becomes include

#### Scenario: Cycle from include to exclude

- **WHEN** the user taps an include tag chip
- **THEN** that tag becomes exclude

#### Scenario: Cycle from exclude back to idle

- **WHEN** the user taps an exclude tag chip
- **THEN** that tag becomes idle

### Requirement: Excluded chips show strikethrough label text

An exclude-state tag chip SHALL display the tag name with strikethrough text so the exclude state is visually distinct from idle and include. An include-state chip SHALL keep the existing selected appearance without strikethrough. An idle chip SHALL keep the existing unselected appearance without strikethrough.

#### Scenario: Exclude is shown with strikethrough

- **WHEN** a tag is in the exclude state
- **THEN** its chip label is rendered with strikethrough

#### Scenario: Include is not shown with strikethrough

- **WHEN** a tag is in the include state
- **THEN** its chip label is not strikethrough
- **AND** the chip uses the selected include appearance

### Requirement: Include and exclude states combine with OR-include then AND-not-exclude

Tag matching SHALL use these rules, applied after category and date filters:

1. If at least one tag is include, a transaction MUST have at least one included tag.
2. If at least one tag is exclude, a transaction MUST NOT have any excluded tag.
3. If no tags are include and no tags are exclude, tag membership does not constrain the result.
4. Tag comparison SHALL use the existing case-insensitive normalized tag key.

These rules SHALL apply to analytics lists, category charts, totals, and grouped monthly charts on the same view.

#### Scenario: Multiple includes match any included tag

- **WHEN** tags A and B are include and no tag is exclude
- **THEN** a transaction with tag A is shown
- **AND** a transaction with tag B is shown
- **AND** a transaction with neither A nor B is hidden

#### Scenario: Multiple excludes hide any excluded tag

- **WHEN** tags A and B are exclude and no tag is include
- **THEN** a transaction with tag A is hidden
- **AND** a transaction with tag B is hidden
- **AND** a transaction with neither A nor B is shown

#### Scenario: Include and exclude together

- **WHEN** tag A is include and tag B is exclude
- **THEN** a transaction with A and not B is shown
- **AND** a transaction with A and B is hidden
- **AND** a transaction with B and not A is hidden
- **AND** a transaction with neither A nor B is hidden

#### Scenario: Untagged transaction with only excludes

- **WHEN** tag A is exclude and no tag is include
- **THEN** a transaction with no tags is shown

#### Scenario: Untagged transaction with includes

- **WHEN** tag A is include
- **THEN** a transaction with no tags is hidden

### Requirement: Bulk tag actions apply to the current period

Select all SHALL set every tag present in the current period on that view to include and SHALL clear every exclude on that view. Clear all SHALL set every tag on that view to idle, including tags that were excluded and tags absent from the current period. Category filter chips SHALL remain two-state and SHALL NOT gain an exclude state.

#### Scenario: Select all includes every tag in the period

- **WHEN** some tags are idle or exclude and the user chooses Select all on the tag filter
- **THEN** every tag present in the current period on that view is include
- **AND** no tag on that view is exclude

#### Scenario: Clear all returns every tag to idle

- **WHEN** some tags are include or exclude and the user chooses Clear all on the tag filter
- **THEN** every tag on that view is idle
- **AND** tag membership does not constrain which transactions are shown

#### Scenario: Collapsed summary reflects include and exclude

- **WHEN** at least one tag is include or exclude
- **THEN** the tag filter summary shows both the include count and the exclude count

### Requirement: Tag states persist across period changes

Tag include and exclude states SHALL be kept when the user changes the analytics period by any means (previous/next month, month picker, grouped start or end month, toggling group-by-month, or the "Show period" hint action). The states SHALL persist for as long as the analytics screen stays open and SHALL remain independent between income and expense views.

#### Scenario: Included tag survives month navigation

- **WHEN** tag A is include and the user moves to the previous month
- **THEN** tag A is still include
- **AND** only transactions with tag A are shown for the new month

#### Scenario: Include of a tag absent from the new period yields an empty result

- **WHEN** tag A is include and the user moves to a period with no transactions tagged A
- **THEN** tag A is still include
- **AND** the view shows no transactions

### Requirement: Tags outside the current period are listed

The tag filter on each view SHALL list every tag that the user has ever applied to a transaction of that view's type (income or expense). Tags with at least one transaction in the current period SHALL be shown first with the normal chip appearance. Tags with no transaction in the current period SHALL be shown after them with a dimmed appearance, collapsed by default behind a control that shows how many such tags exist. Dimmed chips SHALL cycle through idle, include, and exclude like any other tag chip. A tag used only on the other type SHALL NOT be listed on this view.

#### Scenario: Tag from another period is selectable

- **WHEN** the user opens expense analytics for a month without any "trip" expense, and "trip" was used on expenses in an earlier month
- **THEN** a dimmed "trip" chip is available under the collapsed "more" control
- **AND** tapping it sets "trip" to include

#### Scenario: Tag of the other type is not listed

- **WHEN** tag "salary" has only ever been used on income transactions
- **THEN** the expense view does not list "salary"

#### Scenario: Selected out-of-period tag stays visible

- **WHEN** a dimmed tag is include or exclude
- **THEN** its chip remains visible even if the "more" section is collapsed

### Requirement: Hint offers the included tags' period

When at least one tag is include on a view, the system SHALL compute the combined period of the included tags on that view: from the month of the earliest to the month of the latest transaction of that type carrying any included tag. If that combined period is not entirely contained in the current analytics range, the view SHALL show a hint naming the included tags and the combined period, with a "Show period" action. Exclude-state tags SHALL NOT affect the combined period or the hint. The hint SHALL NOT have a dismiss control and SHALL disappear as soon as the combined period fits within the current range or no tag is include.

#### Scenario: Hint appears for a tag outside the range

- **WHEN** the user views October 2026 and sets tag "trip" (used March–June 2024) to include
- **THEN** a hint shows "trip" with the period March 2024 – June 2024 and a "Show period" action

#### Scenario: Adding a tag that widens the period re-shows the hint

- **WHEN** the range is March–June 2024 with "trip" include and the user sets "repair" (used January–April 2025) to include
- **THEN** a hint shows the period March 2024 – April 2025

#### Scenario: No hint when the period already fits

- **WHEN** every transaction of the included tags lies inside the current range
- **THEN** no hint is shown

#### Scenario: Exclude does not trigger the hint

- **WHEN** no tag is include and tag "trip" (used only in 2024) is exclude while viewing October 2026
- **THEN** no hint is shown

### Requirement: Show period sets the range to the tags' combined period

Choosing "Show period" SHALL set the analytics range to exactly the combined period of the included tags, without merging it with the previous range. If the combined period is a single month, the view SHALL use single-month mode on that month. Otherwise it SHALL use group-by-month mode from the first to the last month of the combined period. The range end SHALL NOT be later than the current date. Tag and category filter states SHALL be kept.

#### Scenario: Multi-month tag switches to grouped mode

- **WHEN** the user is in single-month mode on October 2026 with "trip" (March–June 2024) include and chooses "Show period"
- **THEN** the view is in group-by-month mode from March 2024 to June 2024
- **AND** "trip" is still include

#### Scenario: Single-month tag uses single-month mode

- **WHEN** the included tags' transactions all fall in May 2025 and the user chooses "Show period"
- **THEN** the view is in single-month mode on May 2025

#### Scenario: Previous range is not merged in

- **WHEN** the current range is October 2026 and the included tags span March–June 2024
- **THEN** after "Show period" the range is March–June 2024, not March 2024 – October 2026
