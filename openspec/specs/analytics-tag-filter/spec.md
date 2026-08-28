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

### Requirement: Bulk tag actions reset or include all tags

Select all SHALL set every available tag on that view to include. Clear all SHALL set every tag on that view to idle, including tags that were excluded. Category filter chips SHALL remain two-state and SHALL NOT gain an exclude state.

#### Scenario: Select all includes every tag

- **WHEN** some tags are idle or exclude and the user chooses Select all on the tag filter
- **THEN** every available tag on that view is include

#### Scenario: Clear all returns every tag to idle

- **WHEN** some tags are include or exclude and the user chooses Clear all on the tag filter
- **THEN** every tag on that view is idle
- **AND** tag membership does not constrain which transactions are shown

#### Scenario: Collapsed summary reflects include and exclude

- **WHEN** at least one tag is include or exclude
- **THEN** the tag filter summary shows both the include count and the exclude count

#### Scenario: Changing the date range resets tag states

- **WHEN** the user changes the analytics date or month range
- **THEN** all tag chips return to idle
