# 初始化数据、样本文件与测试夹具计划

## 一、作用

这份文档用于解决一个常见问题。

项目代码开始写了，但 Claude Code 没有真实样本、没有初始化数据、没有固定测试夹具，结果写出来的接口和页面只能跑假数据。

## 二、必须准备的样本类型

### 1. 银行流水样本
至少准备：
- 中国银行 1 份
- 农业银行 1 份
- 建设银行 1 份
- 至少 1 份含新模板差异的样本

### 2. 手工流水样本
至少准备：
- 多主体总表 V2 样本 1 份
- 少量系统内快速录入等价样本 1 份
- 含异常字段缺失样本 1 份

### 3. 期望输出样本
至少准备：
- 基础数据表期望结果 1 份
- 单日日报期望结果 1 份
- 区间日报期望结果 1 份
- 导出 Excel 示例 1 份

### 4. 页面参考图
至少准备：
- 首页总控台截图
- 工作台截图
- 基础数据表截图
- 手工流水表截图
- 上传结果预览截图

## 三、初始化数据

开工时至少应准备一份 seed 数据，包含：
- 2 个大区或板块
- 3 个法人
- 6 个账户
- 至少 1 个现金账户
- 至少 1 个无网银手工账户
- 至少 1 个已停用账户
- 至少 1 套 AI 配置测试记录
- 2 个内置 Agent 配置

### Seed SQL 模板

开发阶段使用以下 SQL 作为种子数据，对应 samples/manual 样本。

