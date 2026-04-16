# 仓库开工与目录落地规范

## 一、作用

这份文档用于在 Claude Code 正式开工前，把仓库目录、命名规则、文件摆放位置一次定死。

没有这份文档，AI coding 工具最容易犯的错就是把代码、文档、样本、脚本、导出逻辑堆成一坨。

## 二、仓库顶层目录

```text
zhangfang/
├── docs/
├── backend/
├── frontend/
├── build/
├── samples/
├── exports/
├── scripts/
├── tests/
└── README.md
```

## 三、docs 目录

```text
docs/
├── 00_project_constitution.md
├── 01_v1_scope_and_order.md
├── 02_user_constraints.md
├── 03_tech_constraints.md
├── modules/
├── contracts/
└── tests/
```

要求：
- 生效文档只保留一份
- 历史文档移入 `docs/archive/`
- 任何执行文档不得写成聊天纪要口吻

## 四、backend 目录

```text
backend/
├── main.py
├── config.py
├── database.py
├── requirements.txt
├── api/
├── core/
├── db/
├── services/
├── parsers/
├── agents/
├── data/
└── migrations/
```

要求：
- 路由层只做收发参数
- 业务逻辑进入 `services/`
- 通用引擎进入 `core/`
- 表定义进入 `db/`
- 解析器存储与模板匹配能力进入 `parsers/`

## 五、frontend 目录

```text
frontend/
├── package.json
├── vite.config.js
└── src/
    ├── api/
    ├── views/
    ├── components/
    ├── layouts/
    ├── stores/
    ├── router/
    ├── styles/
    └── utils/
```

要求：
- 页面按模块拆分到 `views/`
- 页面级复用组件进入 `components/`
- 样式与主题分离
- 接口请求统一收敛到 `src/api/`

## 六、samples 目录

```text
samples/
├── bank/
├── manual/
├── screenshots/
└── expected_outputs/
```

要求：
- 所有样本脱敏
- 每个样本必须带说明文档
- 样本与测试文档引用同名标识

## 七、tests 目录

```text
tests/
├── backend/
├── frontend/
├── e2e/
└── fixtures/
```

要求：
- fixtures 与 samples 保持一一对应
- E2E 用例命名要能直接对应验收文档

## 八、命名规则

- 文档统一使用数字前缀排序
- 数据库表名使用小写复数
- API 路径使用小写加中划线
- Vue 页面文件使用 PascalCase
- Python 模块文件使用小写加下划线

## 九、开工前检查

Claude Code 开工前必须确认：
- 目录骨架存在
- 文档目录存在
- 样本目录存在
- 备份目录存在
- README 中写清本地启动命令
