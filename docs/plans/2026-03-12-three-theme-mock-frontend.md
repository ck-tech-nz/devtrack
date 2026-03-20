# Three-Theme Mock Frontend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build three independent Nuxt 3 mock frontend apps (Crystal, Matrix, Warm) for a post-loan management platform, each with 30+ pages of hardcoded mock data in Chinese.

**Architecture:** Three fully independent Nuxt 3 + Nuxt UI + Tailwind CSS apps under `theme-a/`, `theme-b/`, `theme-c/`. Each has its own package.json, layouts, components, and mock data. No code sharing. All data is hardcoded — no API calls.

**Tech Stack:** Nuxt 3, Nuxt UI v2, Tailwind CSS, ECharts (via vue-echarts), TypeScript

**Spec:** `docs/superpowers/specs/2026-03-12-three-theme-mock-frontend-design.md`

**Old frontend reference:** `../frontend-old/src/` (for page structure, business logic, TypeScript interfaces)

---

## Important Notes for All Agents

1. **Language**: All UI text must be in Simplified Chinese (zh-CN). Use realistic Chinese names, addresses, amounts.
2. **ECharts + SSR**: Wrap all chart components in `<ClientOnly>`. Or set `ssr: false` in nuxt.config.
3. **Login**: The login page is purely visual. The "Login" button navigates to `/app/dashboard`.
4. **Nuxt UI v2**: Install `@nuxt/ui@^2` (stable v2.x). Do NOT use v3/alpha.
5. **Nuxt CLI**: Use `npx nuxi@3` (not `@latest`) to ensure Nuxt 3 scaffolding.
6. **Mock data**: Reference TypeScript interfaces from `../frontend-old/src/api/*.ts` for field definitions. Note that `CallRecord` and `CallStats` are defined in `logs.ts` in the old frontend. All mock data should be in dedicated `data/` directories.
7. **Fonts**: Load via Google Fonts. CJK text uses system font fallback (PingFang SC, Microsoft YaHei). Configure in Tailwind.
8. **Dev server ports**: Theme A → port 3000, Theme B → port 3001, Theme C → port 3002. Set via `devServer: { port: 300X }` in nuxt.config.ts.
9. **Dialog components**: Every dialog listed in spec Section 5.1 must have a dedicated `.vue` component file. Do not implement dialogs as inline template code within pages.
10. **Mock data pre-step**: Agent A creates all mock data first. Agents B and C copy from `theme-a/data/` once Agent A's Task 2 is complete. This ensures identical data across all three themes for fair comparison.

---

## Chunk 1: Theme A — Crystal (简洁明快)

**Agent workspace:** `frontend/theme-a/`
**Design identity:** Minimal, clean, Apple/Linear/Stripe inspired. White base, single blue/violet accent, generous whitespace, icon-only collapsible sidebar, side-drawer dialogs.

### Task 1: Scaffold Nuxt 3 App

**Files:**
- Create: `theme-a/package.json`
- Create: `theme-a/nuxt.config.ts`
- Create: `theme-a/app.vue`
- Create: `theme-a/tailwind.config.ts`
- Create: `theme-a/tsconfig.json`

- [ ] **Step 1: Initialize Nuxt 3 project**

```bash
cd /Users/ck/Git/matrix/postloan/frontend
npx nuxi@3 init theme-a --packageManager npm
cd theme-a
```

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/ck/Git/matrix/postloan/frontend/theme-a
npm install @nuxt/ui@^2 echarts vue-echarts
```

- [ ] **Step 3: Configure nuxt.config.ts**

```typescript
export default defineNuxtConfig({
  modules: ['@nuxt/ui'],
  ssr: false,
  devServer: { port: 3000 },
  app: {
    head: {
      title: '矩阵智能·贷后智能体',
      link: [
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap' }
      ]
    }
  },
  ui: {
    global: true
  },
  colorMode: {
    preference: 'light'
  }
})
```

- [ ] **Step 4: Configure Tailwind**

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'sans-serif']
      },
      colors: {
        crystal: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95'
        }
      }
    }
  }
} satisfies Partial<Config>
```

- [ ] **Step 5: Verify dev server starts**

```bash
cd /Users/ck/Git/matrix/postloan/frontend/theme-a
npm run dev
```
Expected: Dev server starts on http://localhost:3000

- [ ] **Step 6: Commit**

```bash
git add theme-a/
git commit -m "feat(theme-a): scaffold Crystal Nuxt 3 app"
```

### Task 2: Create Mock Data

**Files:**
- Create: `theme-a/data/cases.ts`
- Create: `theme-a/data/casePackages.ts`
- Create: `theme-a/data/batches.ts`
- Create: `theme-a/data/strategies.ts`
- Create: `theme-a/data/dashboard.ts`
- Create: `theme-a/data/disposalRecords.ts`
- Create: `theme-a/data/users.ts`
- Create: `theme-a/data/sms.ts`
- Create: `theme-a/data/voices.ts`
- Create: `theme-a/data/scheduledTasks.ts`
- Create: `theme-a/data/executionBatches.ts`
- Create: `theme-a/data/logs.ts`
- Create: `theme-a/data/callRecords.ts`
- Create: `theme-a/data/types.ts`

- [ ] **Step 1: Create types.ts with all shared interfaces**

Copy all TypeScript interfaces from the old frontend's `src/api/*.ts` files into `data/types.ts`. Include: `Case`, `CollectionRecord`, `CasePackage`, `AnalysisBatch`, `AnalysisBatchItem`, `Strategy`, `StrategyDetail`, `Workflow`, `WorkflowAction`, `WorkflowCondition`, `WorkflowConditions`, `ExecutionBatch`, `ExecutionLog`, `ExecutionBatchItem`, `ActionType`, `Tag`, `DashboardStats`, `DashboardTrends`, `DailyCaseTrend`, `StatusDistribution`, `PriorityDistribution`, `AIAnalysisDistribution`, `AIAnalysisHistory`, `AiTagsStats`, `AiTagDimensionItem`, `DisposalRecord`, `DisposalRecordStats`, `CaseWithDisposal`, `CallStats`, `CallRecord`, `SmsSignature`, `SmsTemplate`, `SmsTemplateVariable`, `Voice`, `User`, `Role`, `Permission`, `Organization`, `ScheduledTask`, `ToolCallLog`, `OperationLog`, `ServiceHealth`, `PaginatedResponse`, `WorkflowStep`.

