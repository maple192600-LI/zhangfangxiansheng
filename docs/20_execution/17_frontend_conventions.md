# 17 · 前端开发规范

> 配合 [13_coding_conventions.md](../00_governance/13_coding_conventions.md)、[02_frontend_information_architecture.md](../10_product_design/02_frontend_information_architecture.md) 使用。

---

## §1 · 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 3 | 3.5+（Composition API） |
| 构建工具 | Vite | 8.x |
| UI 组件库 | Ant Design Vue | 4.x |
| 图表 | ECharts | 6.x |
| 状态管理 | Pinia | 3.x |
| 路由 | Vue Router | 4.x |
| HTTP | Axios | 1.x |

不引入第二套组件库。

---

## §2 · 目录结构

```
frontend/src/
├── views/          ← 页面（按功能模块命名，含 agent/ 子目录）
├── components/     ← 通用可复用组件
├── composables/    ← 组合式函数（use 开头）
├── stores/         ← Pinia store
├── api/            ← 接口请求封装（每个模块一个文件）
├── router/         ← 路由配置
├── styles/         ← 全局样式
└── utils/          ← 工具函数
```

---

## §3 · 页面组件约定

### §3.1 · 表格为主战场

首页和工作页面以表格为核心交互方式：
- 使用 Ant Design Vue 的 `<a-table>` 组件
- 支持筛选、排序、分页
- 导出按钮导出当前筛选结果

### §3.2 · 页面模板

```vue
<template>
  <div class="page-container">
    <!-- 页面标题 + 操作按钮 -->
    <div class="page-header">
      <h2>页面标题</h2>
      <div class="page-actions">
        <a-button @click="handleExport">导出</a-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="page-filters">
      <a-form layout="inline">
        <!-- 筛选条件 -->
      </a-form>
    </div>

    <!-- 数据表格 -->
    <a-table
      :columns="columns"
      :data-source="data"
      :loading="loading"
      :pagination="pagination"
      @change="handleTableChange"
    />
  </div>
</template>
```

---

## §4 · API 调用约定

### §4.1 · 封装格式

```javascript
// src/api/bankImport.js
import request from './request'

export function uploadBankFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/bank/import', formData)
}

export function getBatches(params) {
  return request.get('/api/bank/batches', { params })
}
```

### §4.2 · 响应处理

统一处理 `code !== 0` 的情况：

```javascript
// src/api/request.js（拦截器）
service.interceptors.response.use(
  response => {
    const { code, message, data } = response.data
    if (code !== 0) {
      message.error(message)
      return Promise.reject(new Error(message))
    }
    return data
  }
)
```

### §4.3 · 禁止事项

- 禁止在组件中直接写 axios 调用（必须通过 `src/api/` 封装）
- 禁止在前端暴露 API 密钥或 token 到 URL 参数中

---

## §5 · 状态管理

### §5.1 · 什么时候用 Pinia

- 跨页面共享的状态（用户信息、Agent 配置）
- 需要持久化的状态

### §5.2 · 什么时候用 ref/reactive

- 页面内部状态
- 表单数据
- 筛选条件

### §5.3 · 禁止事项

- 不在 Pinia store 中存 API 原始响应（存处理后的数据）
- 不在多个 store 中重复存同一份数据

---

## §6 · 视觉风格

- 稳重复克制的暖色系
- 柔和浅暖中性背景 + 低饱和稳重绿色主强调色
- 砂金/暖棕辅助色
- 详细规范见 `references/style_and_interaction/style_theme_spec.md`

---

## §7 · 禁止事项

- 不暴露 JSON 编辑器、正则表达式、字段映射配置给用户（§C9）
- 不使用英文错误提示
- 不引入未经批准的第三方组件库
- 不在模板中使用 `v-html`（防 XSS）
- 不使用 `console.log`（用 `console.debug` 或移除）

---

**版本**
- v1.0 · 2026-05-02 · 首次发布
