# 01 V1 Scope And Order

## 1. Goal

V1 only delivers a usable local MVP for fund daily work.

The user must be able to:

- maintain divisions, entities, accounts, and initial balances
- import bank files
- upload or enter manual fund rows
- preview results before formal inclusion
- generate base data and reports by date range
- export and print
- view simple dashboard
- use backup, rollback, and logs

## 2. Development order

The AI coding tool must follow this order:

1. project skeleton and startup
2. database and base tables
3. master data center
4. AI config and built-in agent skeleton
5. bank import and parser template skeleton
6. manual flow dual-track mechanism
7. upload result preview and manual maintenance
8. base data table and report generation
9. home dashboard
10. export, print, backup, rollback, logs
11. integration testing
12. real sample regression

No step may skip the previous one.

## 3. Required docs to read before coding

The tool must read:

- 00_project_constitution.md
- 02_user_constraints.md
- 03_tech_constraints.md
- all module execution docs
- all contract docs

## 4. Done criteria for V1

V1 is done only if all of the following are true:

- local startup works
- home dashboard works
- bank import works for at least 2 bank formats
- manual flow works through quick entry and Excel upload
- upload result preview can hold pending and abnormal rows
- base data table is generated from all valid rows
- report pages can query by date range
- export and print work
- rollback by batch works
- backup and restore work
- logs can be checked
