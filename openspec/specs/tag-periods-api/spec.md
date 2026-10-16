# tag-periods-api Specification

## Purpose

Lets clients learn, for each of the user's tags, when it was first and last used on income and on expense transactions, so they can offer tag-wide date ranges.

## Requirements

### Requirement: Tags endpoint reports tag usage periods

`GET /api/tags` SHALL keep returning the `tags` list of tag names unchanged and SHALL additionally return a list of tag periods. Each tag period SHALL contain the tag name, the transaction type (`income` or `expense`, from the transaction's category), the timestamp of the earliest transaction of that type carrying the tag, and the timestamp of the latest one. A tag used on both types SHALL produce one entry per type. A tag with no transactions SHALL produce no entries. Only the requesting user's tags and transactions SHALL be considered.

#### Scenario: Tag used on expenses only

- **WHEN** the user's tag "trip" is on expense transactions dated 2024-03-05 and 2024-06-20
- **THEN** the response contains one period for "trip" with type `expense`, first 2024-03-05 and last 2024-06-20

#### Scenario: Tag used on both types

- **WHEN** tag "gift" is on one income and two expense transactions
- **THEN** the response contains one `income` period and one `expense` period for "gift"

#### Scenario: Unused tag

- **WHEN** tag "old" exists but no transaction carries it
- **THEN** "old" appears in `tags`
- **AND** no period entry exists for "old"

#### Scenario: Other users are isolated

- **WHEN** another user has transactions tagged with the same tag name
- **THEN** those transactions do not affect the requesting user's periods

#### Scenario: Existing field is backward compatible

- **WHEN** an existing client reads only `tags`
- **THEN** it receives the same list of names as before
