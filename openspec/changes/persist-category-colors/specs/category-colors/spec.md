## Purpose

Keep each category visually recognizable across analytics periods and devices by persisting its color on the server and letting its owner choose a replacement from a fixed palette.

## ADDED Requirements

### Requirement: Categories have persistent server-owned colors

The system SHALL persist a color for every existing and newly created category, including default categories. The color SHALL remain unchanged across reads, restarts, account logout/login, category renaming, and category type changes unless its owner explicitly selects a replacement. Category list, detail, creation, and update responses SHALL include the persisted color.

#### Scenario: Existing categories receive colors
- **WHEN** an installation containing categories is upgraded
- **THEN** every existing category has a persisted color from the supported palette
- **AND** its transactions, ownership, name, and type remain unchanged

#### Scenario: Category metadata changes
- **WHEN** the owner renames a category or changes its type without choosing another color
- **THEN** the category retains its persisted color

#### Scenario: Another device reads the category
- **WHEN** the same account loads categories on another device after a color update succeeds
- **THEN** the response contains the updated color

### Requirement: Automatic assignment uses a 32-color palette

The system SHALL use a fixed palette of 32 distinct colors for automatic assignment and user selection. The aggregate Other color SHALL be reserved outside this palette. Automatic assignment SHALL use an unused palette color among all categories belonging to the user while any unused color remains. After exhaustion, colors SHALL be reusable. Existing categories SHALL be assigned using the complete category collection per user, independent of analytics periods, ranks, and filters. Manual selection SHALL allow any palette color, including an already used color.

#### Scenario: Unused colors remain
- **WHEN** a category is created for a user with unused palette colors
- **THEN** the category receives one of those unused colors
- **AND** existing category colors remain unchanged

#### Scenario: Palette is exhausted
- **WHEN** a category is created for a user whose categories already use all 32 palette colors
- **THEN** creation succeeds with a reused palette color

#### Scenario: Default categories are created
- **WHEN** the system creates a user's standard income and expense categories
- **THEN** it assigns colors under the same unused-first rule across both types

### Requirement: Owners can change colors through category editing

The category editing screen SHALL show the current color and all 32 selectable palette colors, with an indication of the selected color. Saving SHALL persist the selected color through the category API. New categories SHALL receive automatic colors without requiring color selection on the creation screen. A failed save SHALL show an error and SHALL NOT be presented as a successful server update.

#### Scenario: Choose and save a color
- **WHEN** the owner selects a different palette color and successfully saves the category
- **THEN** reopening the editor shows that color as selected
- **AND** subsequent category responses contain it

#### Scenario: Reuse another category's color
- **WHEN** the owner selects a palette color already used by another category
- **THEN** saving succeeds without changing the other category's color

#### Scenario: Cancel editing
- **WHEN** the owner changes the selection and leaves without saving
- **THEN** the persisted color remains unchanged

#### Scenario: Saving fails
- **WHEN** the server rejects or cannot complete a color update
- **THEN** the editor displays a failure and allows retrying
- **AND** the application does not report that the color was saved

### Requirement: Color updates are backward compatible and user scoped

An update request omitting color SHALL preserve the stored color, including requests from older clients. An explicitly supplied color SHALL be a supported palette value; explicit null and unsupported values SHALL be rejected with a validation error without modifying the category. Requests for another user's category SHALL NOT disclose or modify it and SHALL return the same not-found response as an unknown category.

#### Scenario: An older client updates metadata
- **WHEN** an update contains name and type but omits color
- **THEN** the stored color is preserved
- **AND** the metadata update succeeds

#### Scenario: Invalid color is submitted
- **WHEN** an update explicitly supplies null or an unsupported color
- **THEN** the API returns a validation error
- **AND** the category's color and metadata remain unchanged

#### Scenario: Another user's category is accessed
- **WHEN** a user requests or updates a category belonging to another account
- **THEN** the API returns not found
- **AND** the category remains unchanged

### Requirement: Analytics breakdowns use category identity colors

Individual categories in the circular chart, monthly stacked bars, their legends, and the detailed category breakdown SHALL use the persisted color of that category. Changing periods, filters, amounts, or rankings SHALL NOT change that color. This feature SHALL NOT change income/expense semantic colors in transaction views or introduce category colors into category lists, selectors, or filter chips outside analytics breakdowns.

#### Scenario: Rankings change between months
- **WHEN** a category moves from the largest total in one month to a lower rank in another
- **THEN** all individual representations of that category keep its persisted color

#### Scenario: Filters change rankings
- **WHEN** account, tag, or category filters change which categories and amounts are included
- **THEN** each remaining category keeps its persisted color

#### Scenario: Charts are compared
- **WHEN** a category appears individually in both circular and monthly stacked charts
- **THEN** both charts and their breakdown labels use the same persisted color

### Requirement: Other aggregation is independent of color assignment

The existing aggregation policy SHALL remain: up to seven categories are shown individually; with more than seven, six leading categories are shown individually and the remainder is aggregated as Other. The Other aggregate SHALL remain gray. Each constituent category SHALL retain its own persisted color in the detailed breakdown, including while it belongs to Other. Membership in Other SHALL NOT be inferred from a category's color.

#### Scenario: A category enters Other
- **WHEN** a category moves from an individual chart segment into Other after a period or filter change
- **THEN** its contribution is included in the gray aggregate
- **AND** its individual row in the detailed breakdown retains its persisted color

#### Scenario: More than seven categories are present
- **WHEN** a chart contains eight or more categories
- **THEN** it shows six leading individual categories and the gray Other aggregate
- **AND** the 32-color palette does not increase that display limit

### Requirement: Devices observe updates on normal data reload

The client SHALL use colors included in ordinary category responses and SHALL keep the loaded values in screen memory. The feature SHALL NOT add persistent local color storage, separate color-fetch requests, or realtime synchronization. An already open analytics screen SHALL observe remote changes on its next normal category reload, including reopening the screen or changing the analytics period.

#### Scenario: Remote update and subsequent reload
- **WHEN** device A saves a new category color while device B has analytics open, and device B subsequently reloads categories through normal navigation
- **THEN** device B's breakdowns use the newly persisted color
- **AND** no realtime update before that reload is required
