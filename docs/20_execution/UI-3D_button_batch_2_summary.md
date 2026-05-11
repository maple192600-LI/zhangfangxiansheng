# UI-3D-2: Complete Native Button Migration to Naive UI

## Summary

清除 `frontend/src` 中所有剩余原生 `<button>` 标签，全部替换为 Naive UI `NButton` 组件。

## Scope

| Category | Files | Button Count | Migration Strategy |
|----------|-------|-------------|-------------------|
| Tab buttons | AccountManage (4), SystemMaintenance (2) | 6 | `NButton quaternary` + custom class |
| Dropdown menu items | AccountManage (12) | 12 | `NButton quaternary` + custom class |
| Agent chat | ChatPanel | 12 | `NButton quaternary` + custom class |
| Agent file panel | FilePanel | 4 | `NButton quaternary` + custom class |
| Agent memory | MemoryPanel | 5 | `NButton quaternary` + custom class |
| Agent sessions | SessionsPanel | 2 | `NButton quaternary` + custom class |
| Agent settings | SettingsPanel | 6 | `NButton quaternary` + custom class |
| Agent skills | SkillsPanel | 6 | `NButton quaternary` + custom class |
| Agent detail tabs | AgentDetail | 1 | `NButton quaternary` + custom class |
| AIConfig sidebar | AIConfig | 4 | `NButton quaternary` + custom class |
| MainLayout | MainLayout | 5 | `NButton quaternary` + custom class |
| Exception filter pills | ExceptionCenter | 3 | `NButton quaternary` + custom class |
| Modal close | ReportTemplate | 1 | `NButton quaternary` + custom class |
| **Total** | **13 files** | **~67** | |

## Migration Rules

1. All native `<button>` → `<NButton quaternary>` (minimal base styling)
2. Original CSS class preserved via `class` prop for custom styling override
3. Active/toggle state preserved via `:class="{ active: ... }"` binding
4. Event handlers (`@click`, `@click.stop`) unchanged
5. Disabled state preserved via `:disabled` prop
6. No interface changes, no business logic changes, no refactoring

## Files Changed (13)

- `frontend/src/layouts/MainLayout.vue` — 3 user-btn + 2 right-tab
- `frontend/src/views/AgentDetail.vue` — 1 agent-tab-btn (+ added NButton import)
- `frontend/src/views/AIConfig.vue` — 4 sidebar buttons (btn-add, btn-add-inline, btn-log, key-toggle)
- `frontend/src/views/AccountManage.vue` — 4 tab-btn + 12 dropdown-menu items
- `frontend/src/views/ExceptionCenter.vue` — 3 filter pills
- `frontend/src/views/ReportTemplate.vue` — 1 modal-close
- `frontend/src/views/SystemMaintenance.vue` — 2 tab-btn
- `frontend/src/views/agent/ChatPanel.vue` — 12 buttons (+ added NButton import)
- `frontend/src/views/agent/FilePanel.vue` — 4 buttons (+ added NButton import)
- `frontend/src/views/agent/MemoryPanel.vue` — 5 buttons (+ added NButton import)
- `frontend/src/views/agent/SessionsPanel.vue` — 2 buttons (+ added NButton import)
- `frontend/src/views/agent/SettingsPanel.vue` — 6 buttons (+ added NButton to existing import)
- `frontend/src/views/agent/SkillsPanel.vue` — 6 buttons (+ added NButton import)

## Verification

- `npm run build`: PASS (built in 574ms)
- `<button` grep in `*.vue`: 0 matches (zero residue)
- `</button>` grep in `*.vue`: 0 matches (zero residue)
- `ant-design` import grep: 0 matches (no antd residue)

## NButton Import Additions

6 files needed NButton import added:
- `AgentDetail.vue` — `import { NButton } from 'naive-ui'`
- `ChatPanel.vue` — `import { NButton } from 'naive-ui'`
- `FilePanel.vue` — `import { NButton } from 'naive-ui'`
- `MemoryPanel.vue` — `import { NButton } from 'naive-ui'`
- `SessionsPanel.vue` — `import { NButton } from 'naive-ui'`
- `SkillsPanel.vue` — `import { NButton } from 'naive-ui'`
- `SettingsPanel.vue` — added `NButton` to existing `NSelect` import

7 files already had NButton imported:
- `MainLayout.vue`, `AIConfig.vue`, `AccountManage.vue`, `ExceptionCenter.vue`, `ReportTemplate.vue`, `SystemMaintenance.vue`, `OperationLog.vue` (and others from Batch 1)