- [ ] **Step 2: Create mock data files**

Each file exports arrays/objects of mock data using the interfaces. Key requirements:
- **cases.ts**: 50+ cases with realistic Chinese names (张三, 李四, 王五...), case IDs like `CASE-2026-001`, varied statuses (待处理/处理中/已解决/已关闭), priorities (高/中/低), realistic RMB amounts (50,000 - 2,000,000), overdue days (30-365), AI tags with risk_level/urgency/willingness_level, ML predictions with repayment_probability. Also export 5-10 CollectionRecord entries per case.
- **casePackages.ts**: 8-10 packages with types (通用/电话催收/诉讼/调解...), import statuses, realistic case counts and amounts.
- **batches.ts**: 5-6 analysis batches in states (pending/running/paused/completed/failed), with batch items.
- **strategies.ts**: 4-5 strategies with full workflows (conditions on overdue_days, amount, AI tags + actions like send_sms, make_call). Also export ActionType[] (5-6 items) and Tag[] (15-20 items) arrays.
- **executionBatches.ts**: 3-4 ExecutionBatch records in varied states + 10 ExecutionLog entries + 8 ExecutionBatchItem entries.
- **dashboard.ts**: DashboardStats, 30-day DailyCaseTrend[], StatusDistribution[], PriorityDistribution[], AIAnalysisDistribution[], AiTagsStats with 6 dimensions, top 5 packages, 10 recent AIAnalysisHistory records.
- **disposalRecords.ts**: 30 records with varied statuses and methods, plus DisposalRecordStats.
- **users.ts**: 10 users, 4 roles (超级管理员/管理员/操作员/查看员) with permissions, 3 organizations.
- **sms.ts**: 3 signatures, 5 templates with realistic SMS content for debt collection.
- **voices.ts**: 3 voice configs.
- **scheduledTasks.ts**: 4-5 tasks with cron expressions + execution history records (HistoryResponse with 3-5 past batch runs per task).
- **logs.ts**: 15 ToolCallLog entries, 10 OperationLog entries, ServiceHealth data.
- **callRecords.ts**: 20 call records with CallStats (emotion/compliance distribution).

- [ ] **Step 3: Commit**

```bash
git add theme-a/data/
git commit -m "feat(theme-a): add comprehensive mock data"
```

### Task 3: Layout and Navigation

**Files:**
- Create: `theme-a/layouts/default.vue` — Main app layout with collapsible icon sidebar + content area
- Create: `theme-a/layouts/auth.vue` — Minimal layout for login page
- Create: `theme-a/layouts/landing.vue` — Layout for public landing page
- Create: `theme-a/components/AppSidebar.vue` — Icon-only expandable sidebar
- Create: `theme-a/components/AppHeader.vue` — Top header with breadcrumb + user menu
- Create: `theme-a/composables/useNavigation.ts` — Menu structure data

- [ ] **Step 1: Create navigation composable**

Define the menu structure per the spec's navigation hierarchy:
- 平台概览 (Dashboard icon)
- 案件管理 (案件包/全部案件/处置记录)
- 智能分析 (分析批次/通话记录)
- 策略中心 (策略管理/执行批次/动作类型/标签管理)
- 消息管理 (短信签名/短信模板/语音管理)
- 系统管理 (用户/角色/组织/定时任务/服务监控/工具调用日志)

Each menu item has: icon, label, route, children (optional).

- [ ] **Step 2: Create AppSidebar.vue**

Crystal style:
- 64px wide collapsed (icons only), 240px expanded
- Hover to expand or click toggle button
- White background, subtle gray border right
- Active item: violet/blue accent background
- Smooth transition animations
- Bottom: user avatar + settings link

- [ ] **Step 3: Create AppHeader.vue**

Crystal style:
- Breadcrumb navigation (auto-generated from route)
- Right side: notification bell (static), user avatar dropdown (Profile, About, Logout)
- Clean, minimal, no tabs

- [ ] **Step 4: Create default.vue layout**

