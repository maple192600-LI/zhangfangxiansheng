# 00 Project Constitution

## 1. Purpose

This file is the highest-priority execution constraint for AI coding tools working on the project.

Project name: ZhangFang  
Current stage: V1  
Current only goal: cash / fund daily workflow MVP for treasury and cashier scenarios

## 2. Hard boundaries

The tool MUST do these things:

- implement only V1 cash and fund workflow
- keep frontend as Vue 3 + Vite + Ant Design Vue
- keep backend as Python 3.11+ + FastAPI + SQLAlchemy
- keep V1 database as SQLite
- keep core workflow deterministic and rule-driven
- keep all UI text in Chinese
- keep the table workflow as the main battlefield

The tool MUST NOT do these things:

- do not introduce Electron, Tauri, Rust business layer, Docker-first architecture
- do not switch database to PostgreSQL in V1
- do not build invoice OCR main flow, expense approval, contract workflow in V1
- do not let runtime AI freely decide account ownership, final summary text, or balance correctness
- do not replace table workflow with card-only or chat-only interaction
- do not add paid grid dependencies in V1

## 3. User boundary

Target users are Chinese finance operators using Windows, Excel, online banking exports, and finance software.

The implementation must satisfy:

- double-click style local startup
- no command line required for end users
- no JSON editing required for end users
- major actions visible in UI
- errors must be readable in Chinese

## 4. V1 product scope

V1 includes:

- home dashboard
- master data center
- bank file import and parser template skeleton
- manual flow dual-track mechanism
- upload result preview
- base data table
- cash daily and account balance reports
- basic integrated reports
- export / print
- logs / backup / rollback
- AI config and built-in agent skeleton

V1 does not include:

- invoice OCR formal production flow
- expense approval production flow
- contract approval production flow
- multi-user collaboration
- centralized deployment
- custom agent creation UI

## 5. Code structure constraint

Project root should follow:

```text
backend/
  main.py
  config.py
  database.py
  core/
  db/
  api/
  services/
  agents/
  parsers/
  data/

frontend/
  src/
    views/
    components/
    api/
```

Rules:

- route layer only handles request / response
- business logic must stay in services
- data model definitions must stay in db
- export, parser, agent, logging, backup must stay in core or services
- do not build coupled monolith files

## 6. Delivery rule

After each development step, the tool must output:

- files created or modified
- functions completed
- known risks
- why this step is ready for the next one

## 7. Acceptance standard

A task is not complete unless:

- code runs
- UI is Chinese
- workflow is testable with real or de-sensitized samples
- fields and states follow the contract docs
- main workflow can be manually verified by finance users
