## Purpose

Lets users narrow analytics income and expense views to chosen categories and keep that choice while moving between periods.

## ADDED Requirements

### Requirement: Category filter has all and explicit-set modes

Each analytics view (income, expense) SHALL keep its category filter in one of two modes. In **all** mode, the default, every category present in the current period is selected, including categories that first appear after a period change. Any manual toggle of a category chip SHALL switch the filter to **explicit-set** mode, holding exactly the categories that are selected after the toggle. In explicit-set mode, categories that appear in a new period and are not in the set SHALL be unselected. Select all SHALL return the filter to all mode. Clear all SHALL switch to explicit-set mode with an empty set.

#### Scenario: All mode picks up new categories

- **WHEN** the filter is in all mode and the user moves to a month containing category "Pharmacy" that was absent from the previous month
- **THEN** "Pharmacy" is selected

#### Scenario: Explicit set does not pick up new categories

- **WHEN** the user leaves only "Food", "Taxi" and "Rent" selected and moves to a month containing "Pharmacy"
- **THEN** only "Food", "Taxi" and "Rent" are selected
- **AND** "Pharmacy" is unselected

#### Scenario: Deselecting one category fixes the set

- **WHEN** the filter is in all mode and the user deselects "Taxi"
- **THEN** the filter holds every other category present at that moment as an explicit set
- **AND** a category first appearing in a later period is unselected

#### Scenario: Select all restores all mode

- **WHEN** the filter is an explicit set and the user chooses Select all
- **THEN** every category in the current period is selected
- **AND** categories appearing in later periods are selected too

### Requirement: Category selection persists across period changes

The category filter mode and set SHALL be kept when the user changes the analytics period by any means, for as long as the analytics screen stays open. Income and expense category filters SHALL remain independent.

#### Scenario: Explicit set survives navigation

- **WHEN** the user selects only "Food" and moves to the previous month and back
- **THEN** only "Food" is selected in both months

### Requirement: Empty match shows an empty state instead of resetting

If no category of an explicit set has transactions in the current period, the view SHALL show an empty state stating that no transactions match the selected filters, and SHALL keep the explicit set unchanged. The filter SHALL NOT fall back to selecting all categories.

#### Scenario: Selected categories absent from the period

- **WHEN** only "Rent" is selected and the user moves to a month without "Rent" transactions
- **THEN** the view shows the empty state
- **AND** after moving to a month with "Rent" transactions, only "Rent" is selected
