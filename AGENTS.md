# AGENTS.md

## Project Authority

This repository is the active workspace for `账房先生`, a local finance Agent workbench for Chinese finance operators.

Every AI coding tool must read these files before planning or editing:

1. `docs/README.md`
2. `docs/00_governance/06_document_authority_audit.md`
3. `docs/00_governance/01_scope_and_order.md`
4. `docs/00_governance/02_user_constraints.md`
5. `docs/00_governance/03_tech_constraints.md`
6. `docs/00_governance/04_coding_conventions.md`
7. `docs/00_governance/05_testing_strategy.md`
8. `docs/00_governance/08_anti_drift.md`
9. `docs/00_governance/09_agent_capability.md`
10. `docs/20_execution/16_agent_system_execution.md`
11. `docs/20_execution/17_skill_system_design.md`
12. `docs/20_execution/18_code_migration_inventory.md`

The file `docs/00_governance/00_project_constitution.md` contains frozen contracts. Do not edit it unless the user explicitly approves the contract-change flow.

## Reference Material

`new/` is a non-authority area. It may contain third-party source trees, research notes, copied experiments, and archived old project documents. It is not implementation authority for this project.

Files under `references/`, `samples/`, and `templates/` are supporting inputs. They are not product architecture authority unless an active task explicitly names them.

## Naming Rule

Use stable product names:

- Agent
- Skill
- Memory
- Parser
- Rule
- Artifact

Do not introduce new version-suffixed concepts or parallel replacement names for the same capability. Existing legacy names must be migrated through an explicit cleanup task, not copied forward.

## Product Workflow

The intended workflow is:

1. User uploads a bank statement or report template.
2. Agent helps create or improve a Parser or Rule.
3. User reviews and accepts the result.
4. The accepted Parser or Rule is saved in the rule center.
5. Daily work executes deterministic code from the accepted rule.
6. `fund_events` is the visible base data table and reporting fact source.

Agent may help create rules, explain results, and learn preferences. Runtime import, posting, aggregation, and report generation must be deterministic and must not call an LLM.

## Hard Rules

- Do not develop directly on `main`.
- Use GitHub Flow: create a short-lived branch from `main`, make scoped commits, open a PR, pass checks and review, then merge.
- Do not keep parallel implementations for the same capability.
- Do not create replacement files to bypass defects.
- Do not commit `runtime/`, `.venv/`, `node_modules/`, downloads, logs, database files, or temporary outputs.
- Do not put docs, fixtures, runtime data, or test artifacts inside `product/`.
- User-visible work must pass browser validation.
- Completion requires project guard results and test/build evidence.

## Git And PR Workflow

This project uses GitHub Flow, suitable for an open-source repository:

1. Keep `main` protected and always runnable.
2. Create branches from current `main`.
3. Use branch names like `docs/governance-cleanup`, `fix/bank-parser-runtime`, `feat/rule-center`, or `chore/api-inventory-guard`.
4. Keep each branch focused on one capability, bug, migration, or documentation cleanup.
5. Use Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `test(scope): ...`, `refactor(scope): ...`, `chore(scope): ...`, `ci(scope): ...`.
6. Open a pull request for every merge to `main`.
7. PRs must include summary, changed files, verification commands, guard results, browser validation when relevant, and known gaps.
8. Merge only after required checks pass and review comments are resolved.
9. Prefer squash merge for small focused branches; use merge commits only when preserving multi-commit history is important.
10. After merge, delete the feature branch.

When the public GitHub repository is created:

- Add the GitHub remote before pushing.
- Push the current branch to GitHub.
- Open a draft PR for work still under review, and mark it ready only after verification is complete.
- Never push secrets, local databases, runtime uploads, generated reports, logs, or dependency folders.
- Issues should track user-visible bugs, roadmap work, and migration tasks.

## Completion Checklist

Before claiming completion, provide:

- Changed file list.
- Verification commands and actual results.
- Guard results.
- Browser validation result for user-visible changes.
- Known gaps or blocked contract changes.
- PR or branch status when the work is intended for GitHub.
