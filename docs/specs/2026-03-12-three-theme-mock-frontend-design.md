# Three-Theme Mock Frontend Design Spec

**Date**: 2026-03-12
**Purpose**: Create three independent mock static frontends for the post-loan management platform, for the product owner to evaluate design quality and select the best one for production development.
**Audience**: Marketing department demos + internal design evaluation.

---

## 1. Overview

Three fully independent Nuxt 3 applications, each showcasing a distinct design philosophy. All pages use hardcoded mock data (no API calls). All UI is in Simplified Chinese (zh-CN).

The user will evaluate all three and select one to develop into the production frontend.

## 2. Project Structure

```
frontend/
├── theme-a/          # Crystal (简洁明快)
│   ├── nuxt.config.ts
│   ├── package.json
│   ├── app.vue
│   ├── pages/
│   ├── layouts/
│   ├── components/
│   └── assets/
├── theme-b/          # Matrix (专业科技感)
│   ├── (same structure)
├── theme-c/          # Warm (人性化功能丰富)
│   ├── (same structure)
├── docs/             # Existing documentation
└── README.md
```

Each app is fully standalone with its own `package.json`, dev server, and build pipeline.

**Tech stack per app:**
- Nuxt 3 + Nuxt UI + Tailwind CSS
- ECharts for dashboard visualizations
- All data hardcoded as mock JSON/TS files
- No API calls, no auth logic, no state management needed

## 3. Page Inventory

Every app must implement all of the following pages with mock data:

| Area | Page | Route | Key Elements |
|------|------|-------|-------------|
| Public | Login | `/login` | Username/password form, captcha, branding |
| Public | Landing/Home | `/` | Product introduction, CTA to login |
| Dashboard | Analytics overview | `/app/dashboard` | Stat cards, charts (line, pie, bar), trends, recent activity, top packages |
| Cases | Case list | `/app/cases` | Filterable/sortable table, status badges, stat summary cards |
| Cases | Case detail | `/app/cases` (dialog) | AI analysis results, ML predictions, tags, collection history timeline |
| Packages | Package list | `/app/case-packages` | Package cards/table, status, stats |
| Packages | Package detail | `/app/case-packages/:id` | Case breakdown, import status, analysis stats |
| Packages | Import workflow | `/app/case-packages/import` | Multi-step wizard: upload → column mapping → confirm |
| Batches | Batch list | `/app/batches` | Batch table with status, progress indicators |
| Batches | Batch detail | `/app/batches` (dialog) | Item-level status, error messages, statistics |
| Strategy | Strategy list | `/app/strategies` | Strategy cards/table with active/inactive status |
| Strategy | Strategy dialog | `/app/strategies` (dialog) | Workflow builder: conditions + actions configuration |
| Strategy | Execution batch list | `/app/execution-batches` | Execution runs with status and results |
| Strategy | Execution batch detail | `/app/execution-batches` (dialog) | Run details, action logs |
| Actions | Action type list | `/app/action-types` | Action type configuration table |
| Actions | Tag management | `/app/tags` | Tag CRUD with type indicators |
| SMS | Signature list | `/app/sms-signatures` | SMS signature management |
| SMS | Template list | `/app/sms-templates` | SMS template management with preview |
| Voice | Voice list | `/app/voices` | Voice configuration management |
| Disposal | Disposal records | `/app/disposal-records` | Stat cards (status distribution, overview), filterable table, detail dialog |
| Call | Call records | `/app/call-records` | Stats panel (emotion/compliance distribution, connect rate, avg duration, token cost, call cost), call log table with filters |
| Admin | User list | `/app/users` | User management table |
| Admin | Role list | `/app/roles` | Role management with permissions |
| Admin | Organization list | `/app/organizations` | Multi-tenant org management |
| System | Scheduled tasks | `/app/scheduled-tasks` | Cron-based task table with editor |
| System | Service monitor | `/app/service-monitor` | Health status dashboard |
| System | Tool call logs | `/app/tool-call-logs` | API invocation audit trail |
| Profile | User profile | `/app/profile` | User info and settings |
| Info | Roadmap | `/app/roadmap` | Product roadmap display |
| Info | About | `/app/about` | App version and info |
| Errors | 404 | `/404` | Not found page |
| Errors | Forbidden | `/app/forbidden` | Permission denied page |

## 4. Theme Definitions

### Theme A: Crystal (简洁明快)

**Design Philosophy**: Less is more. Every element earns its place.

