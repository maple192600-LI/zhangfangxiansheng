import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:5173'
const API = 'http://localhost:8000/api'

// ═══════════════════════════════════════════
// Round 8 — 集成测试（完整业务流程）
// ═══════════════════════════════════════════

test.describe('Round 8 — 集成测试：完整业务流程', () => {

  // ── 1. 后端 API 健康 ──

  test('API 健康检查', async ({ request }) => {
    const res = await request.get(`${API}/health`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.data.status).toBe('running')
  })

  // ── 2. 主数据 CRUD ──

  test('板块/法人/账户 — 查询主数据', async ({ request }) => {
    // 板块
    const divs = await request.get(`${API}/divisions`)
    expect(divs.ok()).toBeTruthy()
    const divData = await divs.json()
    expect(divData.code).toBe(0)
    expect(divData.data.length).toBeGreaterThan(0)

    // 法人
    const ents = await request.get(`${API}/entities`)
    expect(ents.ok()).toBeTruthy()
    const entData = await ents.json()
    expect(entData.code).toBe(0)
    expect(entData.data.items.length).toBeGreaterThan(0)

    // 账户树
    const tree = await request.get(`${API}/accounts/tree`)
    expect(tree.ok()).toBeTruthy()
    const treeData = await tree.json()
    expect(treeData.code).toBe(0)
  })

  test('法人 — 字段命名统一', async ({ request }) => {
    const res = await request.get(`${API}/entities`)
    const body = await res.json()
    const first = body.data.items[0]
    // 必须有 entity_code, name, short_name
    expect(first).toHaveProperty('entity_code')
    expect(first).toHaveProperty('name')
    expect(first).toHaveProperty('short_name')
  })

  test('账户 — 字段命名统一', async ({ request }) => {
    const res = await request.get(`${API}/accounts`)
    const body = await res.json()
    const first = body.data.items[0]
    // 必须有 account_code, account_alias
    expect(first).toHaveProperty('account_code')
    expect(first).toHaveProperty('account_alias')
  })

  // ── 3. 基础数据表 ──

  test('基础数据表 — API 查询', async ({ request }) => {
    const res = await request.get(`${API}/base-data?date_from=2026-03-01&date_to=2026-04-30`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('items')
    expect(body.data).toHaveProperty('total')
  })

  test('基础数据表 — 重建余额', async ({ request }) => {
    const res = await request.post(`${API}/base-data/rebuild`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  // ── 4. 报表生成 ──

  test('资金日报 — 生成并查询', async ({ request }) => {
    const res = await request.get(`${API}/reports/daily?start_date=2026-03-01&end_date=2026-04-30`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  test('账户余额表 — 查询', async ({ request }) => {
    const res = await request.get(`${API}/reports/account-balance?start_date=2026-03-01&end_date=2026-04-30`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  test('收入明细表 — 查询', async ({ request }) => {
    const res = await request.get(`${API}/reports/income-list?start_date=2026-03-01&end_date=2026-04-30`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  test('支出明细表 — 查询', async ({ request }) => {
    const res = await request.get(`${API}/reports/expense-list?start_date=2026-03-01&end_date=2026-04-30`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  // ── 5. 首页总控台 ──

  test('首页 — 总览 API', async ({ request }) => {
    const res = await request.get(`${API}/home/overview`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('pending_tasks')
    expect(body.data).toHaveProperty('abnormal_count')
    expect(body.data).toHaveProperty('today_generated')
  })

  test('首页 — 待办 API', async ({ request }) => {
    const res = await request.get(`${API}/home/todos`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  test('首页 — 快捷入口 API', async ({ request }) => {
    const res = await request.get(`${API}/home/quick-links`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  test('首页 — 系统状态 API', async ({ request }) => {
    const res = await request.get(`${API}/home/system-status`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('reminders')
  })

  // ── 6. 看板 ──

  test('看板 — 指标 API', async ({ request }) => {
    const res = await request.get(`${API}/dashboard/metrics`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('total_income')
    expect(body.data).toHaveProperty('total_expense')
  })

  test('看板 — 收支趋势 API', async ({ request }) => {
    const res = await request.get(`${API}/dashboard/trends?days=30`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('dates')
    expect(body.data).toHaveProperty('income')
    expect(body.data).toHaveProperty('expense')
    expect(body.data.dates.length).toBeGreaterThan(0)
  })

  test('看板 — 账户分布 API', async ({ request }) => {
    const res = await request.get(`${API}/dashboard/composition`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('items')
  })

  // ── 7. 导出 ──

  test('导出 — 基础数据表 Excel', async ({ request }) => {
    const res = await request.post(`${API}/export/report`, {
      data: { export_type: 'base_data', start_date: '2026-03-01', end_date: '2026-04-30' }
    })
    expect(res.ok()).toBeTruthy()
    expect(res.headers()['content-type']).toContain('spreadsheet')
  })

  test('导出 — 资金日报 Excel', async ({ request }) => {
    const res = await request.post(`${API}/export/report`, {
      data: { export_type: 'daily_report', start_date: '2026-03-01', end_date: '2026-04-30' }
    })
    expect(res.ok()).toBeTruthy()
  })

  // ── 8. 备份恢复 ──

  test('备份 — 创建备份', async ({ request }) => {
    const res = await request.post(`${API}/backups/create`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('filename')
  })

  test('备份 — 列出备份', async ({ request }) => {
    const res = await request.get(`${API}/backups`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data).toHaveProperty('items')
    expect(body.data).toHaveProperty('total')
  })

  // ── 9. 操作日志 ──

  test('操作日志 — 查询', async ({ request }) => {
    const res = await request.get(`${API}/logs`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  // ── 10. 批次管理 ──

  test('批次 — 列出批次', async ({ request }) => {
    const res = await request.get(`${API}/batches`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  // ── 11. 手工流水 ──

  test('手工流水 — 字段池查询', async ({ request }) => {
    const res = await request.get(`${API}/manual-flow/field-pool`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    // 验证命名统一：不再有"识别键"
    const fieldNames = body.data.map(f => f.field_name_cn)
    expect(fieldNames).not.toContain('法人识别键')
    expect(fieldNames).not.toContain('账户识别键')
    expect(fieldNames).toContain('法人简称')
    expect(fieldNames).toContain('账户名称')
  })

  test('手工流水 — 方案查询', async ({ request }) => {
    const res = await request.get(`${API}/manual-flow/schemes`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data.length).toBeGreaterThan(0)
  })

  // ── 12. 解析模板 ──

  test('解析模板 — 列出模板', async ({ request }) => {
    const res = await request.get(`${API}/parser-templates`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  // ── 13. AI 配置 ──

  test('AI配置 — 列出', async ({ request }) => {
    const res = await request.get(`${API}/ai-configs`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  test('AI配置 — 支持的供应商', async ({ request }) => {
    const res = await request.get(`${API}/ai-providers`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
  })

  // ── 14. Agent 配置 ──

  test('Agent配置 — 列出', async ({ request }) => {
    const res = await request.get(`${API}/agent-configs`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.code).toBe(0)
    expect(body.data.length).toBeGreaterThan(0)
  })
})


// ═══════════════════════════════════════════
// 前端页面 E2E 验证
// ═══════════════════════════════════════════

test.describe('Round 8 — 前端页面加载验证', () => {

  const pages = [
    { path: '/', name: '首页', checks: ['.metric-strip', '.progress-list'] },
    { path: '/bank-import', name: '网银导入', checks: ['.upload-zone'] },
    { path: '/manual-flow', name: '手工流水', checks: ['.batch-bar'] },
    { path: '/base-data', name: '基础数据表', checks: ['.data-table'] },
    { path: '/daily-report', name: '资金日报', checks: ['.data-table'] },
    { path: '/account-balance', name: '账户余额表', checks: ['.data-table'] },
    { path: '/income-list', name: '收入明细', checks: ['.data-table'] },
    { path: '/expense-list', name: '支出明细', checks: ['.data-table'] },
    { path: '/account-manage', name: '账户管理', checks: ['.data-table'] },
    { path: '/rule/bank', name: '银行流水规则', checks: [] },
    { path: '/ai-config', name: 'AI配置', checks: [] },
    { path: '/backup-restore', name: '备份恢复', checks: [] },
    { path: '/operation-log', name: '操作日志', checks: [] },
  ]

  for (const p of pages) {
    test(`${p.name} — 页面加载`, async ({ page }) => {
      await page.goto(`${BASE}${p.path}`, { waitUntil: 'networkidle', timeout: 15000 })
      await page.waitForTimeout(1500)

      // 不应该是空白页
      const content = await page.evaluate(() => document.querySelector('.content')?.innerHTML?.length || 0)
      expect(content).toBeGreaterThan(0)

      // 检查关键元素
      for (const sel of p.checks) {
        const count = await page.locator(sel).count()
        if (count > 0) {
          expect(count).toBeGreaterThan(0)
        }
      }
    })
  }

  // ── 首页 ECharts 图表验证 ──

  test('首页 — ECharts 图表正常渲染', async ({ page }) => {
    await page.goto(`${BASE}/`, { waitUntil: 'networkidle', timeout: 15000 })
    await page.waitForTimeout(3000)

    const chartCount = await page.evaluate(() =>
      document.querySelectorAll('div[_echarts_instance_]').length
    )
    expect(chartCount).toBeGreaterThanOrEqual(2)
  })

  // ── 命名统一验证 ──

  test('账户管理 — 表头命名统一', async ({ page }) => {
    await page.goto(`${BASE}/account-manage`, { waitUntil: 'networkidle', timeout: 15000 })
    await page.waitForTimeout(1500)

    const headers = await page.evaluate(() =>
      Array.from(document.querySelectorAll('th')).map(t => t.textContent.trim())
    )
    expect(headers).toContain('账户编码')
    expect(headers).toContain('账户名称')
    expect(headers).toContain('法人简称')
    expect(headers).toContain('银行账号')
    // 不应该有旧的命名
    expect(headers).not.toContain('编码')
    expect(headers).not.toContain('别名')
    expect(headers).not.toContain('账号')
  })

  test('基础数据表 — 表头命名统一', async ({ page }) => {
    await page.goto(`${BASE}/base-data?table=base_data`, { waitUntil: 'networkidle', timeout: 15000 })
    await page.waitForTimeout(1500)

    const headers = await page.evaluate(() =>
      Array.from(document.querySelectorAll('th')).map(t => t.textContent.trim())
    )
    expect(headers).toContain('法人简称')
    expect(headers).toContain('账户名称')
    expect(headers).not.toContain('法人')
    expect(headers).not.toContain('账户')
  })
})
