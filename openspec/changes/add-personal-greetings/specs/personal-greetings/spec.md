## Purpose

Позволяет владельцу приложения назначать пользователям короткие персональные поздравления через серверную CLI, а пользователям — читать и закрывать их на вкладке транзакций с сохранением состояния между устройствами.

## ADDED Requirements

### Requirement: One replaceable personal greeting per user

The system SHALL store at most one current greeting per user. Each assignment SHALL replace the previous greeting, create a new assignment identifier, reset dismissal, and make the greeting immediately eligible for display, including when the text is unchanged. Greeting text MUST contain non-whitespace content and MUST be at most 1000 Unicode code points. The system SHALL preserve line breaks and emoji and SHALL treat the content as plain text.

#### Scenario: Assign a personal greeting
- **WHEN** the operator assigns valid text to an existing user
- **THEN** that user has one current greeting with the supplied text
- **AND** other users' greetings are unchanged

#### Scenario: Reassign the same text after dismissal
- **WHEN** the operator assigns the same text to a user who dismissed the previous greeting
- **THEN** the new assignment has a different identifier and is visible again
- **AND** the previous assignment is no longer current

#### Scenario: Reject invalid text
- **WHEN** assignment text is empty, whitespace-only, or longer than 1000 Unicode code points
- **THEN** assignment fails with an explanatory error and no greetings are changed

### Requirement: Optional inclusive Moscow expiration date

The operator SHALL be able to omit expiration or provide a valid calendar date in YYYY-MM-DD format, interpreted inclusively in Europe/Moscow. The greeting SHALL be active before the start of the following day in that timezone and expired at and after that instant. Without expiration, it SHALL remain eligible until dismissed, replaced, or deleted. Dates before today's Moscow date MUST be rejected before mutation. Eligibility SHALL depend on the current time, independently of the transaction date selected by the user.

#### Scenario: Expiration boundary
- **WHEN** a greeting expires on 2026-12-31
- **THEN** it is eligible at 2026-12-31 23:59:59 Europe/Moscow
- **AND** it is not eligible at 2027-01-01 00:00:00 Europe/Moscow

#### Scenario: No expiration
- **WHEN** the operator assigns a greeting without an expiration date
- **THEN** passage of time alone does not expire it

#### Scenario: Invalid expiration
- **WHEN** the operator supplies an invalid date or a date before today in Moscow
- **THEN** assignment fails without replacing any greeting

### Requirement: Server-side operator commands

The server CLI SHALL support assigning, viewing, and deleting greetings for a specific existing user or all existing users. Individual users SHALL be selectable by user ID or username. Unknown users and invalid or conflicting target arguments MUST fail without mutation. Viewing SHALL report the recipient, current text and identifier, expiration, and active, dismissed, or expired state, or the absence of a greeting. Deleting SHALL remove the current assignment, including a dismissed or expired one; deleting an absent greeting SHALL be a successful no-op. Operator commands SHALL require server access and SHALL NOT expose assignment, inspection of other users, or deletion capabilities through the user-facing API.

#### Scenario: Inspect and remove a greeting
- **WHEN** the operator views a selected user's greeting and then deletes it
- **THEN** inspection reports the current assignment and its state
- **AND** subsequent inspection reports no greeting and the user API returns no active greeting

#### Scenario: Unknown recipient
- **WHEN** the operator targets a nonexistent username or user ID
- **THEN** the command exits unsuccessfully with a clear error and no data changes

### Requirement: Confirmed bulk assignment to existing recipients

Bulk assignment SHALL capture the existing recipient set, report its size, and require explicit confirmation before replacing greetings. Cancellation or unavailable confirmation SHALL leave all greetings unchanged. A confirmed assignment SHALL atomically replace greetings for that captured set using the same text and expiration. Users registered after recipient selection SHALL NOT inherit the greeting. Bulk deletion SHALL also report the target count and require confirmation. An empty target set SHALL complete without mutation and report zero recipients.

#### Scenario: Confirmed bulk replacement
- **WHEN** the operator confirms assignment to a captured set of three users
- **THEN** all three receive a new assignment, replacing any active, dismissed, or expired greeting
- **AND** a user registered after selection does not receive that greeting

