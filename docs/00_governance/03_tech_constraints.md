# 03 Tech Constraints

## 1. Fixed stack for V1

Backend:
- Python 3.11+
- FastAPI
- SQLAlchemy
- openpyxl
- Polars

Frontend:
- Vue 3
- Vite
- Ant Design Vue
- ECharts

Database:
- SQLite only in V1

Packaging:
- local executable style
- backend serves frontend static build

## 2. Rules

- deterministic code first, AI second
- parser rules must be auditable
- no runtime model free judgment on critical accounting decisions
- keep all main logic local
- use SQLAlchemy for all DB access
- no hardcoded raw SQL everywhere
