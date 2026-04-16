# V1 执行文档 02｜AI 配置与 Agent 骨架

## 一、文档目的

本文档用于约束 V1 中与 AI 相关的两块内容。

第一块是 AI 服务商配置。

第二块是 Agent 基础骨架与工作区目录。

当前阶段只做骨架、入口、基础加载逻辑和最小可用配置，不做跨阶段的大型 Agent 平台。

## 二、本块在 V1 中的作用

这一块不是为了炫技。

它的作用有三层。

一层，让用户能在界面里把 API Key 配好，后续模板识别、规则草案、查数辅助才有基础。

一层，让系统从 V1 开始就有 Agent 的工作区隔离思路，后续做费用 Agent、成本 Agent、分析 Agent 时不用推倒重来。

一层，让 Cloud Code 先把“骨头”长好，肉以后再长。

## 三、本块当前只做什么

当前块只做下面这些内容。

AI 厂商配置页面。

AI 连接测试。

默认 AI 配置的读写存储。

Agent 目录结构创建。

shared 公共区创建。

内置总管 Agent 与解析助手目录创建。

Agent 文件加载骨架。

一个最基础的 Agent 配置表。

一个极简的 Agent 管理只读界面或配置卡片。

## 四、本块当前不做什么

当前块不做下面这些内容。

用户自定义创建 Agent。

多 Agent 自动协作。

Agent 自主执行复杂任务流。

Agent 自动改规则并生效。

Agent 完整对话平台。

Agent 自主学习闭环。

## 五、AI 配置的业务要求

### 1. 用户必须能看懂

配置页面必须全中文。

不能让用户手动改 JSON。

不能让用户去写环境变量。

不能让用户理解 provider code、header、payload 这些技术词。

### 2. 页面中至少应有这些字段

- AI 服务商
- 显示名称
- API Key
- Base URL，可选
- 模型名称
- 是否默认
- 当前状态

### 3. 默认支持的服务商

第一阶段建议至少预置：

- 智谱清言
- Kimi
- 通义千问
- OpenAI 兼容接口
- Ollama 本地模型
- 自定义兼容接口

页面中对用户展示中文厂商名。

### 4. 必须有测试连接

用户填完 API Key 后，必须有“测试连接”按钮。

测试成功后再允许保存会更稳。

至少要把测试结果明确告诉用户。

## 六、数据库要求

AI 配置表 `ai_configs` 必须正式落表。

字段至少包含：

- id
- provider
- display_name
- api_key，加密存储
- base_url
- model_name
- is_default
- status
- created_at

此外必须补 `agent_configs` 表。

字段至少包含：

- id
- agent_id
- display_name
- is_builtin
- is_enabled
- permissions
- ai_config_id
- created_at

## 七、加密与安全要求

API Key 不允许明文裸存。

后端必须提供最基础的加密存储工具。

建议放在：

- `backend/core/security.py`

第一阶段做到对称加密即可。

重点是本地存储时不要明文直写数据库。

## 八、Agent 工作区结构硬约束

V1 就要把工作区目录结构建好。

目录建议如下。

```text
backend/agents/
├── shared/
│   ├── COMPANY.md
│   ├── KNOWLEDGE.md
│   └── DATA_SCHEMA.md
│
├── master/
│   ├── SOUL.md
│   ├── AGENT.md
│   ├── USER.md
│   ├── MEMORY.md
│   ├── TOOLS.md
│   ├── RULES.md
│   └── WORKFLOW.md
│
├── parser-assistant/
│   ├── SOUL.md
│   ├── AGENT.md
│   ├── USER.md
│   ├── MEMORY.md
│   ├── TOOLS.md
│   ├── RULES.md
│   └── WORKFLOW.md
│
└── custom/
```

## 九、shared 公共区要求

shared 目录是公共知识区。

它的职责是承载可共享但不混乱的公共内容。

### 1. COMPANY.md

用于生成公司信息摘要。

V1 先做到根据数据库里的大区、法人、账户基础信息自动生成简版内容即可。

### 2. KNOWLEDGE.md

作为公共知识库预留。

V1 可以先空置或写入系统初始化说明。

### 3. DATA_SCHEMA.md

用于描述当前数据库结构。

V1 可以先由系统生成简版。

## 十、Agent 文件的职责边界

### SOUL.md

负责气质、表达方式、身份底色。

### AGENT.md

负责角色定义与职责描述。

### USER.md

负责用户偏好和对该 Agent 的特别要求。

### MEMORY.md

负责该 Agent 自己的记忆。

### TOOLS.md

负责工具权限与数据访问边界。

### RULES.md

负责该 Agent 必须遵守的业务规则。

### WORKFLOW.md

负责标准工作流。

## 十一、V1 里两个内置 Agent 的最小要求

### 1. master

定位是总管 Agent。

V1 不要求它真能做复杂总管调度。

但目录、权限表、配置记录必须有。

### 2. parser-assistant

定位是解析助手。

它是 V1 后续“新银行模板识别与保存”这条链路的重要预埋角色。

当前阶段至少要保证它有独立目录、独立配置项、独立文件组。

## 十二、后端实现要求

后端需至少新增或完善以下文件。

- `backend/core/ai_provider.py`
- `backend/core/agent_engine.py`
- `backend/core/security.py`
- `backend/api/agent.py`
- `backend/api/settings.py`
- `backend/db/tables.py`
- `backend/services/agent_service.py`，可新增

### ai_provider.py

负责统一不同厂商的调用入口。

V1 只要把配置读取、基础测试连通性、最小调用接口定义好即可。

### agent_engine.py

负责加载 Agent 目录、读取七类文件、返回 Agent 元信息。

V1 不要求复杂推理调度。

先实现“能读取、能列出、能初始化”的能力。

## 十三、前端实现要求

建议至少补以下页面或区块。

- `frontend/src/views/AIConfig.vue`
- `frontend/src/views/AgentManage.vue`，可先做极简版

AI 配置页必须让用户：

- 新增配置
- 编辑配置
- 设为默认
- 测试连接
- 启用或停用

Agent 管理页第一阶段可只展示：

- 总管 Agent
- 解析助手
- 当前状态
- 使用的模型配置
- 是否启用

## 十四、自测场景

### 场景 1

用户新增一个智谱清言配置。

填入 API Key。

点击测试连接。

提示成功。

保存后可设为默认。

### 场景 2

用户新增一个 Ollama 本地模型配置。

填本地地址。

测试连接。

保存成功。

### 场景 3

系统首次启动时，自动创建 shared、master、parser-assistant 目录与基础 md 文件。

### 场景 4

Agent 管理页能显示两个内置 Agent，并能读出它们是否启用。

## 十五、本块完成标准

用户能在中文界面里完成 AI 配置。

API Key 不明文裸存。

至少存在 shared、master、parser-assistant 三套目录。

七类 md 文件骨架已生成。

后端可读取 Agent 元信息。

前端可展示当前内置 Agent 状态。

## 十六、本块完成后的衔接

这一块完成后，才适合进入“银行流水导入与模板识别”。

因为新模板识别会依赖 AI 配置，解析助手也要有挂载位置。