```sql
-- ========================================
-- Seed Data V1
-- 与 samples/manual/manual_sample_confirmed.xlsx 配套
-- ========================================

-- 板块
INSERT INTO divisions (id, name, sort_order, status, created_at, updated_at)
VALUES
  (1, '养护板块', 0, 'enabled', datetime('now'), datetime('now')),
  (2, '票据板块', 1, 'enabled', datetime('now'), datetime('now'));

-- 法人实体
INSERT INTO entities (id, division_id, entity_code, name, short_name, status, created_at, updated_at)
VALUES
  (1, 1, 'E001', '山西喜跃发实业发展有限公司', '实业公司', 'enabled', datetime('now'), datetime('now')),
  (2, 1, 'E002', '养护分公司', '养护公司', 'enabled', datetime('now'), datetime('now')),
  (3, 2, 'E003', '路桥项目公司', '路桥公司', 'enabled', datetime('now'), datetime('now')),
  (4, 1, 'E004', '建筑安装公司', '建筑公司', 'enabled', datetime('now'), datetime('now')),
  (5, 1, 'E005', '设备租赁公司', '租赁公司', 'enabled', datetime('now'), datetime('now'));

-- 账户（含期初余额）
INSERT INTO accounts (id, entity_id, account_code, account_alias, bank_name, branch_name,
  account_number, account_type, instrument_type, input_method, currency,
  initial_balance, balance_date, status, notes, created_at, updated_at)
VALUES
  (1, 1, 'A001', '中行手工户', '中国银行', '太原分行', '6217xxxx0001',
   '银行账户', '银行存款', 'manual', 'CNY', 200000.00, '2026-03-01',
   'enabled', '无网银手工户', datetime('now'), datetime('now')),
  (2, 2, 'A101', '现金账户', NULL, NULL, NULL,
   '现金', '现金', 'manual', 'CNY', 12860.00, '2026-03-02',
   'enabled', '现金日记账', datetime('now'), datetime('now')),
  (3, 3, 'A301', '票据登记簿', NULL, NULL, NULL,
   '票据', '票据', 'manual', 'CNY', 0.00, '2026-03-02',
   'enabled', '仅记录影响资金口径的票据', datetime('now'), datetime('now')),
  (4, 3, 'A302', '受限资金手工户', NULL, NULL, NULL,
   '其他', '受限资金', 'manual', 'CNY', 95000.00, '2026-03-02',
   'enabled', '手工资金载体', datetime('now'), datetime('now')),
  (5, 4, 'A205', '农商行手工户', '农商行', '养护支行', '6210xxxx0005',
   '银行账户', '银行存款', 'manual', 'CNY', 82000.00, '2026-03-03',
   'enabled', '低频手工补录', datetime('now'), datetime('now')),
  (6, 5, 'A402', '无网银结算户', '工商银行', '太原支行', '6222xxxx0006',
   '银行账户', '银行存款', 'manual', 'CNY', 40600.00, '2026-03-04',
   'enabled', '无网银账户', datetime('now'), datetime('now'));

-- 账户别名（用于手工表匹配）
INSERT INTO account_aliases (id, account_id, alias_text, alias_type, created_at)
VALUES
  (1, 1, '中行手工户', 'display_name', datetime('now')),
  (2, 1, 'A001', 'code', datetime('now')),
  (3, 2, '现金账户', 'display_name', datetime('now')),
  (4, 2, 'A101', 'code', datetime('now')),
  (5, 3, '票据登记簿', 'display_name', datetime('now')),
  (6, 4, '受限资金手工户', 'display_name', datetime('now')),
  (7, 5, '农商行手工户', 'display_name', datetime('now')),
  (8, 6, '无网银结算户', 'display_name', datetime('now'));

-- AI 配置（测试用）
INSERT INTO ai_configs (id, provider, display_name, api_key_encrypted, base_url, model_name, is_default, status, created_at)
VALUES
  (1, 'zhipu', '智谱 GLM-4 Flash（测试）', '', 'https://open.bigmodel.cn/api/paas/v4', 'glm-4-flash', 1, 'active', datetime('now'));

-- Agent 配置
INSERT INTO agent_configs (id, agent_code, agent_name, agent_type, workspace_dir, ai_config_id, description, status, created_at, updated_at)
VALUES
  (1, 'shared', '共享能力区', 'shared', 'agents/shared', 1, '所有 Agent 共享的通用能力、工具和规则', 'active', datetime('now'), datetime('now')),
  (2, 'master', '主控 Agent', 'master', 'agents/master', 1, '负责调度各专业 Agent，理解用户意图', 'active', datetime('now'), datetime('now')),
  (3, 'parser_assistant', '解析助手', 'parser_assistant', 'agents/parser-assistant', 1, '负责解析银行流水和手工模板', 'active', datetime('now'), datetime('now'));

-- 手工字段池核心字段
INSERT INTO manual_field_pool (id, field_code, field_name_cn, data_type, is_core, is_default_visible, is_disable_allowed, is_parse_key, is_validation_key, is_batch_inheritable, status, created_at, updated_at)
VALUES
  (1, 'entity_match_key', '法人识别键', 'text', 1, 1, 0, 1, 1, 0, 'active', datetime('now'), datetime('now')),
  (2, 'account_match_key', '账户识别键', 'text', 1, 1, 0, 1, 1, 0, 'active', datetime('now'), datetime('now')),
  (3, 'business_date', '业务日期', 'date', 1, 1, 0, 1, 1, 0, 'active', datetime('now'), datetime('now')),
  (4, 'summary_text', '摘要', 'text', 1, 1, 0, 0, 1, 0, 'active', datetime('now'), datetime('now')),
  (5, 'counterparty_name', '对方名称', 'text', 1, 1, 0, 0, 1, 0, 'active', datetime('now'), datetime('now')),
  (6, 'income_amount', '收入', 'number', 1, 1, 0, 0, 1, 0, 'active', datetime('now'), datetime('now')),
  (7, 'expense_amount', '支出', 'number', 1, 1, 0, 0, 1, 0, 'active', datetime('now'), datetime('now'));

-- 默认手工方案
INSERT INTO manual_template_schemes (id, scheme_code, scheme_name, description, selected_fields_json, is_default, status, created_at, updated_at)
VALUES
  (1, 'manual_multi_subject_basic', '多主体总表标准版', '默认多主体手工总表',
   '["entity_match_key","account_match_key","business_date","summary_text","counterparty_name","income_amount","expense_amount","previous_balance_input","note_text","department_name","income_expense_type","handler_name","owner_name","pending_recovery_flag","receipt_no","voucher_no"]',
   1, 'active', datetime('now'), datetime('now'));
```

## 四、fixtures 约定

每个样本都必须配一份 fixtures 说明：
- 样本编号
- 样本来源
- 样本用途
- 预期命中模块
- 预期是否触发异常
- 预期输出文件

## 五、禁止情况

- 禁止直接拿线上真实文件不脱敏入仓库
- 禁止样本和期望结果脱节
- 禁止前端页面靠手写假数据长期顶着不接接口

## 六、Claude Code 使用方式

Claude Code 每次做导入、解析、日报、异常处理时，都必须指定正在使用哪个样本编号和哪个期望输出，不得只说“我本地试了一下”。
