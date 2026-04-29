# AGENTS.md

## MUST READ FIRST

- `docs/01_项目文件地图与交付边界.md`
- `PRD_账房先生_本地财务Agent工作台.md`
- `docs/03_AI_Coding_开发协作规范.md`
- `docs/02_测试与验收规范.md`
- `docs/24_产品代码开发路线图.md`
- `docs/25_技术栈与工程架构蓝图.md`

## ROUTE RULES

Read only matching rule cards from `rules/`.

- Excel / template / parser / mapping: `rules/01_禁止硬编码与模板适配.md`
- master data / settings / linkage: `rules/02_单一事实源与数据联动.md`
- visible UI / upload / export / preview: `rules/03_浏览器验收.md`
- workflow / nodes / canvas / version: `rules/04_工作流配方.md`
- dynamic objects / fields / data center: `rules/05_动态业务对象.md`
- PR / completion / review: `rules/06_PR与完成定义.md`
- file placement / delivery package: `rules/07_文件边界与交付白名单.md`
- temp files / test outputs / downloads / logs: `rules/08_临时文件与开发产物清理.md`
- bugfix / replacement / refactor: `rules/09_问题修复与替换实现清理.md`
- dependency / env / database / install: `rules/10_环境隔离与依赖安装.md`
- GitHub / branch / PR / optional multi-device work: `rules/11_GitHub分支与PR开发.md`
- guard checks / pre-PR / packaging checks: `rules/12_项目护栏检查.md`
- delete feature / delete page / delete test file / delete template during development: `rules/13_开发阶段删除语义.md`
- app delete / disable / archive / void / rollback / lifecycle: `rules/14_正式产品删除与生命周期.md`
- task card / issue / PR template / handoff: `rules/15_任务单与PR模板.md`
- GitHub private repo / first commit / first PR: `rules/16_GitHub仓库创建与首次提交.md`
- project guard script implementation: `rules/17_项目护栏脚本实现.md`
- browser acceptance record / frontend verification: `rules/18_浏览器验收记录.md`
- fixtures / sample files / expected outputs / uploaded test files: `rules/19_样本与测试文件管理.md`
- data model / field dictionary / master data / dynamic object: `rules/20_数据模型与字段字典.md`
- API / frontend-backend contract / error code / page API map: `rules/21_API与前后端契约.md`
- workflow recipe schema / nodes / canvas / execution record: `rules/22_工作流配方详细设计.md`
- Agent Runtime / workspace / memory / context / tool permissions: `rules/23_Agent_Runtime与权限边界.md`
- Skill loading / global Skill / workspace Skill / compatibility import / skill-creator / allowed_agents / permissions / node registration: `rules/24_Skill目录与生命周期.md`
- repository setup / first setup / initial directories / `.gitignore`: `docs/09_开发环境初始化手册.md`

## NEVER

- Hardcode sample files, filenames, columns, cells, sheets, or one-off template branches.
- Claim completion without browser validation for user-visible work.
- Modify tests or reference samples to hide failure.
- Store master-data names as facts when stable ids are required.
- Let an agent write application data directly.
- Work directly on `main` for implementation tasks.
- Keep parallel implementations for the same capability.
- Create parallel replacement files to bypass a defect.
- Treat a development-time delete request as hide-only or frontend-only deletion.
- Treat app delete actions as frontend-only deletion or undefined deletion.
- Commit `data/`, `.venv/`, `node_modules/`, downloads, logs, or temporary outputs.
- Put docs, fixtures, runtime data, or test artifacts inside `app/`.

## DONE REQUIRES

- Relevant docs read.
- Relevant rule cards read.
- Minimal scoped changes.
- Backend self-check.
- Browser validation path.
- Browser acceptance record path when user-visible work is involved.
- User-visible check steps.
- Temp artifact cleanup status.
- Replaced entry / reference cleanup status.
- Delete residual search result when deletion is involved.
- app delete lifecycle meaning and impact check when app data is involved.
- Branch / PR status when GitHub is used.
- Project guard check result.
- Task card and PR template completeness.
- Risk and rollback note.

