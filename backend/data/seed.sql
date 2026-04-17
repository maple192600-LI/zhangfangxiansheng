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
  (1, 'entity_match_key', '法人简称', 'text', 1, 1, 0, 1, 1, 0, 'active', datetime('now'), datetime('now')),
  (2, 'account_match_key', '账户名称', 'text', 1, 1, 0, 1, 1, 0, 'active', datetime('now'), datetime('now')),
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
   1, 'active', datetime('now'), datetime('now'))

-- 手工字段池 — 可选字段（余额/时间/业务）
INSERT INTO manual_field_pool (id, field_code, field_name_cn, data_type, is_core, is_default_visible, is_disable_allowed, is_parse_key, is_validation_key, is_batch_inheritable, status, created_at, updated_at)
VALUES
  (8, 'previous_balance_input', '上期余额', 'number', 0, 0, 1, 0, 1, 0, 'active', datetime('now'), datetime('now')),
  (9, 'ending_balance_input', '期末余额', 'number', 0, 0, 1, 0, 1, 0, 'active', datetime('now'), datetime('now')),
  (10, 'business_time', '业务时间', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now'));

-- 手工字段池 — 可选字段（业务信息）
INSERT INTO manual_field_pool (id, field_code, field_name_cn, data_type, is_core, is_default_visible, is_disable_allowed, is_parse_key, is_validation_key, is_batch_inheritable, status, created_at, updated_at)
VALUES
  (11, 'group_name', '分组', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (12, 'department_name', '所属部门', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (13, 'income_expense_type', '收支类型', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (14, 'handler_name', '经办人', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (15, 'owner_name', '负责人', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (16, 'note_text', '备注', 'text', 0, 1, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (17, 'pending_recovery_flag', '待回补', 'bool', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (18, 'voucher_no', '凭证号', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now')),
  (19, 'receipt_no', '回单编号', 'text', 0, 0, 1, 0, 0, 0, 'active', datetime('now'), datetime('now'));

-- 附加预设手工方案
INSERT INTO manual_template_schemes (id, scheme_code, scheme_name, description, selected_fields_json, is_default, status, created_at, updated_at)
VALUES
  (2, 'manual_simple_cash', '现金简版', '现金类快速录入',
   '["entity_match_key","account_match_key","business_date","summary_text","counterparty_name","income_amount","expense_amount","note_text"]',
   0, 'active', datetime('now'), datetime('now')),
  (3, 'manual_bank_manual_account', '手工银行账户简版', '无网银账户或少量手工银行发生额',
   '["entity_match_key","account_match_key","business_date","summary_text","counterparty_name","income_amount","expense_amount","previous_balance_input","ending_balance_input","voucher_no","receipt_no"]',
   0, 'active', datetime('now'), datetime('now')),
  (4, 'manual_multi_subject_with_people', '多主体总表（含人员信息）', '多主体录入带经办人和负责人',
   '["entity_match_key","account_match_key","business_date","summary_text","counterparty_name","income_amount","expense_amount","department_name","handler_name","owner_name","note_text"]',
   0, 'active', datetime('now'), datetime('now'));