Compose sidebar + header + `<slot />` for page content. Use flex layout. Content area has light gray background (#F9FAFB) with padding.

- [ ] **Step 5: Create auth.vue and landing.vue layouts**

auth.vue: Centered content, no sidebar/header.
landing.vue: Custom navigation bar for public pages.

- [ ] **Step 6: Create app.vue**

```vue
<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
```

- [ ] **Step 7: Verify layout renders**

```bash
cd /Users/ck/Git/matrix/postloan/frontend/theme-a && npm run dev
```
Navigate to http://localhost:3000/app/dashboard — should see sidebar + header + empty content area.

- [ ] **Step 8: Commit**

```bash
git add theme-a/layouts/ theme-a/components/ theme-a/composables/ theme-a/app.vue
git commit -m "feat(theme-a): add Crystal layout with collapsible icon sidebar"
```

### Task 4: Login & Landing Pages

**Files:**
- Create: `theme-a/pages/index.vue` — Landing page
- Create: `theme-a/pages/login.vue` — Login page

- [ ] **Step 1: Create login page**

Crystal style: Centered card on subtle gradient background (white → light violet). Card contains:
- App logo + title "矩阵智能·贷后智能体"
- Username input (placeholder: 请输入用户名)
- Password input (placeholder: 请输入密码)
- Captcha row: input + captcha image placeholder
- "登录" button (violet accent, full width)
- Clicking "登录" navigates to `/app/dashboard`

- [ ] **Step 2: Create landing page**

Crystal style: Clean product landing with:
- Hero section: headline + subtitle + "开始使用" CTA button → `/login`
- 3-4 feature cards (AI智能分析, 策略自动化, 数据看板, 批量处理)
- Minimal footer

- [ ] **Step 3: Verify both pages render and navigation works**
- [ ] **Step 4: Commit**

```bash
git add theme-a/pages/
git commit -m "feat(theme-a): add login and landing pages"
```

### Task 5: Dashboard Page

**Files:**
- Create: `theme-a/pages/app/dashboard.vue`
- Create: `theme-a/components/dashboard/StatCard.vue`
- Create: `theme-a/components/charts/LineChart.vue`
- Create: `theme-a/components/charts/PieChart.vue`
- Create: `theme-a/components/charts/BarChart.vue`

- [ ] **Step 1: Create chart wrapper components**

Each chart component wraps vue-echarts inside `<ClientOnly>`. Accept props for data/options. Crystal style: muted colors, clean axes, no decorative elements.

- [ ] **Step 2: Create StatCard component**

Crystal style: White card, subtle shadow, large number, small label below, optional trend indicator (↑/↓ with green/red).

- [ ] **Step 3: Create dashboard page**

Layout:
- Row 1: 4 StatCards (总案件数, 总金额, 待处理, 高优先级)
- Row 2: LineChart (30日案件趋势) + PieChart (状态分布)
- Row 3: BarChart (优先级分布) + AI分析用户画像 (tag dimension stats as horizontal bars)
- Row 4: Recent AI analyses list (simple table)

Import mock data from `data/dashboard.ts`.

- [ ] **Step 4: Verify dashboard renders with charts**
- [ ] **Step 5: Commit**

```bash
git add theme-a/pages/app/dashboard.vue theme-a/components/dashboard/ theme-a/components/charts/
git commit -m "feat(theme-a): add dashboard with stat cards and charts"
```

### Task 6: Case Management Pages

**Files:**
- Create: `theme-a/pages/app/cases.vue`
- Create: `theme-a/components/cases/CaseDetailDrawer.vue`
- Create: `theme-a/components/cases/CreatePackageDialog.vue`
- Create: `theme-a/pages/app/case-packages/index.vue`
- Create: `theme-a/pages/app/case-packages/[id].vue`
- Create: `theme-a/pages/app/case-packages/import.vue`
- Create: `theme-a/pages/app/disposal-records.vue`

- [ ] **Step 1: Create case list page**

Crystal style:
- Stat summary row: 4 mini cards (total, pending, in-progress, resolved)
- Collapsible filter bar (search, status dropdown, priority dropdown, date range)
- Clean table with columns: 案件ID, 借款人, 逾期金额, 逾期天数, 状态, 优先级, AI分析, 操作
- Status/priority as subtle colored badges
- Pagination at bottom
- Click row → open CaseDetailDrawer

- [ ] **Step 2: Create CaseDetailDrawer**

Side drawer (right, 600px wide) with tabs:
- 基本信息: Key-value pairs (borrower info, amounts, dates)
- AI分析: Risk level, urgency, willingness tags displayed as cards, ML prediction probability bar
- 处置记录: Timeline of CollectionRecord entries

- [ ] **Step 3: Create case package list page**

Table with: 编号, 名称, 类型, 案件数, 总金额, 导入状态, 创建时间, 操作
"新建案件包" button (opens simple form dialog)

- [ ] **Step 4: Create case package detail page**

Route: `/app/case-packages/:id`
- Package info header (name, type, status, stats)
- Table of cases in this package
- Import status section

- [ ] **Step 5: Create import workflow page**

3-step stepper:
1. Upload: File drop zone + file input
2. Column mapping: Source columns → target fields table (show mock smart-match results with confidence %)
3. Confirm: Summary stats + "开始导入" button

All steps display mock data. Stepper allows forward/backward navigation.

- [ ] **Step 6: Create disposal records page**

- Stat cards row: 总记录, 已处置, 处理中, 待处置, 处置率
- Filterable table: 案件ID, 借款人, 逾期金额, 处置方式, 操作员, 状态, 处置时间

- [ ] **Step 7: Verify all case pages render and navigation works**
- [ ] **Step 8: Commit**

```bash
git add theme-a/pages/app/cases.vue theme-a/pages/app/case-packages/ theme-a/pages/app/disposal-records.vue theme-a/components/cases/
git commit -m "feat(theme-a): add case management, packages, import, disposal records"
```

### Task 7: Batch & Analysis Pages

**Files:**
- Create: `theme-a/pages/app/batches.vue`
- Create: `theme-a/components/batches/BatchDetailDrawer.vue`
- Create: `theme-a/pages/app/call-records.vue`

- [ ] **Step 1: Create batch list page**

Table: 批次号, 案件包, 工作流类型, 状态, 进度 (progress bar), 成功/失败/跳过, 创建时间
Click row → BatchDetailDrawer

- [ ] **Step 2: Create BatchDetailDrawer**

- Batch summary (code, status, progress bar, timestamps)
- Workflow steps indicator (WorkflowStep[])
- Item list table: 序号, 案件ID, 借款人, 状态, 耗时, 错误信息

- [ ] **Step 3: Create call records page**

- Stats panel: 6 cards (总通话, 已接通, 接通率, 平均时长, Token消耗, 通话费用)
- Emotion distribution mini chart + Compliance distribution mini chart
- Table: 通话ID, 案件ID, 债务人, 电话, 状态, 时长, 情绪, 合规, 创建时间

- [ ] **Step 4: Verify pages render**
- [ ] **Step 5: Commit**

```bash
git add theme-a/pages/app/batches.vue theme-a/pages/app/call-records.vue theme-a/components/batches/
git commit -m "feat(theme-a): add batch list, batch detail, call records"
```

### Task 8: Strategy Pages

**Files:**
- Create: `theme-a/pages/app/strategies.vue`
- Create: `theme-a/components/strategies/StrategyDetailDrawer.vue`
- Create: `theme-a/components/strategies/StrategyFormDrawer.vue`
- Create: `theme-a/pages/app/execution-batches.vue`
- Create: `theme-a/components/strategies/ExecutionBatchDetailDrawer.vue`
- Create: `theme-a/components/strategies/CreateExecutionBatchDrawer.vue`
- Create: `theme-a/pages/app/action-types.vue`
- Create: `theme-a/components/strategies/ActionTypeDialog.vue`
- Create: `theme-a/pages/app/tags.vue`
- Create: `theme-a/components/strategies/TagDialog.vue`

- [ ] **Step 1: Create strategy list page**

Clean card layout, each card shows: strategy name, code, active/inactive badge, workflow count, action types summary, condition summary preview. Buttons: 查看详情, 编辑.

- [ ] **Step 2: Create StrategyDetailDrawer**

- Strategy info (name, code, description, status)
- Workflows list: Each workflow shows conditions (field/operator/value) and actions (type + params) in a clean card layout

- [ ] **Step 3: Create StrategyFormDrawer**

Form with:
- Name, code, description, active toggle
- Workflow builder: Add/remove workflows, each with condition rows (field dropdown + operator dropdown + value input) and action rows (type dropdown + params)

- [ ] **Step 4: Create execution batch list page**

Table: 批次号, 策略, 分析批次, 状态, 进度, 成功/失败/无匹配, 创建时间
"新建执行批次" button → CreateExecutionBatchDrawer (select strategy dropdown + select analysis batch dropdown + "创建" button)
Click row → ExecutionBatchDetailDrawer

- [ ] **Step 5: Create ExecutionBatchDetailDrawer**

- Batch info + progress
- Execution log table: 案件ID, 借款人, 匹配工作流, 状态, 执行动作, 错误信息

- [ ] **Step 6: Create action types page + ActionTypeDialog**

Table: 编码, 名称, 分类, N8N Webhook, 状态, 操作
"新建" button opens ActionTypeDialog (form: code, name, description, category dropdown, webhook URL, params schema, active toggle)

- [ ] **Step 7: Create tags page + TagDialog**

Table: 编码, 名称, 标签类型 (规则/AI), 数据类型, 选项, 排序, 状态, 操作
"新建" button opens TagDialog (form: code, name, tag_type radio, data_type dropdown, options array input for enum, rule_expression textarea for rule type, description, active toggle)

- [ ] **Step 8: Verify all strategy pages**
- [ ] **Step 9: Commit**

```bash
git add theme-a/pages/app/strategies.vue theme-a/pages/app/execution-batches.vue theme-a/pages/app/action-types.vue theme-a/pages/app/tags.vue theme-a/components/strategies/
git commit -m "feat(theme-a): add strategy management, execution batches, action types, tags"
```

### Task 9: Messaging Pages

**Files:**
- Create: `theme-a/pages/app/sms-signatures.vue`
- Create: `theme-a/pages/app/sms-templates.vue`
- Create: `theme-a/components/sms/SmsTemplateDialog.vue`
- Create: `theme-a/pages/app/voices.vue`

- [ ] **Step 1: Create SMS signature list page**

Table: 签名内容, 服务商, 状态, 默认签名, 创建人, 创建时间
"新建" button opens form dialog

- [ ] **Step 2: Create SMS template list page**

Table: 编码, 名称, 签名, 分类, 使用次数, 状态, 操作
Click → SmsTemplateDialog

- [ ] **Step 3: Create SmsTemplateDialog**

Drawer with: code, name, signature select, category, content textarea with variable insertion hints, preview panel showing rendered content

- [ ] **Step 4: Create voice management page**

Table: 名称, 语音ID, 类型, 状态, 语言, 性别, 创建时间
"新建" button opens form dialog

- [ ] **Step 5: Commit**

```bash
git add theme-a/pages/app/sms-signatures.vue theme-a/pages/app/sms-templates.vue theme-a/pages/app/voices.vue theme-a/components/sms/
git commit -m "feat(theme-a): add SMS signatures, templates, voice management"
```

### Task 10: Admin Pages

**Files:**
- Create: `theme-a/pages/app/users.vue`
- Create: `theme-a/components/admin/UserDialog.vue`
- Create: `theme-a/pages/app/roles.vue`
- Create: `theme-a/components/admin/RoleDialog.vue`
- Create: `theme-a/pages/app/organizations.vue`
- Create: `theme-a/components/admin/OrganizationDialog.vue`

- [ ] **Step 1: Create user list page + UserDialog**

Table: 用户名, 邮箱, 手机, 组织, 角色, 状态, 最后登录
"新建用户" button → UserDialog (form: username, email, phone, password, organization select, role multiselect, active toggle). Same dialog for edit (pre-filled).

- [ ] **Step 2: Create role list page + RoleDialog**

Table: 名称, 描述, 类型 (平台/组织), 用户数, 权限数, 创建时间
"新建角色" → RoleDialog (form: name, description, role_type radio, permission tree checkbox selector)

- [ ] **Step 3: Create organization list page + OrganizationDialog**

Table: 名称, 编码, 类型, 状态, 联系人, 用户数, 创建时间
"新建组织" → OrganizationDialog (form: name, code, org_type dropdown, status, contact_person, contact_phone, description)

- [ ] **Step 4: Commit**

```bash
git add theme-a/pages/app/users.vue theme-a/pages/app/roles.vue theme-a/pages/app/organizations.vue
git commit -m "feat(theme-a): add user, role, organization management"
```

### Task 11: System Pages

**Files:**
- Create: `theme-a/pages/app/scheduled-tasks.vue`
- Create: `theme-a/components/system/CronEditor.vue`
- Create: `theme-a/components/system/TaskHistoryDrawer.vue`
- Create: `theme-a/pages/app/service-monitor.vue`
- Create: `theme-a/pages/app/tool-call-logs.vue`

- [ ] **Step 1: Create scheduled tasks page**

Table: 名称, Cron表达式, 工作流类型, 策略, 状态, 运行次数, 上次运行, 下次运行, 操作
"新建" → dialog with CronEditor component
"历史" → TaskHistoryDrawer

- [ ] **Step 2: Create CronEditor component**

Visual cron builder: dropdowns for minute, hour, day, month, weekday with preview of next 5 run times. Also shows cron expression string.

- [ ] **Step 3: Create service monitor page**

Card grid showing service health:
- Each card: service name, status indicator (green/yellow/red dot), latency, URL
- Services: Django Backend, N8N Workflow, Database, Redis, Celery

- [ ] **Step 4: Create tool call logs page**

Table: 日志ID, 工具名称, 分类, 请求URL, 状态, 耗时, 创建时间
Click row → expandable detail with request/response data

- [ ] **Step 5: Commit**

```bash
git add theme-a/pages/app/scheduled-tasks.vue theme-a/pages/app/service-monitor.vue theme-a/pages/app/tool-call-logs.vue theme-a/components/system/
git commit -m "feat(theme-a): add scheduled tasks, service monitor, tool call logs"
```

### Task 12: Remaining Pages

**Files:**
- Create: `theme-a/pages/app/profile.vue`
- Create: `theme-a/pages/app/roadmap.vue`
- Create: `theme-a/pages/app/about.vue`
- Create: `theme-a/pages/app/forbidden.vue`
- Create: `theme-a/pages/404.vue`

- [ ] **Step 1: Create profile page**

User info card: avatar placeholder, username, email, phone, organization, roles. "编辑" button (non-functional in mock).

- [ ] **Step 2: Create roadmap page**

Timeline-style roadmap with 4-5 milestones:
- Q1 2026: 基础平台搭建
- Q2 2026: AI分析引擎上线
- Q3 2026: 策略自动化执行
- Q4 2026: 智能语音外呼集成

- [ ] **Step 3: Create about page**

App info: name, version (1.0.0), description, tech stack, team credits.

- [ ] **Step 4: Create error pages**

`forbidden.vue`: 403 illustration + "您没有权限访问此页面" + back button.
`404.vue`: 404 illustration + "页面未找到" + back to home button.

- [ ] **Step 5: Commit**

```bash
git add theme-a/pages/app/profile.vue theme-a/pages/app/roadmap.vue theme-a/pages/app/about.vue theme-a/pages/app/forbidden.vue theme-a/pages/404.vue
git commit -m "feat(theme-a): add profile, roadmap, about, and error pages"
```

### Task 13: Polish & Final Verification

- [ ] **Step 1: Verify all sidebar links navigate correctly**

Click through every menu item and verify the page loads.

- [ ] **Step 2: Verify all dialogs/drawers open and close**

Test: case detail, strategy detail/edit, batch detail, execution batch detail, SMS template, cron editor, task history, all create/edit dialogs.

- [ ] **Step 3: Verify all charts render**

Dashboard charts, call record stats charts, disposal stats.

- [ ] **Step 4: Visual consistency check**

Ensure Crystal design language is consistent: whitespace, accent colors, typography, card shadows, border radius.

- [ ] **Step 5: Final commit**

```bash
git add theme-a/
git commit -m "feat(theme-a): Crystal theme polish and final adjustments"
```

---

## Chunk 2: Theme B — Matrix (专业科技感)

**Agent workspace:** `frontend/theme-b/`
**Design identity:** Dark mode, data-dense, Vercel/Datadog/Bloomberg inspired. #0A0A0A base, neon accents (cyan/green/purple), glassmorphism, monospace numbers, dense tables, command palette, multi-panel layouts.

### Task 14: Scaffold Nuxt 3 App

Same as Task 1 but in `theme-b/` directory.

- [ ] **Step 1: Initialize Nuxt 3 project**

```bash
cd /Users/ck/Git/matrix/postloan/frontend
npx nuxi@3 init theme-b --packageManager npm
cd theme-b
npm install @nuxt/ui@^2 echarts vue-echarts vue-sparkline
```

- [ ] **Step 2: Configure nuxt.config.ts**

Same base config but with:
```typescript
devServer: { port: 3001 },
colorMode: {
  preference: 'dark'
}
```

- [ ] **Step 3: Configure Tailwind for dark Matrix theme**

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      colors: {
        matrix: {
          bg: '#0A0A0A',
          surface: '#141414',
          border: '#262626',
          cyan: '#00D4FF',
          green: '#00FF88',
          purple: '#A855F7',
          amber: '#FBBF24'
        }
      }
    }
  }
} satisfies Partial<Config>
```

Add Google Fonts in nuxt.config.ts head:
```typescript
link: [
  { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap' }
]
```

- [ ] **Step 4: Verify dark dev server**
- [ ] **Step 5: Commit**

```bash
git add theme-b/
git commit -m "feat(theme-b): scaffold Matrix dark Nuxt 3 app"
```

### Task 15: Create Mock Data

Same data as Task 2 but in `theme-b/data/`. **Copy the exact same mock data** to ensure fair comparison.

- [ ] **Step 1: Copy types and mock data from theme-a**

```bash
cp -r /Users/ck/Git/matrix/postloan/frontend/theme-a/data/ /Users/ck/Git/matrix/postloan/frontend/theme-b/data/
```

- [ ] **Step 2: Commit**

```bash
git add theme-b/data/
git commit -m "feat(theme-b): add mock data"
```

### Task 16: Layout and Navigation (Matrix Style)

**Files:**
- Create: `theme-b/layouts/default.vue`
- Create: `theme-b/layouts/auth.vue`
- Create: `theme-b/layouts/landing.vue`
- Create: `theme-b/components/AppSidebar.vue`
- Create: `theme-b/components/AppHeader.vue`
- Create: `theme-b/components/CommandPalette.vue`
- Create: `theme-b/composables/useNavigation.ts`

- [ ] **Step 1: Create navigation composable**

Same menu structure as Crystal but with added status indicators per section.

- [ ] **Step 2: Create AppSidebar.vue**

Matrix style:
- 260px fixed width, dark (#141414) with subtle border
- Grouped sections with section headers in muted text
- Active item: left border accent (cyan) + subtle glow
- Status indicators: colored dots next to items (green=healthy, yellow=warning)
- Compact spacing, small text
- Bottom: system status indicator + user info

- [ ] **Step 3: Create AppHeader.vue**

Matrix style:
- Dark header, breadcrumb left
- Right: Command palette trigger button (⌘K), notification count badge, user dropdown
- Subtle bottom border glow

- [ ] **Step 4: Create CommandPalette.vue**

Nuxt UI `UCommandPalette` with hardcoded search results:
- Recent pages
- Quick actions (查看仪表板, 新建案件包, etc.)
- Opens with Cmd+K keyboard shortcut

- [ ] **Step 5: Create layouts**

default.vue: Dark background, sidebar + header + content.
auth.vue: Full-screen dark with animated grid/particle background.
landing.vue: Dark landing page layout.

- [ ] **Step 6: Verify layout renders**
- [ ] **Step 7: Commit**

```bash
git add theme-b/layouts/ theme-b/components/ theme-b/composables/
git commit -m "feat(theme-b): add Matrix dark layout with command palette"
```

### Task 17: Login & Landing Pages (Matrix Style)

- [ ] **Step 1: Create login page**

Matrix style: Full-screen #0A0A0A background with subtle animated grid pattern (CSS only). Centered glassmorphism card (backdrop-blur, semi-transparent border). Neon accent on focus states. "矩阵智能" logo in cyan glow.

- [ ] **Step 2: Create landing page**

Dark, dramatic landing: large hero text with gradient, animated stat counters, feature cards with glassmorphism, dark-mode CTA buttons with glow effects.

- [ ] **Step 3: Commit**

```bash
git add theme-b/pages/
git commit -m "feat(theme-b): add Matrix login and landing pages"
```

### Task 18: Dashboard (Matrix Style)

- [ ] **Step 1: Create chart components**

Matrix style charts: dark backgrounds, neon-colored lines/bars, glow effects on data points, animated counters. Include additional chart types: RadarChart, HeatmapChart.

- [ ] **Step 2: Create dashboard page**

Dense layout:
- Row 1: 6+ stat cards with animated number counters, sparklines, trend arrows
- Row 2: Large line chart (30日趋势) + radar chart (AI维度分析)
- Row 3: Heatmap (案件活跃度) + pie chart (状态分布)
- Row 4: Dense activity feed table with timestamps and status indicators

- [ ] **Step 3: Commit**

```bash
git add theme-b/pages/app/dashboard.vue theme-b/components/
git commit -m "feat(theme-b): add Matrix dashboard with rich data viz"
```

### Task 19: Case Management Pages (Matrix Style)

**Files:**
- Create: `theme-b/pages/app/cases.vue`
- Create: `theme-b/components/cases/CaseDetailModal.vue` — full-width tabbed modal (not drawer)
- Create: `theme-b/components/cases/CreatePackageDialog.vue`
- Create: `theme-b/pages/app/case-packages/index.vue`
- Create: `theme-b/pages/app/case-packages/[id].vue`
- Create: `theme-b/pages/app/case-packages/import.vue`
- Create: `theme-b/pages/app/disposal-records.vue`

**Matrix differences:** Always-visible filter panel on left side. Dense table with monospace IDs (`font-mono`). Inline sparklines (via vue-sparkline) for amount trends in table cells. Full-width tabbed modal for case detail (tabs: 基本信息, AI分析, ML预测, 处置记录). Neon status badges.

- [ ] **Steps:** Create all pages and components following Task 6 structure → verify → commit

```bash
git commit -m "feat(theme-b): add case management pages"
```

### Task 20: Batch & Call Records (Matrix Style)

**Files:**
- Create: `theme-b/pages/app/batches.vue`
- Create: `theme-b/components/batches/BatchDetailModal.vue`
- Create: `theme-b/pages/app/call-records.vue`

**Matrix differences:** Animated progress bars with glow effect. Real-time aesthetic with pulsing status indicators. Call stats as large neon-colored number cards. Emotion/compliance charts as horizontal stacked bars.

- [ ] **Steps:** Create all pages → verify → commit

```bash
git commit -m "feat(theme-b): add batch list, call records"
```

### Task 21: Strategy Pages (Matrix Style)

**Files:**
- Create: `theme-b/pages/app/strategies.vue`
- Create: `theme-b/components/strategies/StrategyDetailModal.vue`
- Create: `theme-b/components/strategies/StrategyFormModal.vue`
- Create: `theme-b/components/strategies/CreateExecutionBatchDialog.vue`
- Create: `theme-b/pages/app/execution-batches.vue`
- Create: `theme-b/components/strategies/ExecutionBatchDetailModal.vue`
- Create: `theme-b/pages/app/action-types.vue`
- Create: `theme-b/components/strategies/ActionTypeDialog.vue`
- Create: `theme-b/pages/app/tags.vue`
- Create: `theme-b/components/strategies/TagDialog.vue`

**Matrix differences:** Strategy table with dense data. Workflow builder with node-graph visual feel (dark boxes connected by neon lines). Condition/action panels side by side in modal. Monospace condition expressions.

- [ ] **Steps:** Create all pages and components → verify → commit

```bash
git commit -m "feat(theme-b): add strategy, execution batches, action types, tags"
```

### Task 22: Messaging Pages (Matrix Style)

**Files:**
- Create: `theme-b/pages/app/sms-signatures.vue`
- Create: `theme-b/pages/app/sms-templates.vue`
- Create: `theme-b/components/sms/SmsTemplateDialog.vue`
- Create: `theme-b/pages/app/voices.vue`

**Matrix differences:** Dense table layouts. Template preview in monospace code block style with syntax highlighting for variables. Dark card backgrounds.

- [ ] **Steps:** Create all pages → verify → commit

```bash
git commit -m "feat(theme-b): add SMS and voice management"
```

### Task 23: Admin Pages (Matrix Style)

**Files:**
- Create: `theme-b/pages/app/users.vue`
- Create: `theme-b/components/admin/UserDialog.vue`
- Create: `theme-b/pages/app/roles.vue`
- Create: `theme-b/components/admin/RoleDialog.vue`
- Create: `theme-b/pages/app/organizations.vue`
- Create: `theme-b/components/admin/OrganizationDialog.vue`

**Matrix differences:** Permission matrix view for roles (grid of checkboxes with cyan highlights). Dense user table with inline status indicators. Role comparison view (side-by-side columns).

- [ ] **Steps:** Create all pages and dialogs → verify → commit

```bash
git commit -m "feat(theme-b): add user, role, organization management"
```

### Task 24: System Pages (Matrix Style)

**Files:**
- Create: `theme-b/pages/app/scheduled-tasks.vue`
- Create: `theme-b/components/system/CronEditor.vue`
- Create: `theme-b/components/system/TaskHistoryModal.vue`
- Create: `theme-b/pages/app/service-monitor.vue`
- Create: `theme-b/pages/app/tool-call-logs.vue`

**Matrix differences:** Service monitor as a status board with large status indicators, latency sparklines, and uptime percentages. Tool call logs with expandable JSON viewer (dark code block style). CronEditor with monospace expression display.

- [ ] **Steps:** Create all pages → verify → commit

```bash
git commit -m "feat(theme-b): add system pages"
```

### Task 25: Remaining Pages + Polish (Matrix Style)

**Files:**
- Create: `theme-b/pages/app/profile.vue`
- Create: `theme-b/pages/app/roadmap.vue`
- Create: `theme-b/pages/app/about.vue`
- Create: `theme-b/pages/app/forbidden.vue`
- Create: `theme-b/pages/404.vue`

**Matrix differences:** 404/403 with terminal aesthetic (blinking cursor, monospace text, `> ERROR 404: PAGE_NOT_FOUND`). Profile page with dark cards and subtle borders.

- [ ] **Steps:** Create all pages → verify all navigation → verify all dialogs → visual consistency check → commit

```bash
git commit -m "feat(theme-b): add remaining pages and polish"
```

---

## Chunk 3: Theme C — Warm (人性化功能丰富)

**Agent workspace:** `frontend/theme-c/`
**Design identity:** Warm, human, Notion/Figma/Lark inspired. Cream base (#FAFAF8), colorful accents, rounded corners, emoji icons, card-list hybrids, progressive disclosure, friendly illustrations, micro-interactions.

### Task 26: Scaffold Nuxt 3 App

Same as Task 1 but in `theme-c/` directory.

- [ ] **Step 1: Initialize and configure**

```bash
cd /Users/ck/Git/matrix/postloan/frontend
npx nuxi@3 init theme-c --packageManager npm
cd theme-c
npm install @nuxt/ui@^2 echarts vue-echarts
```

Configure Tailwind:
```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'PingFang SC', 'Microsoft YaHei', 'sans-serif']
      },
      colors: {
        warm: {
          bg: '#FAFAF8',
          surface: '#FFFFFF',
          border: '#E8E5E0',
          accent: '#6366F1',
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          info: '#3B82F6'
        }
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px'
      }
    }
  }
} satisfies Partial<Config>
```

Add in nuxt.config.ts:
```typescript
devServer: { port: 3002 },
```
And in head links:
```typescript
{ rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap' }
```

- [ ] **Step 2: Commit**

```bash
git add theme-c/
git commit -m "feat(theme-c): scaffold Warm Nuxt 3 app"
```

### Task 27: Create Mock Data

- [ ] **Step 1: Copy mock data from theme-a**

```bash
cp -r /Users/ck/Git/matrix/postloan/frontend/theme-a/data/ /Users/ck/Git/matrix/postloan/frontend/theme-c/data/
```

- [ ] **Step 2: Commit**

```bash
git add theme-c/data/
git commit -m "feat(theme-c): add mock data"
```

### Task 28: Layout and Navigation (Warm Style)

**Files:**
- Create: `theme-c/layouts/default.vue`
- Create: `theme-c/layouts/auth.vue`
- Create: `theme-c/layouts/landing.vue`
- Create: `theme-c/components/AppSidebar.vue`
- Create: `theme-c/components/AppHeader.vue`
- Create: `theme-c/composables/useNavigation.ts`

- [ ] **Step 1: Create navigation composable**

Same menu structure but with emoji icons:
- 📊 平台概览
- 📁 案件管理 (📦 案件包 / 📋 全部案件 / 🔄 处置记录)
- 🧠 智能分析 (🔬 分析批次 / 📞 通话记录)
- ⚡ 策略中心 (🎯 策略管理 / ▶️ 执行批次 / 🔧 动作类型 / 🏷️ 标签管理)
- 💬 消息管理 (✍️ 短信签名 / 📝 短信模板 / 🎙️ 语音管理)
- ⚙️ 系统管理 (👤 用户 / 🛡️ 角色 / 🏢 组织 / ⏰ 定时任务 / 📡 服务监控 / 📜 日志)

- [ ] **Step 2: Create AppSidebar.vue**

Warm style:
- 260px width, cream background
- Rounded section groups with subtle backgrounds
- Search input at top ("搜索菜单...")
- Favorites section (star-marked pages)
- Recent items section
- Emoji icons next to labels
- Active item: rounded highlight with accent color
- Smooth hover transitions
- Bottom: user card with avatar, name, role

- [ ] **Step 3: Create AppHeader.vue**

Warm style:
- Greeting message: "👋 你好, 管理员"
- Breadcrumb with rounded segment style
- Right: Quick actions button, notifications bell with friendly badge, user menu

- [ ] **Step 4: Create layouts**

default.vue: Cream background (#FAFAF8), sidebar + header + content with generous rounded cards.
auth.vue: Split layout — left illustration panel, right content.
landing.vue: Warm landing layout with illustrations.

- [ ] **Step 5: Verify and commit**

```bash
git add theme-c/layouts/ theme-c/components/ theme-c/composables/
git commit -m "feat(theme-c): add Warm layout with emoji nav and search"
```

### Task 29: Login & Landing (Warm Style)

- [ ] **Step 1: Create login page**

Split layout: Left panel with warm illustration/branding + tagline "让贷后管理更智能、更人性". Right panel with friendly form, rounded inputs, "欢迎回来 👋" heading.

- [ ] **Step 2: Create landing page**

Warm, inviting: illustrated hero section, feature cards with icons and descriptions, testimonial-style section, friendly CTA.

- [ ] **Step 3: Commit**

```bash
git add theme-c/pages/
git commit -m "feat(theme-c): add Warm login and landing pages"
```

### Task 30: Dashboard (Warm Style)

- [ ] **Step 1: Create chart components**

Warm style: Smooth area charts instead of line, friendly donut charts with large center labels, soft gradient fills, animated transitions.

- [ ] **Step 2: Create dashboard page**

- Greeting banner: "👋 你好, 管理员 — 今天有 12 个案件需要处理"
- Row 1: 4 stat cards with illustrated icons (not just numbers), friendly color coding
- Row 2: Area chart (趋势) + donut chart (状态) with tooltips
- Row 3: Quick action cards (新建案件包, 开始分析, 创建策略, 查看报告)
- Row 4: Recent items as card list with avatars and relative timestamps

- [ ] **Step 3: Commit**

```bash
git add theme-c/pages/app/dashboard.vue theme-c/components/
git commit -m "feat(theme-c): add Warm dashboard with friendly UX"
```

### Task 31: Case Management Pages (Warm Style)

**Files:**
- Create: `theme-c/pages/app/cases.vue`
- Create: `theme-c/components/cases/CaseDetailSlideOver.vue` — slide-over panel (not drawer/modal)
- Create: `theme-c/components/cases/CreatePackageDialog.vue`
- Create: `theme-c/pages/app/case-packages/index.vue`
- Create: `theme-c/pages/app/case-packages/[id].vue`
- Create: `theme-c/pages/app/case-packages/import.vue`
- Create: `theme-c/pages/app/disposal-records.vue`

**Warm differences:** Search-first bar at top. Filter chips (not dropdowns) that can be added/removed. Toggle between card view and table view. Case detail via slide-over panel with section headers and collection history timeline. Import wizard with illustrations per step and celebration animation on completion.

- [ ] **Steps:** Create all pages and components → verify → commit

```bash
git commit -m "feat(theme-c): add case management pages"
```

### Task 32: Batch & Call Records (Warm Style)

**Files:**
- Create: `theme-c/pages/app/batches.vue`
- Create: `theme-c/components/batches/BatchDetailSlideOver.vue`
- Create: `theme-c/pages/app/call-records.vue`

**Warm differences:** Friendly progress indicators with emoji status (✅ ❌ ⏳). Card-based batch overview instead of dense table. Call stats with friendly icons and warm colors.

- [ ] **Steps:** Create all pages → verify → commit

```bash
git commit -m "feat(theme-c): add batch list, call records"
```

### Task 33: Strategy Pages (Warm Style)

**Files:**
- Create: `theme-c/pages/app/strategies.vue`
- Create: `theme-c/components/strategies/StrategyDetailSlideOver.vue`
- Create: `theme-c/components/strategies/StrategyFormSlideOver.vue`
- Create: `theme-c/components/strategies/CreateExecutionBatchDialog.vue`
- Create: `theme-c/pages/app/execution-batches.vue`
- Create: `theme-c/components/strategies/ExecutionBatchDetailSlideOver.vue`
- Create: `theme-c/pages/app/action-types.vue`
- Create: `theme-c/components/strategies/ActionTypeDialog.vue`
- Create: `theme-c/pages/app/tags.vue`
- Create: `theme-c/components/strategies/TagDialog.vue`

**Warm differences:** Visual strategy cards with plain-language condition summaries ("当逾期天数 > 90天 且 风险等级 = 高..."). Guided wizard for creating strategies with helpful tooltips and inline help text. Friendly tag display with colorful pills.

- [ ] **Steps:** Create all pages and components → verify → commit

```bash
git commit -m "feat(theme-c): add strategy, execution batches, action types, tags"
```

### Task 34: Messaging Pages (Warm Style)

**Files:**
- Create: `theme-c/pages/app/sms-signatures.vue`
- Create: `theme-c/pages/app/sms-templates.vue`
- Create: `theme-c/components/sms/SmsTemplateDialog.vue`
- Create: `theme-c/pages/app/voices.vue`

**Warm differences:** Template cards with live preview panel. Friendly variable insertion UI with clickable variable chips. Voice cards with avatar-style icons.

- [ ] **Steps:** Create all pages → verify → commit

```bash
git commit -m "feat(theme-c): add SMS and voice management"
```

### Task 35: Admin Pages (Warm Style)

**Files:**
- Create: `theme-c/pages/app/users.vue`
- Create: `theme-c/components/admin/UserDialog.vue`
- Create: `theme-c/pages/app/roles.vue`
- Create: `theme-c/components/admin/RoleDialog.vue`
- Create: `theme-c/pages/app/organizations.vue`
- Create: `theme-c/components/admin/OrganizationDialog.vue`

**Warm differences:** People-focused cards with avatars and role tag pills. Drag-style role assignment (visual, non-functional in mock). Organization cards with team member count and warm illustrations.

- [ ] **Steps:** Create all pages and dialogs → verify → commit

```bash
git commit -m "feat(theme-c): add user, role, organization management"
```

### Task 36: System Pages (Warm Style)

**Files:**
- Create: `theme-c/pages/app/scheduled-tasks.vue`
- Create: `theme-c/components/system/CronEditor.vue`
- Create: `theme-c/components/system/TaskHistorySlideOver.vue`
- Create: `theme-c/pages/app/service-monitor.vue`
- Create: `theme-c/pages/app/tool-call-logs.vue`

**Warm differences:** Friendly service cards with large green checkmarks for healthy, yellow warning icons for degraded. Task history displayed as a visual timeline with emoji markers. Tool call logs with expandable accordion rows.

- [ ] **Steps:** Create all pages → verify → commit

```bash
git commit -m "feat(theme-c): add system pages"
```

### Task 37: Remaining Pages + Polish (Warm Style)

**Files:**
- Create: `theme-c/pages/app/profile.vue`
- Create: `theme-c/pages/app/roadmap.vue`
- Create: `theme-c/pages/app/about.vue`
- Create: `theme-c/pages/app/forbidden.vue`
- Create: `theme-c/pages/404.vue`

**Warm differences:** Illustrated empty states with friendly copy. 404 page: "迷路了？" with warm illustration and helpful navigation links. Roadmap with friendly milestone illustrations. Profile with warm avatar card.

- [ ] **Steps:** Create all pages → verify all navigation → verify all dialogs → visual consistency check → commit

```bash
git commit -m "feat(theme-c): add remaining pages and polish"
```

---

## Execution Strategy

This plan is designed for **3 parallel agents** (subagents):

| Agent | Tasks | Theme |
|-------|-------|-------|
| Agent A | Tasks 1-13 | Crystal (简洁明快) |
| Agent B | Tasks 14-25 | Matrix (专业科技感) |
| Agent C | Tasks 26-37 | Warm (人性化功能丰富) |

**Dependencies:**
- Agent A Task 2 (mock data creation) must complete before Agent B Task 15 and Agent C Task 27 can copy the data.
- No other cross-agent dependencies exist. All three agents can work in parallel after mock data is available.

**Verification after all agents complete:**
1. `cd theme-a && npm run dev` → http://localhost:3000
2. `cd theme-b && npm run dev` → http://localhost:3001
3. `cd theme-c && npm run dev` → http://localhost:3002
4. Click through every sidebar link in each app
5. Open every dialog/drawer
6. Verify charts render