- **Inspiration**: Linear, Apple, Stripe Dashboard
- **Color Palette**: White base (#FFFFFF), single accent (blue/violet), minimal grays for hierarchy
- **Layout**: Generous whitespace, slim sidebar (icon-only, expandable), card-based content areas
- **Typography**: Clean sans-serif (Inter or similar), large headings, comfortable line-height
- **Tables**: Minimal borders, hover highlights, subtle zebra striping
- **Charts**: Simple line/bar/donut with muted colors, no decoration
- **Navigation**: Collapsible icon sidebar + breadcrumb, no browser-style tabs
- **Dialogs**: Side drawer panels, clean form layouts
- **Key trait**: Every screen feels calm and uncluttered. Information density deliberately low.

### Theme B: Matrix (专业科技感)

**Design Philosophy**: Data is king. Maximum information, maximum control.

- **Inspiration**: Vercel, Datadog, Bloomberg Terminal (modern take)
- **Color Palette**: Dark mode primary (#0A0A0A base), neon accents (cyan #00D4FF, green #00FF88, purple #A855F7), glassmorphism effects
- **Layout**: Dense multi-panel layouts, data-forward design, minimal padding
- **Typography**: System sans-serif for UI, monospace accents (JetBrains Mono) for numbers/IDs/codes
- **Tables**: Dense rows, sortable with indicators, inline status badges, sparkline columns
- **Charts**: Rich data viz — heatmaps, radar charts, animated counters, real-time aesthetic
- **Navigation**: Full sidebar with grouped sections + status indicators, command palette (Cmd+K) — UI shell only with hardcoded search results
- **Dialogs**: Full-width modals with tabbed content
- **Extra deps**: Sparkline library (e.g. vue-sparkline) for inline table sparklines
- **Key trait**: Feels like mission control. Every pixel serves data.

### Theme C: Warm (人性化功能丰富)

**Design Philosophy**: Technology should feel human. Guide, don't overwhelm.

- **Inspiration**: Notion, Figma, Lark/飞书
- **Color Palette**: Warm neutrals (cream #FAFAF8, soft gray), colorful balanced accents, light gradients
- **Layout**: Cards with rounded corners (12-16px radius), contextual tooltips, inline help text, progressive disclosure
- **Typography**: Friendly rounded sans-serif (Plus Jakarta Sans or similar), comfortable sizing
- **Tables**: Card-list hybrid views, expandable rows, rich inline previews
- **Charts**: Friendly donut/area charts with smooth animations, illustrated empty states
- **Navigation**: Sidebar with emoji/avatar icons, favorites section, recent items, search-first design
- **Dialogs**: Slide-over panels with sections, friendly illustrations
- **Key trait**: Feels approachable. Rich micro-interactions, never overwhelming.

## 5. Navigation Menu Structure

All three themes must use this menu hierarchy (visual presentation varies per theme):

```
平台概览 (Dashboard)
  └── 数据看板 → /app/dashboard

案件管理 (Case Management)
  ├── 案件包管理 → /app/case-packages
  ├── 全部案件 → /app/cases
  └── 处置记录 → /app/disposal-records

智能分析 (Intelligent Analysis)
  ├── 分析批次 → /app/batches
  └── 通话记录 → /app/call-records

策略中心 (Strategy Center)
  ├── 策略管理 → /app/strategies
  ├── 执行批次 → /app/execution-batches
  ├── 动作类型 → /app/action-types
  └── 标签管理 → /app/tags

消息管理 (Messaging)
  ├── 短信签名 → /app/sms-signatures
  ├── 短信模板 → /app/sms-templates
  └── 语音管理 → /app/voices

系统管理 (System)
  ├── 用户管理 → /app/users
  ├── 角色管理 → /app/roles
  ├── 组织管理 → /app/organizations
  ├── 定时任务 → /app/scheduled-tasks
  ├── 服务监控 → /app/service-monitor
  └── 工具调用日志 → /app/tool-call-logs

其他 (Other — in user menu/footer, not sidebar)
  ├── 个人资料 → /app/profile
  ├── 产品路线图 → /app/roadmap
  └── 关于 → /app/about
```

## 5.1 Dialog & Component Inventory

Each page's interactive dialogs must be mocked (open/close works, forms are static):

| Page | Dialogs/Components |
|------|-------------------|
| Case list | CaseDetailDialog — tabs: basic info, AI analysis, collection history timeline |
| Case packages | CreatePackageDialog, PackageDetailDialog |
| Import workflow | 3-step wizard (upload → smart column mapping → confirm) |
| Batches | BatchDetailDialog — item list with status, statistics |
| Strategies | StrategyDialog (create/edit with workflow builder), StrategyDetailDialog |
| Execution batches | CreateExecutionBatchDialog (select strategy + batch), ExecutionBatchDetailDialog |
| Action types | ActionTypeDialog (create/edit) |
| Tags | TagDialog (create/edit with type selector) |
| SMS templates | SmsTemplateDialog (create/edit with preview) |
| Scheduled tasks | CronEditor component, HistoryDialog (execution history) |
| Users | CreateUserDialog, EditUserDialog |
| Roles | RoleDialog with permission assignment |
| Organizations | OrganizationDialog |

## 5.2 Key Page Design Details per Theme

### Login
- **Crystal**: Centered minimal card on subtle gradient background, single input flow
- **Matrix**: Full-screen dark with animated particle/grid background, glassmorphism card
- **Warm**: Split layout — illustration/branding left, form right, friendly welcome copy

### Dashboard
- **Crystal**: 4 stat cards → 2 charts → recent activity list. Clean grid.
- **Matrix**: 6+ stat cards with animated counters → multi-chart grid (heatmap, radar, line, pie) → live activity feed. Dense.
- **Warm**: Greeting banner with user name → stat cards with icons → charts with tooltips → quick-action buttons → recent items as cards.

### Case List
- **Crystal**: Collapsible filter bar → clean table → pagination. Detail via side drawer.
- **Matrix**: Always-visible filter panel → dense data table with inline badges/sparklines → detail via full-width tabbed modal.
- **Warm**: Search-first bar → filter chips → card/table toggle → detail via slide-over with timeline.

### Case Package Import
- **Crystal**: 3-step stepper (upload → map → confirm), minimal per step
- **Matrix**: Wizard with live preview, drag-drop column mapping, real-time validation stats
- **Warm**: Illustrated wizard, smart suggestions highlighted, celebration on completion

### Strategy Management
- **Crystal**: Clean card list → form dialog for editing
- **Matrix**: Dense table with inline status → workflow builder with node-graph feel
- **Warm**: Visual cards with condition summaries → guided builder with plain-language previews

### Admin Pages
- **Crystal**: Standard list + form dialogs, consistent minimal style
- **Matrix**: Dense tables, permission matrices, role comparison views
- **Warm**: People-focused cards with avatars, tag-style role assignment

## 6. Mock Data Requirements

Each theme needs the same mock data set to ensure fair comparison. **Agents must reference the old frontend's TypeScript interfaces at `/Users/ck/Git/matrix/postloan/frontend-old/src/api/` for canonical field definitions** — specifically `cases.ts`, `casePackages.ts`, `batches.ts`, `strategies.ts`, `disposalRecords.ts`, `dashboard.ts`, `sms.ts`, `voices.ts`, `users.ts`, `scheduledTasks.ts`, `logs.ts`, and `types.ts`.

### Record Counts
- **Dashboard**: 6 stat values, 30-day trend data, status/priority distributions, AI tag dimension stats, top 5 packages, 10 recent AI analyses
- **Cases**: 50+ mock cases with varied statuses, priorities, AI tags, amounts, plus 5-10 CollectionRecord entries per case for history timeline
- **Case Packages**: 8-10 packages with different types (general, collection_phone, litigation, etc.) and statuses
- **Disposal Records**: 30 records with varied statuses, plus stats (status distribution, overview grid)
- **Batches**: 5-6 analysis batches in various states (pending, running, paused, completed, failed)
- **Strategies**: 4-5 strategies with full workflows (conditions + actions)
- **Execution Batches**: 3-4 execution runs with execution logs
- **Tags**: 15-20 tags across categories (boolean, enum, integer, decimal, string types)
- **Action Types**: 5-6 action types (send_sms, make_call, update_case, create_task, send_email)
- **SMS**: 3 signatures, 5 templates with content
- **Voices**: 3 voice configs
- **Call Records**: 20 records with stats (emotion distribution, compliance distribution, connect rate, avg duration, token consumption, call cost)
- **Users**: 10 users across roles
- **Roles**: 4 roles (superadmin, admin, operator, viewer) with permission lists
- **Organizations**: 3 organizations
- **Scheduled Tasks**: 4-5 tasks with cron expressions and execution history
- **Tool Call Logs**: 15 log entries

### Key Domain Fields (Chinese content required)
- Case statuses: 待处理, 处理中, 已解决, 已关闭
- Priorities: 高 (逾期严重), 中 (标准), 低 (轻微)
- AI tags: risk_level, urgency, customer_type, overdue_severity, willingness_level, suggested_strategy
- Package types: 通用, 电话催收, 上门催收, 诉讼, 调解, 执行, 核销
- Amounts: Realistic RMB values (use 万 for 10,000+)
- Dates: Realistic date ranges around 2026-01-01 to 2026-03-12

## 7. Technical Notes

- **ECharts + Nuxt 3 SSR**: All chart components must be wrapped in `<ClientOnly>` or use a client-only plugin. ECharts does not support server-side rendering.
- **Fonts**: Load via Google Fonts. CJK (Chinese) text will use system font fallback (PingFang SC, Microsoft YaHei, etc.). Specify in Tailwind fontFamily config.
- **Nuxt UI version**: Use Nuxt UI v2 (stable). Do not use v3/alpha.
- **Dark mode (Theme B)**: Requires custom `tailwind.config.ts` color palette overriding Nuxt UI default tokens. Set `colorMode: { preference: 'dark' }` in nuxt.config.
- **No real auth**: Login page is purely visual. "Login" button navigates directly to `/app/dashboard`.

## 8. Implementation Strategy

Three parallel agents, each building one complete app independently. No code sharing.

**Execution order per agent:**
1. Scaffold Nuxt 3 + Nuxt UI app
2. Set up layouts and navigation
3. Create mock data files (reference old frontend's API types for field definitions)
4. Build pages starting with: Login → Dashboard → Case Management → Strategy → Admin → remaining pages
5. Polish: animations, empty states, responsive basics

## 9. Success Criteria

- All 30+ pages/dialogs implemented per theme
- Each theme has a clearly distinct, cohesive design identity
- Mock data is realistic and consistent (Chinese content, realistic amounts/dates)
- Pages are navigable — sidebar links work, dialogs open, wizards step through
- No API calls — everything is static mock
- Each app runs independently with `npm run dev`