#### Scenario: Cancel or fail a bulk mutation
- **WHEN** confirmation is declined or unavailable, or a database failure prevents completion
- **THEN** no recipient receives a partial assignment or deletion

### Requirement: Authenticated current-user greeting API

The system SHALL provide authenticated API operations to retrieve the current user's active greeting and dismiss a particular assignment. Retrieval SHALL return either the assignment identifier, text, and optional expiration instant, or an explicit empty result when absent, dismissed, or expired. The recipient SHALL be derived exclusively from authentication. Unauthenticated requests MUST be rejected; no operation SHALL read or alter another user's greeting.

#### Scenario: No active greeting
- **WHEN** an authenticated user has no greeting, or their greeting is dismissed or expired
- **THEN** retrieval succeeds with an explicit empty result

#### Scenario: User isolation
- **WHEN** a user attempts to dismiss another user's assignment identifier
- **THEN** the other user's greeting is unchanged and the request reveals no message content

#### Scenario: Authentication required
- **WHEN** a client requests or dismisses a greeting without valid authentication
- **THEN** the API rejects the request as unauthorized

### Requirement: Persistent assignment-specific dismissal

Dismissal SHALL be stored on the server and SHALL apply only to the specified assignment belonging to the authenticated user. Repeated dismissal of the same current assignment SHALL succeed without additional effects. A stale dismissal after replacement or deletion SHALL NOT hide a newer greeting. Other devices SHALL observe the dismissal on their next successful retrieval; instantaneous push synchronization is not required.

#### Scenario: Close across devices
- **WHEN** a user dismisses a greeting on device A and device B retrieves the greeting again
- **THEN** device B receives no active greeting for that assignment

#### Scenario: Delayed dismissal after replacement
- **WHEN** an operator replaces assignment A with B before a delayed dismissal of A arrives
- **THEN** B remains active and retrievable

### Requirement: Greeting block on the transactions tab

The Flutter app SHALL show an active greeting as a dismissible text block above the transaction list only on the transactions tab, including when the list is empty. The block SHALL preserve line breaks and emoji, wrap long text, and allow the complete text and close action to remain reachable on small screens and with increased text size. No block SHALL occupy space for an empty result. Greeting loading and errors SHALL NOT prevent transaction use.

#### Scenario: Display on the home tab
- **WHEN** an authenticated user opens the transactions tab with an active greeting
- **THEN** the text and a clearly labeled accessible close control appear above the list
- **AND** the greeting does not appear on accounts or categories tabs

#### Scenario: Long text with an empty list
- **WHEN** the user has no transactions and a 1000-code-point greeting on a narrow screen
- **THEN** the complete greeting, close control, and transaction empty state remain accessible without layout overflow

### Requirement: Refresh and failure behavior

The app SHALL retrieve greeting state when the transactions screen is first opened, on returning to that tab, on application resume, and on explicit transaction refresh. It SHALL discard stale responses from an earlier user or request. A loaded greeting SHALL disappear at its expiration instant, without requiring a user refresh. Successful dismissal SHALL hide the targeted greeting; a failed dismissal SHALL leave it available and display a retryable error. A greeting retrieval failure SHALL be surfaced with a retry action without hiding transaction data; the app SHALL NOT present unvalidated cached greeting text as current.

#### Scenario: Resume after dismissal elsewhere
- **WHEN** the app resumes after the greeting was dismissed on another device
- **THEN** it retrieves current state and removes that greeting after successful retrieval

#### Scenario: Expire while open
- **WHEN** a displayed greeting reaches its expiration instant while the app remains open
- **THEN** the block disappears without changing transaction data

#### Scenario: Failed dismissal
- **WHEN** a dismissal request fails
- **THEN** the greeting remains available and an error allows the user to retry closing it

#### Scenario: Retrieval failure
- **WHEN** greeting retrieval fails while transaction retrieval succeeds
- **THEN** the transaction list remains usable and a greeting error offers retry
- **AND** previously loaded greeting text is not displayed as a current greeting until validated
