# Home Pages Design — Public Landing + Authenticated Workspace

## Overview

DevTrack currently has no public landing page (root `/` is the login form) and no dedicated post-login home. This spec adds both:

1. **Public landing page** at `/` — split layout with branding + app preview
2. **Authenticated home** at `/app/home` — command center with personal tasks, activity, stats, quick actions

## Public Landing Page

### Route & Layout

- **URL:** `/`
- **Layout:** `auth` (no sidebar, centered content)
- **Auth redirect:** If user has valid token, auto-redirect to `/app/home`

### Structure — Split Layout

**Left side:**
- DevTrakr logo (`~/assets/images/logo-icon.svg`) + app name
- Tagline: "团队项目管理，高效协作"
- Feature highlights as icon+text rows:
  - Issue 追踪 — 创建、分配、跟踪问题
  - 数据看板 — 实时统计分析
  - 团队协作 — 权限与角色管理
  - 仓库集成 — Git 仓库关联
- Two CTA buttons: 登录 (primary, links to `/login`) and 注册 (outline, links to `/register`)

**Right side:**
- Stylized app preview mockup built with HTML/CSS (not a screenshot)
- Shows a mini kanban board and trend chart using crystal color palette
- Decorative, not functional — conveys "this is a project management tool"

**Footer:** `© 2026 DevTrakr 项目管理平台`

**Responsive behavior:**
- Desktop: side-by-side, left content + right preview
- Mobile (< md): stacked — content on top, preview hidden or simplified below

### Login Page Relocation

The current login form at `/` moves to a new `/login` route:
- **File:** `frontend/app/pages/login.vue`
- Same `auth` layout, same form, same logic
- After successful login, redirect to `/app/home` (not `/app/issues`)

## Authenticated Home Page

### Route & Layout

- **URL:** `/app/home`
- **Layout:** `default` (sidebar + header)
- **Page title:** "工作台"

### Structure — Command Center (Two-Column)

#### Quick Actions Bar (top, full width)

- "新建 Issue" button (primary, links to issue creation or opens modal)
- Search input (placeholder: "搜索 Issue 或项目...") — navigates to `/app/issues?search=...`
- Quick jump links to `/app/projects` and `/app/issues`

#### Left Column — Personal

**我的待办:**
- List of issues assigned to current user, excluding resolved/closed
- Sorted by priority (紧急 → 高 → 中 → 低)
- Each row: priority color dot, issue number (ISS-XXX), title, priority badge
- Click navigates to `/app/issues/{id}`
- Header shows count
- Empty state: "没有待办任务 🎉"
- Limit: 10 items, with "查看全部" link to `/app/issues?assigned_to=me`

**提及我的:**
- Recent notifications where user is mentioned or assigned
- Each row: actor name + action description + time ago
- Click navigates to relevant issue
- Header shows unread count
- Limit: 5 items, with "查看全部" link to `/app/notifications`

#### Right Column — Team

**项目健康:**
- 4 stat cards in 2x2 grid:
  - 本周解决 (green)
  - 待处理 (amber)
  - 进行中 (blue)
  - 总 Issue 数 (crystal/purple)
- Same data as existing `/api/dashboard/stats/` endpoint

**最近动态:**
- Team activity feed, 10 most recent items
- Each row: icon + description + time ago
- Same data and rendering as current dashboard activity section
- Scrollable if overflow

### Data Sources

All data from existing backend endpoints — no new backend work:

| Section | Endpoint | Notes |
|---------|----------|-------|
| My tasks | `GET /api/issues/?assigned_to={userId}&status__not=resolved&status__not=closed&ordering=-priority&page_size=10` | Filter by current user, exclude done |
| Mentions | `GET /api/notifications/?is_read=false&page_size=5` | Unread notifications |
| Stats | `GET /api/dashboard/stats/` | Existing endpoint |
| Activity | `GET /api/dashboard/recent-activity/` | Existing endpoint |

If the issues endpoint doesn't support `assigned_to` filtering or `status__not` exclusion, that filtering will happen client-side from a broader query.

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `frontend/app/pages/login.vue` | Login form (moved from current `index.vue`) |
| `frontend/app/pages/app/home.vue` | Authenticated command center |

### Modified Files

| File | Change |
|------|--------|
| `frontend/app/pages/index.vue` | Rewrite as public landing page (currently login form) |
| `frontend/app/middleware/auth.global.ts` | Add `/login` to public routes; change post-login redirect to `/app/home`; redirect authenticated users from `/` to `/app/home` |
| `frontend/app/composables/useNavigation.ts` | Add "工作台" as first nav item with `i-heroicons-home` icon, route `/app/home` |
| `frontend/app/pages/login.vue` (new) | Login form extracted from current `index.vue`, redirect target changed to `/app/home` |

### Unchanged

- `/app/dashboard` — keeps charts, leaderboard, analytics (separate purpose)
- All other pages, layouts, components
- All backend endpoints and models

## Navigation Updates

- Sidebar: "工作台" added as first item, icon `i-heroicons-home`, route `/app/home`
- Login success: redirect changes from `/app/issues` → `/app/home`
- Auth middleware: `/login` added as allowed unauthenticated route

## Responsive Behavior

**Public landing:**
- `>= md`: split layout (left content, right preview)
- `< md`: stacked, preview hidden or simplified

**Authenticated home:**
- `>= lg`: two-column command center
- `md`: two-column, tighter spacing
- `< md`: single column — quick actions, then tasks, mentions, stats, activity stacked
