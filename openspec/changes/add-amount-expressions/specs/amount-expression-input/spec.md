## Purpose

Позволяет вычислять денежные суммы непосредственно в полях ввода операций и баланса счёта, проверять итог до сохранения и набирать выражения через системную клавиатуру телефона или физическую клавиатуру.

## ADDED Requirements

### Requirement: Expressions in all monetary entry forms
The application SHALL accept arithmetic expressions in transaction creation and editing, initial account balance, and account balance editing. Ordinary numeric input SHALL remain supported.

#### Scenario: Expression used in each form
- **WHEN** the user enters `120+80` in any of these monetary fields and saves an otherwise valid form
- **THEN** the submitted monetary value is `200`

#### Scenario: Existing plain numeric input
- **WHEN** the user enters `42.5` in a monetary field
- **THEN** the field accepts the value and resolves it to `42.50`

### Requirement: Arithmetic syntax and precedence
The application SHALL support addition, subtraction, multiplication (`*` or `×`), division (`/` or `÷`), parentheses, unary signs, and decimal literals with a dot or comma. Multiplication and division SHALL precede addition and subtraction; operators at the same precedence SHALL be evaluated left to right. Whitespace between tokens SHALL be ignored. Unsupported syntax SHALL NOT be silently evaluated or partially accepted.

#### Scenario: Standard precedence
- **WHEN** the user enters `100+50*2`
- **THEN** the result is `200`

#### Scenario: Parentheses and division
- **WHEN** the user enters `(100+50)/2`
- **THEN** the result is `75`

#### Scenario: Decimal separators and displayed operator symbols
- **WHEN** the user enters `1,5 × 2 + 0.25`
- **THEN** the result is `3.25`

#### Scenario: Left associative division
- **WHEN** the user enters `100/5/2`
- **THEN** the result is `10`

#### Scenario: Unsupported syntax
- **WHEN** the user enters `10%`, `2^3`, or `2(3+4)`
- **THEN** the field does not offer a valid result and the form cannot save that input

### Requirement: Preview and monetary rounding
For a valid expression the application SHALL show its monetary result beneath the field while preserving the expression for editing. The application SHALL round the final result to two decimal places, using nearest rounding with ties away from zero, and SHALL submit that same rounded value. Intermediate computations SHALL NOT be rounded to cents. Negative zero SHALL be presented and saved as zero. Existing monetary display conventions SHALL be preserved.

#### Scenario: Repeating fraction
- **WHEN** the user enters `100/3`
- **THEN** the preview represents `33.33` and saving submits `33.33`

#### Scenario: Expression remains editable
- **WHEN** the user enters `120+80` and sees the preview
- **THEN** the field still contains `120+80` and editing it recomputes the preview

#### Scenario: Round only final value
- **WHEN** the user enters `1/3*3`
- **THEN** the preview and submitted amount are `1`

#### Scenario: Decimal rounding ties
- **WHEN** the user enters `1.005` or `-1.005`
- **THEN** the rounded result is respectively `1.01` or `-1.01`

### Requirement: Zero and negative amounts
The application SHALL accept zero and negative expression results in all monetary entry forms.

#### Scenario: Negative result
- **WHEN** the user enters `-100+20`
- **THEN** the accepted result is `-80`

#### Scenario: Zero result
- **WHEN** the user enters `100-100`
- **THEN** the accepted result is `0`

### Requirement: Invalid input and error timing
The application SHALL prevent saving empty, incomplete, invalid, or non-finite expression results and SHALL hide the result preview for such input. While the user is editing, empty, incomplete and syntactically invalid input SHALL show an actionable validation message only after focus leaves the field or a submit attempt occurs. Division by zero SHALL show an actionable error immediately. A corrected expression SHALL clear the error and restore the current result; a previous valid result SHALL NOT be submitted for invalid current input.

#### Scenario: Incomplete expression while focused
- **WHEN** the user types `100+` in a focused field before leaving the field or attempting submission
- **THEN** no result or validation error is shown and the form cannot save that expression

#### Scenario: Validation after blur or submit
- **WHEN** the user leaves the field or attempts submission with `100+` or an empty value
- **THEN** an appropriate validation message is shown and no save request is sent

#### Scenario: Division by zero
- **WHEN** the user enters `100/(2-2)`
- **THEN** a division-by-zero message is shown immediately and saving is prevented

#### Scenario: Recovery from invalid expression
- **WHEN** the user corrects `100/0` to `100/2`
- **THEN** the error is cleared and the preview represents `50`

### Requirement: Native keyboard input
The application SHALL request ordinary text input for monetary fields on phones and in browsers, allowing arithmetic operators and decimal separators. The application SHALL NOT show an in-app calculator keyboard or force a particular internal layout of the installed system keyboard. Users SHALL be able to switch their keyboard to its symbols or numeric layout manually. Native caret, selection, deletion and paste behavior SHALL remain available. The field and result preview SHALL remain visible above the system keyboard. The keyboard Done action SHALL finish editing without saving the form or replacing the expression. Desktop users SHALL be able to type or paste expressions with a physical keyboard.

#### Scenario: Phone input
- **WHEN** a phone user focuses a monetary field
- **THEN** the application requests the system text keyboard and shows no custom calculator panel
- **AND** the field and preview remain visible when the software keyboard occupies screen space

#### Scenario: System keyboard layout choice
- **WHEN** the user switches the system keyboard to symbols or its numeric panel
- **THEN** arithmetic input is accepted without the application replacing or controlling that keyboard layout

#### Scenario: Native selection and replacement
- **WHEN** the user selects part of an expression and types or pastes replacement text
- **THEN** the selection is replaced and the preview is recomputed from the resulting expression

#### Scenario: Finish input without submitting
- **WHEN** the user activates the keyboard Done action after entering `120+80`
- **THEN** editing finishes, the expression remains in the field, and the form is not submitted

#### Scenario: Switch to a text field
- **WHEN** the user moves focus from a monetary field to the description field
- **THEN** ordinary text input is available through the same system keyboard

#### Scenario: Desktop input
- **WHEN** a desktop user types or pastes `(120+80)/2` into a monetary field
- **THEN** the preview represents `100`

### Requirement: Persist only the evaluated amount
The application SHALL send only the rounded numeric amount through the existing monetary API fields. The original expression SHALL NOT be persisted. Reopening a saved operation or account SHALL populate the field with the stored numeric amount or current account balance.

#### Scenario: Reopen saved transaction
- **WHEN** the user saves a transaction with `120+80` and reopens it
- **THEN** the monetary field contains the numeric amount `200` rather than the expression

#### Scenario: Edit account balance
- **WHEN** the user saves `1000-250` as the account balance
- **THEN** the existing balance adjustment behavior sets the resulting balance to `750` and reopening shows the resulting numeric balance
