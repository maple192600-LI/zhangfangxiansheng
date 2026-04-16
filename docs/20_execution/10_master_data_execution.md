# 10 Master Data Execution

## 1. Module goal

Deliver a complete master data center for:

- division
- entity
- account
- account alias
- initial balance and balance date

This module is the anchor for all later import, manual flow, reports, and ownership matching.

## 2. Scope in this iteration

Must build:

- division CRUD
- entity CRUD
- account CRUD
- account alias management
- enable / disable instead of physical delete
- initial balance required on account creation
- account code unique
- entity code unique

Must not build now:

- complex permission workflow
- bulk import for master data
- historical account merge tool

## 3. Frontend pages

### 3.1 Page
`frontend/src/views/AccountManage.vue`

### 3.2 Required regions

- left tree: division -> entity -> account
- right detail panel
- create / edit drawer
- alias management drawer

### 3.3 Tree display columns

At minimum show:

- entity short name
- account alias
- bank name
- masked account number or account code
- account type
- input method
- status

## 4. Backend files

- `backend/api/master_data.py`
- `backend/services/master_data_service.py`
- `backend/db/tables.py`
- `backend/db/schemas.py`

## 5. API list

### divisions
- `GET /api/divisions`
- `POST /api/divisions`
- `PUT /api/divisions/{id}`
- `POST /api/divisions/{id}/disable`

### entities
- `GET /api/entities`
- `POST /api/entities`
- `PUT /api/entities/{id}`
- `POST /api/entities/{id}/disable`

### accounts
- `GET /api/accounts`
- `GET /api/accounts/{id}`
- `POST /api/accounts`
- `PUT /api/accounts/{id}`
- `POST /api/accounts/{id}/disable`
- `POST /api/accounts/{id}/aliases`

## 6. Input contracts

### create account request
```json
{
  "entity_id": 1,
  "account_code": "A0001",
  "account_alias": "养护农商行手工户",
  "bank_name": "阳曲农商行",
  "branch_name": "谷镇支行",
  "account_number": "103020103000012200",
  "account_type": "general",
  "instrument_type": "bank_manual",
  "input_method": "manual",
  "currency": "CNY",
  "initial_balance": 2902.83,
  "balance_date": "2025-11-01",
  "status": "enabled",
  "notes": ""
}
```

## 7. Validation rules

- `account_code` required and unique
- `entity_id` required
- `account_alias` required
- `initial_balance` required
- `balance_date` required
- physical delete forbidden
- disabled accounts hidden by default list filter, but retrievable by status filter

## 8. Done standard

This module is complete only if:

- user can create at least 1 division, 2 entities, 3 accounts
- alias can be attached to an account
- disabled account does not disappear from history
- UI is fully Chinese
