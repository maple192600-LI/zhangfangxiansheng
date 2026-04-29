# 交接 Prompt：账房先生 Agent 系统开发

> 把下面这段（从"=== 任务开始 ==="到"=== 任务结束 ==="）整段贴给目标 AI Coding 工具
> （Claude Code / Cursor / Codex / Continue 等都可用）。
> 它是自包含的：不需要这段对话上下文。

---

```
=== 任务开始 ===

你是账房先生项目的接手开发者。下面给你完整的任务背景、项目状态、必须读的资料、分阶段任务、验收标准、约束条件。请严格按 §7 的执行顺序工作。

===========================================================================
§1 项目背景
===========================================================================

账房先生（ZhangFang）是一款面向中国财务人员的本地部署财务工作台，
项目根目录：F:/zhangfangxiansheng/
后端：Python 3.11 + FastAPI + SQLAlchemy + SQLite，跑在 127.0.0.1:8000
前端：Vue 3 + Vite + Pinia + Ant Design Vue，build 后由后端 serve
启动方式：双击 F:/zhangfangxiansheng/start.bat
默认登录：用户 admin（密码用户已改过，不要重置）
本地 LLM：Ollama 已安装在 127.0.0.1:11434，模型 qwen3:8b 可用

业务用户是**非程序员**——只会从浏览器使用，不会用命令行。
所有"验收"都必须是用户在浏览器里点出来的可见效果，不能是 curl 命令。

===========================================================================
§2 你要做什么
===========================================================================

实现一套真正的"AI Agent"系统，替代当前所谓 agent（其实只是 LLM 调用链）。

核心理念：
  - Agent = 岗位主体（理解+编排）：理解业务意图、生成规则、写脚本草案、
    调用工具试运行、解释差异、维护 skill。
  - Skill = 手艺（确定性执行）：调用 Python/DuckDB/openpyxl/Polars/模板解析器/导出器。
  - Agent 负责"编排和理解"，工具/Skill 负责"确定性执行"。
  - 用户可自由命名 agent（"财务总监"/"出纳助手"等中文名）、自建多个 agent。

参考开源项目（已调研定型）：
  - 主参考：SafeRL-Lab/nano-claude-code (CheetahClaws)
    https://github.com/SafeRL-Lab/nano-claude-code
    Python 实现，多 provider，含 Skill/Plugin/Memory/Session/Permission 全套体系。
    重点学：agent.py（generator 流式 loop 范本）、tool_registry.py（注册装饰器）、
    skill/（skill 系统）、providers.py（多 provider 抽象）。
  - 次参考：TeeWhyKay/claude-code-python-rewrite（src/ 目录组织）

===========================================================================
§3 必读资料（不读完不准动手）
===========================================================================

1. **完整开发文档**（最高优先级，包含 SQL 表结构、组件设计、Phase 验收）：
   F:/zhangfangxiansheng/docs/70_agent_v2/AGENT_DEV_DOC.md

2. **项目宪法 + 技术约束**：
   F:/zhangfangxiansheng/docs/00_governance/00_project_constitution.md
   F:/zhangfangxiansheng/docs/00_governance/03_tech_constraints.md
   F:/zhangfangxiansheng/CLAUDE.md

3. **现有代码必读**：
   F:/zhangfangxiansheng/backend/main.py            后端入口、路由注册
   F:/zhangfangxiansheng/backend/core/ai_call.py    LLM 调用封装（要扩展支持 streaming）
   F:/zhangfangxiansheng/backend/core/ai_provider.py 8 provider 配置
   F:/zhangfangxiansheng/backend/db/tables.py       现有 ORM 表（参考写法）
   F:/zhangfangxiansheng/backend/api/report_template.py 现有 API 风格参考
   F:/zhangfangxiansheng/frontend/src/layouts/MainLayout.vue 左侧导航现状
   F:/zhangfangxiansheng/frontend/src/router/index.js 路由配置
   F:/zhangfangxiansheng/frontend/src/api/index.js  axios 封装

4. **前任的 worktree 实验**（已实现的 Pipeline + bank_parser，可参考但不直接复用）：
   F:/zhangfangxiansheng/.claude/worktrees/nostalgic-blackburn-c67849/backend/agents/harness/
   特别是 skills/bank_parser.py（招行/中行解析逻辑已用本地 Ollama 验证通过）。
   这套作为 Phase 2 的 parse_bank_zhaoshang skill 实现的种子代码。

===========================================================================
§4 必须遵守的约束
===========================================================================

约束 A. 用户视角验收
  - 每个 Phase 的验收标准都是"用户在浏览器里点出来的可见效果"
  - 不允许用 curl 命令作为验收
  - 不允许跳过 Phase 顺序，必须 Phase 1 全部通过才进 Phase 2

约束 B. 不要破坏现有功能
  - 现在已经能用的：账户数据管理、报表模板管理、银行流水导入（基本闭环）
  - 你不能改它们的数据库表结构或 API 路由
  - 你只能"新增" agents_v2 / skills_v2 等新表和 /api/agent_v2/* 新路由

约束 C. 技术栈固定
  - 后端：FastAPI + SQLAlchemy（不引 Django、Flask）
  - 前端：Vue 3 Composition API + Pinia + 现有 Ant Design Vue
  - 流式协议：SSE（不用 WebSocket）
  - LLM client：复用 backend/core/ai_call.py，按需扩展 streaming
  - 沙箱：subprocess + resource limits（不引 Docker）

约束 D. 取消现有 7 个 agent 占位符
  - frontend/src/layouts/MainLayout.vue 第 ~225 行附近的"AI智能体"分组
  - 当前硬编码了 7 个：规则agent / 日报agent / 费用agent / 收入agent / 材料agent / 工资税费agent / 自定义agent
  - 全部删除，改为从后端拉取 agent 列表动态渲染 + 末尾加一个"+ 新建 agent"

约束 E. UI/UX 风格延续
  - 配色：暖色系（柔和浅暖中性背景 + 低饱和稳重绿色主强调色 + 砂金/暖棕辅助色）
  - 大圆角、轻阴影、温度感微文案
  - 参考现有页面（AccountManage.vue / ReportTemplate.vue）的样式

约束 F. 中文优先
  - 所有用户可见文字（按钮、提示、错误消息）必须是中文
  - 代码注释优先中文（参考 docs/70_agent_v2/AGENT_DEV_DOC.md 的写法）

约束 G. 测试用真实样本
  - 桌面上的真实模板：C:/Users/Administrator/Desktop/zhangfang/
  - 真实银行流水：F:/zhangfangxiansheng/samples/bank/
  - 不要凭空造测试数据

约束 H. 用户不会修密码
  - admin 用户密码已被用户改过，你不可以重置
  - 测试时如果需要 token，让用户告诉你或用浏览器 localStorage 里现有的

===========================================================================
§5 关键文件结构（必须按这个组织）
===========================================================================

后端新增：
  backend/
    api/
      agent_v2.py                  ← 新路由
    agents_v2/                     ← 新模块
      __init__.py
      runtime.py                   agent loop（generator 流式）
      provider.py                  Provider 抽象（适配 ollama）
      tool_registry.py             ToolDef + register_tool 装饰器
      tools/
        __init__.py
        fs.py                      fs_read / fs_write / fs_list / fs_edit
        shell.py                   bash_run（白名单）
        python_run.py              python_exec（沙箱）
        duckdb_q.py                duckdb_query
        openpyxl_io.py             openpyxl_read / openpyxl_write
        db_read.py                 db_query_business
        memory.py                  memory_save / memory_search / memory_recall
        skill_ops.py               skill_create / skill_test / skill_run / skill_list
        task.py                    task_create / task_update / task_list
        ask_user.py                ask_user
      skill_loader.py              加载 manifest.yaml + run.py
      memory_store.py              记忆持久化
      session_store.py             会话历史
      permission.py                权限网关
      workspace.py                 工作区文件 IO
      sse_helper.py                SSE 事件序列化

前端新增：
  frontend/src/
    api/agentV2.js                 ← agent v2 API 封装
    stores/agents.js               ← pinia store（导航数据源）
    views/AgentList.vue            ← /agents 列表页
    views/AgentDetail.vue          ← /agents/:id 详情（含 tabs）
    views/agent/                   ← AgentDetail 的子组件
      ChatPanel.vue                聊天 + 文件区
      SettingsPanel.vue            设置 tab
      SkillsPanel.vue              技能 tab
      FilesPanel.vue               文件 tab
      MemoryPanel.vue              记忆 tab
      SessionsPanel.vue            会话历史 tab
    components/agent/
      AgentCreateModal.vue         新建 agent 弹窗
      ToolCallBlock.vue            工具调用块（折叠/展开）
      MessageBubble.vue            消息气泡

数据存储：
  backend/data/agents/{agent_code}/
    workspace/{inbox,outputs,tmp}/
    skills/{skill_code}/{manifest.yaml, run.py, tests/}
    memory/*.md
    sessions/{YYYY-MM-DD}/{ses_xxx.jsonl}
    sessions/latest.json

===========================================================================
§6 分阶段任务（严格按顺序，不要跳）
===========================================================================

——— Phase 1（5 天）：agent 列表 + 新建/删除 + 简单对话 ———

后端：
  1. 加 6 张表（见 AGENT_DEV_DOC.md §3.1），用 alembic 迁移
  2. 实现 agents_v2/runtime.py 的 run_turn generator
  3. 实现 agents_v2/provider.py 包装 ollama streaming（chat /api/chat 接口 stream=true）
  4. 实现 agents_v2/tool_registry.py：装饰器 + schema 自动推断
  5. 实现 4 个最小工具：fs_list / memory_save / memory_search / ask_user
  6. 实现 agents_v2/permission.py
  7. 实现 api/agent_v2.py：
     - GET    /api/agent_v2/agents                  列出 active
     - POST   /api/agent_v2/agents                  新建（自动建工作区目录）
     - GET    /api/agent_v2/agents/{id}             详情
     - PUT    /api/agent_v2/agents/{id}             改名/role_prompt/model
     - DELETE /api/agent_v2/agents/{id}             软删（status=deleted）
     - POST   /api/agent_v2/agents/{id}/sessions    新会话
     - GET    /api/agent_v2/agents/{id}/sessions    会话列表
     - POST   /api/agent_v2/sessions/{sid}/messages SSE 流式接收消息

前端：
  1. 创建 stores/agents.js (pinia)
  2. 改造 MainLayout.vue 的"AI智能体"分组为动态从 store 渲染
  3. 末尾固定加"+ 新建 agent"项，点击触发 AgentCreateModal
  4. AgentCreateModal.vue：表单（名字必填、role_prompt 可空、AI 配置下拉必选）
  5. 新建路由 /agents/:id 指向 AgentDetail.vue
  6. AgentDetail 默认显示 ChatPanel（tab=chat）+ Settings tab
  7. ChatPanel：消息流（用 EventSource 接 SSE） + 输入框 + 发送
  8. SettingsPanel：name/role_prompt/model 编辑 + 保存 + 删除按钮

验收（必须用户视角，全部在 Chrome 里点）：
  ✅ 1. 登录后点左侧"AI智能体" → 看不到 7 个占位符，看到空 + "+ 新建 agent"
  ✅ 2. 点"+ 新建 agent" → 弹窗：填"财务总监" + 岗位职责 + 选 ollama qwen3:8b → 保存
  ✅ 3. 左导航**立即出现**"财务总监"（不刷新页面）
  ✅ 4. 点"财务总监" → 进入聊天界面，标题"财务总监"
  ✅ 5. 输入"你好,你是谁" → 回车 → 流式回复（基于 role_prompt）
  ✅ 6. 切到"设置"tab → 看到 name/role_prompt/model，可改可保存
  ✅ 7. 点"删除"按钮 → 二次确认 → 确认 → 左导航该 agent 消失

技术验收：
  - 6 张表全部建好，agent_messages 表有该会话消息
  - data/agents/{ag_xxx}/ 目录自动创建
  - 单元测试覆盖率 ≥ 80%（runtime / tool_registry / permission）

——— Phase 2（4 天）：工作区文件 + 第一个真实技能 ———

后端：
  1. 工具补全：fs_read / fs_write / fs_edit / openpyxl_read / openpyxl_write /
     db_query_business / duckdb_query / python_exec / bash_run
  2. 实现 skill_loader.py：加载 manifest.yaml + 执行 run.py
  3. 实现 skill 4 个工具：skill_list / skill_run / skill_test / skill_create
  4. 移植 worktree 的 bank_parser.py 到 skills/parse_bank_zhaoshang/
     （路径：data/agents/{system}/skills/parse_bank_zhaoshang/）
     ※ 需要让所有 agent 都能用全局 skill，不只是创建者
  5. 文件上传 API：POST /api/agent_v2/agents/:id/files（multipart）

前端：
  1. ChatPanel 加右侧文件树组件
  2. ToolCallBlock 组件：折叠/展开、状态色（蓝/绿/红）、显示参数和结果摘要
  3. SkillsPanel：表格列（display_name / status / verified_at / 验证次数 / 操作）
     操作列：手动运行（输入参数 → 跑 → 看结果）/ 测试

验收：
  ✅ 1. 上传 招行.xlsx 到 inbox → 文件树立即出现
  ✅ 2. 在聊天里说"用招行解析技能解析刚上传的文件"
  ✅ 3. 看到工具调用块"skill_run(parse_bank_zhaoshang)"，几秒后显示解析了 N 行
  ✅ 4. AI 询问是否写库 → 用户确认 → 调 db_query_business 写入 fund_events
  ✅ 5. 切到"基础数据表"业务页面 → 看到刚才写入的流水
  ✅ 6. 进 agent "技能"tab → 看到"招商银行流水解析"verified

技术验收：
  - 端到端延迟（ollama qwen3:8b，1 次 tool call）< 10s
  - 上传 100KB Excel < 1s

——— Phase 3（5 天）：AI 自创建技能 ———

后端：
  1. skill_create 工具：传 name + description + run.py 字符串 + tests，自动落盘
  2. skill_test 工具：跑 tests/ 比对 expected.json，返回 diff
  3. system prompt 加"如何编写新 skill"的范式（参考 CheetahClaws 类似 prompt）

前端：
  1. SkillsPanel 加"教 agent 学新手艺"按钮 → 弹窗引导上传样本+目标描述
  2. SkillDetail.vue（路由 /agents/:id/skills/:scode）：源码只读高亮 + 测试结果表

验收：
  ✅ 1. 用户上传中行流水样本 + 描述目标 → agent 在聊天里：
       fs_read 看样本 → 识别字段 → 起草 run.py + expected.json →
       skill_test 验证 → 失败迭代 → 通过后 skill_create 落盘
  ✅ 2. agent 在聊天回复"已学完，技能名: 中行流水解析，已通过测试"
  ✅ 3. 技能 tab 出现新 skill verified
  ✅ 4. 上传不同月份的中行流水 → 调用该 skill → 一次成功不再走 LLM 起草

——— Phase 4（4 天）：业务场景闭环 ———

后端：
  1. 新建 agent 时支持"快速模板"参数：
     - 出纳助手（预填 role_prompt + 拷贝 3 个内置 skill）
     - 报表分析师
     - 自定义（空白）
  2. 内置 skill：gen_report（按 layout + 时间区间 + entity_id 从 fund_events 取数 →
     openpyxl_write 填到模板 → 输出 .xlsx，全程不调 LLM）
  3. 业务页面"生成报表"按钮调对应 agent 的 gen_report skill

前端：
  1. AgentCreateModal 加"快速模板"下拉
  2. 业务页面（cash-journal / account-balance 等）"生成报表"按钮接 gen_report

验收：
  ✅ 1. 用快速模板"出纳助手"建 agent
  ✅ 2. 上传招行/中行流水 → agent 自动解析进 fund_events
  ✅ 3. "现金日记账"业务页面 → 点"生成报表" → 调 gen_report skill →
       下载到 .xlsx，与原模板格式一致
  ✅ 4. 性能：1000 行 fund_events + 现金日记账模板 → < 3 秒
  ✅ 5. 幂等：同输入 5 次输出一致

===========================================================================
§7 你的执行流程
===========================================================================

每次接到工作时：

第 1 步：读完 §3 列的所有资料，确认理解。
        如果有任何歧义，停下来在聊天里报告，不要猜。

第 2 步：报告当前要做哪个 Phase / 哪个子任务，
        列出预计触碰的文件清单（"我打算改 / 新增 X 个文件"）。
        等用户回"OK 开干"再动手。

第 3 步：实现，遵守 §4 约束。每完成 1 个子任务就在 Chrome 里点一遍验收点，
        截图或描述效果给用户看，不要自我宣布"完成"。

第 4 步：每个 Phase 全部验收点都点过 → 写一份 PHASE_N_REPORT.md
        放到 docs/70_agent_v2/，列：
        - 实际改/新增的文件清单
        - 每个验收点的实测结果（含截图链接）
        - 已知风险/未做的事
        - 下一步建议

第 5 步：让用户确认 PHASE_N_REPORT 后再开 Phase N+1。

===========================================================================
§8 不要做的事
===========================================================================

- 不要重置任何用户密码
- 不要改 backend/db/tables.py 里现有表的结构（只能加新表）
- 不要改现有 API 的 response shape
- 不要写 hardcode 的 7 个 agent 占位符（必须动态从 DB 拉）
- 不要在 Phase 1 验收前开始 Phase 2
- 不要凭空造测试数据，用桌面真实模板和 samples/bank/ 真实流水
- 不要引入 Docker、Redis、Celery、WebSocket 等新基础设施
- 不要给非用户主动要求的功能（语音/图片/MCP/多 agent orchestration）

===========================================================================
§9 完成后交付清单
===========================================================================

完成 Phase 1-4 后必须有：
  - [x] backend/agents_v2/ 完整模块
  - [x] backend/api/agent_v2.py 完整路由
  - [x] frontend/src/views/AgentList.vue + AgentDetail.vue 等完整页面
  - [x] data/agents/system/skills/ 内置至少 4 个 skill：
        parse_bank_zhaoshang / parse_bank_zhonghang / parse_report_template / gen_report
  - [x] docs/70_agent_v2/PHASE_1_REPORT.md ~ PHASE_4_REPORT.md
  - [x] 单元测试覆盖率 ≥ 80%
  - [x] 一份用户操作手册：docs/70_agent_v2/USER_GUIDE.md
        （非程序员读得懂，全是"在浏览器里点 X 看到 Y"）

=== 任务结束 ===
```

---

## 使用说明

把上面 ```` ``` ```` 包裹的整段（从 `=== 任务开始 ===` 到 `=== 任务结束 ===`）整段复制粘贴给目标 AI Coding 工具即可。

如果用 Claude Code，也可以这样开 session：

```bash
cd F:/zhangfangxiansheng
claude code --task "$(cat docs/70_agent_v2/HANDOFF_PROMPT.md)"
```

如果用 Cursor，新开一个 Composer 窗口，把上面整段贴进去。

如果用 Codex CLI，用 `codex --instructions docs/70_agent_v2/HANDOFF_PROMPT.md`。

接到的 AI 应该先回应"我已读完 §3 列的所有资料，准备进 Phase 1，预计触碰文件 X 个，请确认开干"——如果它直接动手没确认，停下让它重读 §7。
