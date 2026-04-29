# AGENTS.md

## MUST READ

This repository currently stores the planning documents in `new/`.

`new/` is a documentation location, not the required future development directory.

Read first:

- `new/AGENTS.md`
- `new/00_项目文件地图与交付边界.md`
- `new/PRD_账房先生_本地财务Agent工作台.md`
- `new/13_AI_Coding_开发协作规范.md`
- `new/12_测试与验收规范.md`

## AUTHORITY

Only the files listed above are implementation authority for this project.

Any other files in the workspace are not development input unless the user explicitly names them.

The final development workspace may be any folder or GitHub repository selected by the user later.

## HARD RULES

- Do not develop directly on `main`.
- Do not keep parallel implementations for the same capability.
- Do not create parallel replacement files to bypass defects.
- Do not commit `runtime/`, `.venv/`, `node_modules/`, downloads, logs, or temporary outputs.
- Do not put docs, fixtures, runtime data, or test artifacts inside `product/`.
- User-visible work must pass browser validation.
- Completion requires project guard check result.
