# 22 Manual Field Pool Contract

## 1. Purpose

Define the field pool used by manual flow template schemes.

The UI may only expose fields defined here.

## 2. Field classes

### 2.1 Core locked fields
These cannot be disabled in any manual scheme:

- entity_match_key
- account_match_key
- business_date
- summary_text
- counterparty_name
- income_amount
- expense_amount

### 2.2 Core optional check fields
These may be enabled or disabled per scheme:

- previous_balance_input
- ending_balance_input
- business_time

### 2.3 Business optional fields
These may be freely enabled from the field pool:

- group_name
- department_name
- income_expense_type
- handler_name
- owner_name
- pending_recovery_flag
- voucher_no
- receipt_no
- note_text

### 2.4 System-only fields
These are not manually input fields:

- batch_code
- parse_status
- abnormal_code
- rolling_balance
- source_type
- created_at

## 3. Scheme mechanics

A manual scheme must support:

- ordered field list
- Chinese column labels
- visibility on or off
- export empty template
- direct use in quick-entry page

## 4. Scheme presets to create in V1

- `manual_simple_cash`
- `manual_multi_subject_basic`
- `manual_multi_subject_with_people`
- `manual_bank_manual_account`

## 5. UI requirements

Manual flow page must provide:

- scheme selector
- optional field selector drawer
- column order adjustment
- save as scheme
- export template button

## 6. Validation

- core locked fields cannot be removed
- disabled fields must not appear in exported template
- disabled fields must not be required during upload parsing
- field labels can vary in UI, but field codes must remain stable
