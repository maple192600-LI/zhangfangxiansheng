# CLAUDE.md

This file gives Claude Code project-specific guidance for `账房先生`.

## Required Reading

Read `AGENTS.md` first, then `docs/README.md`. These two files define the active project entrypoint and the document priority chain.

Do not treat `new/` as authority. It is reference material only.

## Current Product Shape

`账房先生` is a local finance workbench. The user should work through uploads, previews, confirmations, and report exports, not through code, JSON, SQL, regular expressions, or manual field mapping.

The target data flow is:

```text
Upload -> rule match or Agent rule creation -> review -> accepted Parser/Rule
       -> deterministic execution -> fund_events -> reports
```

Agent creates and improves rules. Deterministic code executes accepted rules.

## Engineering Rules

- Keep one implementation per capability.
- Use GitHub Flow: branch from `main`, commit focused changes, open a PR, pass checks and review, then merge.
- Prefer editing the existing path over creating a parallel replacement.
- Preserve user/runtime data.
- Do not edit frozen contracts without explicit user approval.
- Do not add new version-suffixed names for Agent, Skill, Memory, Parser, or Rule concepts.
- Backend routes should validate and delegate to services.
- User-facing text and errors should be Chinese.
- Use `core.response.success/error` for API responses.

## Verification

For every substantial change, run the relevant checks:

```powershell
backend\venv\Scripts\python.exe tools\guards\check_canonical_schema.py
backend\venv\Scripts\python.exe tools\guards\check_primitives_whitelist.py
backend\venv\Scripts\python.exe tools\guards\check_placeholder_binding.py
backend\venv\Scripts\python.exe tools\guards\check_api_inventory.py
backend\venv\Scripts\python.exe tools\guards\check_no_runtime_llm.py
backend\venv\Scripts\python.exe tools\guards\check_no_parallel_implementations.py
backend\venv\Scripts\python.exe tools\guards\check_product_purity.py
```

If a guard fails because a frozen contract has drifted, stop and report the exact drift. Do not silently update `contracts.lock`.

For frontend-visible changes, also run:

```powershell
cd frontend
npm run build
```

Then validate the affected browser flow.

## GitHub Workflow

- Do not work directly on `main`.
- Use short-lived branches named by task type, such as `docs/git-flow`, `fix/parser-runtime`, or `feat/rule-center`.
- Use Conventional Commits.
- Every merge to `main` must go through a PR.
- PR descriptions must include changed scope, verification commands, guard results, browser validation when relevant, and known gaps.
- Do not push runtime data, logs, databases, dependency folders, local secrets, uploads, or generated reports.
