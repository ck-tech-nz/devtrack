# Project Management Tool (theme-pm) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a project management demo app (theme-pm) reusing theme-a's Crystal design system, with issue tracking, GitHub repo integration, AI analysis, and developer stats — all powered by mock data.

**Architecture:** Nuxt 3 SPA with Nuxt UI components, Tailwind CSS (Crystal purple theme), and ECharts for data visualization. Follows theme-a's exact patterns: collapsible sidebar, breadcrumb header, card-based layouts. AI and GitHub modules use a `useServiceStatus()` composable for hot-plug graceful degradation.

**Tech Stack:** Nuxt 3, Vue 3, TypeScript, Nuxt UI 2.x, Tailwind CSS, ECharts 6, vue-echarts 8

**Spec:** `docs/superpowers/specs/2026-03-20-project-management-tool-design.md`

**Reference codebase:** `theme-a/` — copy patterns directly, do not reinvent.

---

## File Structure

```
theme-pm/
├── package.json                    # Same deps as theme-a
├── nuxt.config.ts                  # SPA mode, port 3004, baseURL /theme-pm/
├── tailwind.config.ts              # Crystal color palette (identical to theme-a)
├── tsconfig.json                   # Extends .nuxt/tsconfig.json
├── app.vue                         # Root: NuxtLayout + NuxtPage, zh-CN
│
├── layouts/
│   ├── default.vue                 # Sidebar + Header + main content area
│   └── auth.vue                    # Centered gradient login layout
│
├── composables/
│   ├── useNavigation.ts            # Nav items, currentPath, breadcrumbs
│   └── useServiceStatus.ts         # Hot-plug status for AI & GitHub services
│
├── data/
│   └── mock.ts                     # All mock data (~400 lines)
│
├── components/
│   ├── AppSidebar.vue              # Collapsible sidebar with service status dots
│   ├── AppHeader.vue               # Breadcrumb + user dropdown
│   ├── ServiceStatusDot.vue        # Green/gray dot indicator (reusable)
│   ├── dashboard/
│   │   └── StatCard.vue            # KPI card with trend indicator
│   ├── charts/
│   │   ├── LineChart.vue           # ECharts line chart (from theme-a)
│   │   ├── PieChart.vue            # ECharts pie/donut chart (from theme-a)
│   │   └── BarChart.vue            # ECharts bar chart (from theme-a)
│   └── projects/
│       └── KanbanBoard.vue         # 3-column kanban (待处理/进行中/已解决)
│
├── pages/
│   ├── index.vue                   # Login page (layout: auth)
│   └── app/
│       ├── dashboard.vue           # Project overview dashboard
│       ├── projects/
│       │   ├── index.vue           # Project list (card grid)
│       │   └── [id].vue            # Project detail with kanban
│       ├── issues/
│       │   ├── index.vue           # Issue list (table + filters)
│       │   └── [id].vue            # Issue detail (info, AI, GitHub, timeline)
│       ├── repos/
│       │   ├── index.vue           # GitHub repo list
│       │   └── [id].vue            # Repo detail (commits, PRs, issues)
│       └── ai-insights.vue         # AI insights dashboard
│
├── public/                         # (empty, for future static assets)
└── server/
    └── tsconfig.json               # Extends ../.nuxt/tsconfig.server.json
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `theme-pm/package.json`
- Create: `theme-pm/nuxt.config.ts`
- Create: `theme-pm/tailwind.config.ts`
- Create: `theme-pm/tsconfig.json`
- Create: `theme-pm/app.vue`
- Create: `theme-pm/server/tsconfig.json`

- [ ] **Step 1: Create package.json**

Copy from theme-a, change name to `theme-pm`:

```json
{
  "name": "theme-pm",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "nuxt build",
    "dev": "nuxt dev",
    "generate": "nuxt generate",
    "preview": "nuxt preview",
    "postinstall": "nuxt prepare"
  },
  "dependencies": {
    "@iconify-json/heroicons": "^1.2.3",
    "@nuxt/ui": "^2.22.3",
    "echarts": "^6.0.0",
    "nuxt": "^3.21.1",
    "vue": "^3.5.30",
    "vue-echarts": "^8.0.1",
    "vue-router": "^4.6.4"
  }
}
```

- [ ] **Step 2: Create nuxt.config.ts**

Same as theme-a but with port 3004, baseURL `/theme-pm/`, and updated title:

```typescript
export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: false },
  devServer: { port: 3004 },
  modules: ['@nuxt/ui'],
  colorMode: { preference: 'light' },
  app: {
    baseURL: '/theme-pm/',
    head: {
      title: 'DevTrack - 项目管理平台',
      link: [
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
        },
      ],
    },
  },
  compatibilityDate: '2025-01-01',
})
```

- [ ] **Step 3: Create tailwind.config.ts, tsconfig.json, app.vue, server/tsconfig.json**

`tailwind.config.ts` — identical to theme-a (Crystal colors).

`tsconfig.json`:
```json
{ "extends": "./.nuxt/tsconfig.json" }
```

`app.vue` — identical to theme-a.

`server/tsconfig.json`:
```json
{ "extends": "../.nuxt/tsconfig.server.json" }
```

- [ ] **Step 4: Install dependencies**

```bash
cd theme-pm && npm install
```

- [ ] **Step 5: Verify dev server starts**

```bash
cd theme-pm && npm run dev
```

Expected: Nuxt dev server starts on port 3004, blank page loads at `http://localhost:3004/theme-pm/`.

- [ ] **Step 6: Commit**

```bash
git add theme-pm/
git commit -m "feat(theme-pm): scaffold project with Nuxt 3 + Crystal theme"
```

---

## Task 2: Layouts

**Files:**
- Create: `theme-pm/layouts/default.vue`
- Create: `theme-pm/layouts/auth.vue`

- [ ] **Step 1: Create default.vue layout**

Identical to theme-a's `layouts/default.vue`:

```vue
<template>
  <div class="flex h-screen bg-gray-50/50">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-y-auto p-6 lg:p-8">
        <slot />
      </main>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Create auth.vue layout**

Identical to theme-a's `layouts/auth.vue`:

```vue
<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-crystal-50 via-white to-crystal-100">
    <slot />
  </div>
</template>
```

- [ ] **Step 3: Commit**

```bash
git add theme-pm/layouts/
git commit -m "feat(theme-pm): add default and auth layouts"
```

---

## Task 3: Navigation Composable

**Files:**
- Create: `theme-pm/composables/useNavigation.ts`

- [ ] **Step 1: Create useNavigation.ts**

Follow theme-a's pattern but with the new nav structure. 5 top-level items, GitHub and AI sections get status indicators (handled in sidebar component).

```typescript
export interface NavItem {
  label: string
  icon: string
  to?: string
  children?: NavItem[]
  serviceKey?: 'github' | 'ai'  // for hot-plug status dot
}

export const useNavigation = () => {
  const navItems: NavItem[] = [
    {
      label: '项目概览',
      icon: 'i-heroicons-squares-2x2',
      to: '/app/dashboard',
    },
    {
      label: '项目管理',
      icon: 'i-heroicons-folder-open',
      to: '/app/projects',
    },
    {
      label: '问题跟踪',
      icon: 'i-heroicons-bug-ant',
      to: '/app/issues',
    },
    {
      label: 'GitHub 仓库',
      icon: 'i-heroicons-code-bracket',
      to: '/app/repos',
      serviceKey: 'github',
    },
    {
      label: 'AI 洞察',
      icon: 'i-heroicons-cpu-chip',
      to: '/app/ai-insights',
      serviceKey: 'ai',
    },
  ]

  const route = useRoute()
  const currentPath = computed(() => route.path)

  const breadcrumbs = computed(() => {
    const path = route.path
    const crumbs: { label: string; to?: string }[] = [{ label: '首页', to: '/app/dashboard' }]

    for (const item of navItems) {
      if (item.to === path) {
        crumbs.push({ label: item.label })
        return crumbs
      }
    }

    // Sub-pages
    if (path.startsWith('/app/projects/')) {
      crumbs.push({ label: '项目管理', to: '/app/projects' })
      crumbs.push({ label: '项目详情' })
      return crumbs
    }
    if (path.startsWith('/app/issues/')) {
      crumbs.push({ label: '问题跟踪', to: '/app/issues' })
      crumbs.push({ label: 'Issue 详情' })
      return crumbs
    }
    if (path.startsWith('/app/repos/')) {
      crumbs.push({ label: 'GitHub 仓库', to: '/app/repos' })
      crumbs.push({ label: '仓库详情' })
      return crumbs
    }

    return crumbs
  })

  return { navItems, currentPath, breadcrumbs }
}
```

- [ ] **Step 2: Commit**

```bash
git add theme-pm/composables/
git commit -m "feat(theme-pm): add navigation composable with breadcrumbs"
```

---

## Task 4: Service Status Composable

**Files:**
- Create: `theme-pm/composables/useServiceStatus.ts`

- [ ] **Step 1: Create useServiceStatus.ts**

Provides reactive status for AI and GitHub services. In demo mode, both default to "online" but can be toggled for testing degradation.

```typescript
interface ServiceState {
  online: boolean
  label: string
}

const state = reactive<Record<string, ServiceState>>({
  github: { online: true, label: 'GitHub' },
  ai: { online: true, label: 'AI 服务' },
})

export const useServiceStatus = () => {
  const isOnline = (key: string) => state[key]?.online ?? false
  const getLabel = (key: string) => state[key]?.label ?? key
  const toggle = (key: string) => {
    if (state[key]) state[key].online = !state[key].online
  }

  return { state, isOnline, getLabel, toggle }
}
```

- [ ] **Step 2: Commit**

```bash
git add theme-pm/composables/useServiceStatus.ts
git commit -m "feat(theme-pm): add service status composable for hot-plug design"
```

---

## Task 5: Core Shell Components (Sidebar, Header, ServiceStatusDot)

**Files:**
- Create: `theme-pm/components/AppSidebar.vue`
- Create: `theme-pm/components/AppHeader.vue`
- Create: `theme-pm/components/ServiceStatusDot.vue`

- [ ] **Step 1: Create ServiceStatusDot.vue**

Simple green/gray dot:

```vue
<template>
  <span
    class="inline-block w-2 h-2 rounded-full flex-shrink-0"
    :class="online ? 'bg-emerald-400' : 'bg-gray-300'"
    :title="online ? '在线' : '离线'"
  />
</template>

<script setup lang="ts">
defineProps<{ online: boolean }>()
</script>
```

- [ ] **Step 2: Create AppSidebar.vue**

Based on theme-a's sidebar. Key differences:
- Logo shows "D" for DevTrack instead of "C" for Crystal
- Nav items are flat (no children groups) — simpler than theme-a
- Items with `serviceKey` show a `ServiceStatusDot` next to their label

```vue
<template>
  <aside
    class="h-screen bg-white border-r border-gray-100 flex flex-col transition-all duration-300 ease-in-out flex-shrink-0 relative z-30"
    :class="expanded ? 'w-60' : 'w-16'"
    @mouseenter="expanded = true"
    @mouseleave="expanded = false"
  >
    <!-- Logo -->
    <div class="h-16 flex items-center px-4 border-b border-gray-50">
      <div class="w-8 h-8 rounded-lg bg-crystal-500 flex items-center justify-center flex-shrink-0">
        <span class="text-white font-bold text-sm">D</span>
      </div>
      <transition name="fade">
        <span v-if="expanded" class="ml-3 font-semibold text-gray-900 whitespace-nowrap">DevTrack</span>
      </transition>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto py-4 space-y-1 px-2">
      <NuxtLink
        v-for="item in navItems"
        :key="item.label"
        :to="item.to!"
        class="flex items-center h-10 px-2 rounded-lg transition-colors group"
        :class="currentPath === item.to || (item.to && currentPath.startsWith(item.to + '/'))
          ? 'bg-crystal-50 text-crystal-600'
          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'"
      >
        <UIcon :name="item.icon" class="w-5 h-5 flex-shrink-0" />
        <transition name="fade">
          <span v-if="expanded" class="ml-3 text-sm font-medium whitespace-nowrap flex items-center gap-2">
            {{ item.label }}
            <ServiceStatusDot
              v-if="item.serviceKey"
              :online="isOnline(item.serviceKey)"
            />
          </span>
        </transition>
      </NuxtLink>
    </nav>

    <!-- Service toggles (dev mode) -->
    <div v-if="expanded" class="border-t border-gray-50 py-3 px-3 space-y-1">
      <p class="text-[10px] uppercase tracking-wider text-gray-300 mb-1">服务状态 (Demo)</p>
      <button
        v-for="key in ['github', 'ai']"
        :key="key"
        class="flex items-center justify-between w-full text-xs text-gray-400 hover:text-gray-600 py-1"
        @click="toggle(key)"
      >
        <span>{{ getLabel(key) }}</span>
        <ServiceStatusDot :online="isOnline(key)" />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
const { navItems, currentPath } = useNavigation()
const { isOnline, toggle, getLabel } = useServiceStatus()
const expanded = ref(false)
</script>

<style scoped>
.fade-enter-active { transition: opacity 0.2s ease 0.1s; }
.fade-leave-active { transition: opacity 0.1s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
```

- [ ] **Step 3: Create AppHeader.vue**

Based on theme-a's header pattern:

```vue
<template>
  <header class="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6 lg:px-8 flex-shrink-0">
    <!-- Breadcrumb -->
    <nav class="flex items-center space-x-2 text-sm">
      <template v-for="(crumb, idx) in breadcrumbs" :key="idx">
        <UIcon v-if="idx > 0" name="i-heroicons-chevron-right-20-solid" class="w-4 h-4 text-gray-300" />
        <NuxtLink v-if="crumb.to" :to="crumb.to" class="text-gray-400 hover:text-gray-700 transition-colors">
          {{ crumb.label }}
        </NuxtLink>
        <span v-else class="text-gray-900 font-medium">{{ crumb.label }}</span>
      </template>
    </nav>

    <!-- Right side -->
    <div class="flex items-center space-x-3">
      <UButton icon="i-heroicons-bell" variant="ghost" color="gray" size="sm" class="relative">
        <span class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-crystal-500 rounded-full" />
      </UButton>

      <UDropdown :items="userMenuItems" :popper="{ placement: 'bottom-end' }">
        <button class="flex items-center space-x-2 hover:bg-gray-50 rounded-lg px-2 py-1.5 transition-colors">
          <div class="w-8 h-8 rounded-full bg-crystal-100 flex items-center justify-center">
            <span class="text-crystal-600 text-sm font-medium">管</span>
          </div>
          <span class="text-sm text-gray-700 font-medium hidden sm:inline">管理员</span>
          <UIcon name="i-heroicons-chevron-down-20-solid" class="w-4 h-4 text-gray-400" />
        </button>
      </UDropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
const { breadcrumbs } = useNavigation()
const router = useRouter()

const userMenuItems = [
  [{
    label: '退出登录',
    icon: 'i-heroicons-arrow-right-on-rectangle',
    click: () => router.push('/'),
  }],
]
</script>
```

- [ ] **Step 4: Commit**

```bash
git add theme-pm/components/AppSidebar.vue theme-pm/components/AppHeader.vue theme-pm/components/ServiceStatusDot.vue
git commit -m "feat(theme-pm): add sidebar, header, and service status dot components"
```

---

## Task 6: Chart Components

**Files:**
- Create: `theme-pm/components/charts/LineChart.vue`
- Create: `theme-pm/components/charts/PieChart.vue`
- Create: `theme-pm/components/charts/BarChart.vue`
- Create: `theme-pm/components/dashboard/StatCard.vue`

- [ ] **Step 1: Copy chart components from theme-a**

Copy these files verbatim from theme-a — they are generic and reusable:
- `theme-a/components/charts/LineChart.vue` → `theme-pm/components/charts/LineChart.vue`
- `theme-a/components/charts/PieChart.vue` → `theme-pm/components/charts/PieChart.vue`
- `theme-a/components/charts/BarChart.vue` → `theme-pm/components/charts/BarChart.vue`
- `theme-a/components/dashboard/StatCard.vue` → `theme-pm/components/dashboard/StatCard.vue`

- [ ] **Step 2: Commit**

```bash
git add theme-pm/components/charts/ theme-pm/components/dashboard/
git commit -m "feat(theme-pm): add chart and stat card components (from theme-a)"
```

---

## Task 7: Mock Data

**Files:**
- Create: `theme-pm/data/mock.ts`

This is the largest single file. It contains all mock data per the spec.

- [ ] **Step 1: Create mock.ts with users, projects, and issue data**

```typescript
// ===== Users =====
export const users = [
  { id: 'u1', name: '张三', email: 'zhangsan@company.com', github_id: 'zhangsan-dev', role: '管理员', avatar: '' },
  { id: 'u2', name: '李四', email: 'lisi@company.com', github_id: 'lisi-dev', role: '开发者', avatar: '' },
  { id: 'u3', name: '王五', email: 'wangwu@company.com', github_id: 'wangwu-dev', role: '开发者', avatar: '' },
  { id: 'u4', name: '赵六', email: 'zhaoliu@company.com', github_id: 'zhaoliu-dev', role: '开发者', avatar: '' },
  { id: 'u5', name: '孙七', email: 'sunqi@company.com', github_id: 'sunqi-dev', role: '测试', avatar: '' },
  { id: 'u6', name: '周八', email: 'zhouba@company.com', github_id: 'zhouba-dev', role: '开发者', avatar: '' },
  { id: 'u7', name: '吴九', email: 'wujiu@company.com', github_id: 'wujiu-dev', role: '前端开发', avatar: '' },
  { id: 'u8', name: '郑十', email: 'zhengshi@company.com', github_id: 'zhengshi-dev', role: '后端开发', avatar: '' },
  { id: 'u9', name: '陈明', email: 'chenming@company.com', github_id: 'chenming-dev', role: '开发者', avatar: '' },
  { id: 'u10', name: '林芳', email: 'linfang@company.com', github_id: 'linfang-dev', role: '产品经理', avatar: '' },
]

// ===== Projects =====
export const projects = [
  {
    id: 'p1',
    name: '贷后智能体平台',
    description: '基于 AI 的贷后管理系统，包含智能外呼、策略引擎等模块',
    status: '进行中',
    created_at: '2026-01-15T09:00:00Z',
    updated_at: '2026-03-20T10:00:00Z',
    linked_repos: ['r1'],
    members: [
      { user_id: 'u1', role: 'owner' },
      { user_id: 'u2', role: 'admin' },
      { user_id: 'u3', role: 'member' },
      { user_id: 'u4', role: 'member' },
      { user_id: 'u5', role: 'member' },
      { user_id: 'u7', role: 'member' },
      { user_id: 'u8', role: 'member' },
    ],
  },
  {
    id: 'p2',
    name: 'DevTrack 项目管理工具',
    description: '内部开发团队使用的项目管理和问题追踪工具',
    status: '进行中',
    created_at: '2026-02-01T09:00:00Z',
    updated_at: '2026-03-19T14:00:00Z',
    linked_repos: ['r2'],
    members: [
      { user_id: 'u1', role: 'owner' },
      { user_id: 'u7', role: 'admin' },
      { user_id: 'u9', role: 'member' },
      { user_id: 'u10', role: 'member' },
    ],
  },
  {
    id: 'p3',
    name: '数据分析平台 v2',
    description: '数据可视化和报表系统重构',
    status: '已完成',
    created_at: '2025-09-01T09:00:00Z',
    updated_at: '2026-02-28T18:00:00Z',
    linked_repos: ['r1', 'r2'],
    members: [
      { user_id: 'u2', role: 'owner' },
      { user_id: 'u6', role: 'member' },
      { user_id: 'u8', role: 'member' },
    ],
  },
]

// ===== Labels =====
export const labelOptions = ['前端', '后端', 'Bug', '优化', '需求', '文档', 'CI/CD', '安全', '性能', 'UI/UX']

// ===== Issues (50+) =====
const issueTemplates = [
  { title: '执行完成后偶发未外呼', labels: ['Bug', '后端'], cause: '批次外呼任务异步执行时序问题', solution: '增加任务状态校验和重试机制' },
  { title: '外呼内容与策略选择无挂钩', labels: ['Bug', '后端'], cause: '话术与策略关联逻辑缺失', solution: '增加策略-话术映射配置' },
  { title: '上传案件表格信息无关', labels: ['Bug', '前端'], cause: '仅姓名有关联，其他字段未映射', solution: '完善字段映射逻辑' },
  { title: 'AI 均通时有概率叫错名字', labels: ['Bug', '后端', '性能'], cause: '模型调用时的参数传递问题', solution: '修复参数传递和名称校验' },
  { title: '音色为默认音色（非录制音色）', labels: ['Bug', '后端'], cause: '调用API时的默认音色非克隆音', solution: '配置默认音色为克隆音色ID' },
  { title: 'AI 第一句不像真人', labels: ['优化', '后端'], cause: '开场白内容过长，缩短后效果有提升', solution: '优化开场白生成策略' },
  { title: '闪信功能：不同单位及单账号可配置', labels: ['需求', '后端'], cause: '', solution: '已实现闪信功能，支持多单位配置' },
  { title: '短信模板配置与内容配置完善', labels: ['需求', '前端', '后端'], cause: '', solution: '等待AI策略功能完成后集成' },
  { title: '文书生成→转链接→写入短信变量', labels: ['需求', '后端'], cause: '', solution: '引入已开发的功能模块' },
  { title: '呼入语音：需考虑呼入案件对应', labels: ['需求', '后端'], cause: '', solution: '实现用户回拨和呼入功能，根据用户号码匹配' },
  { title: '策略执行间隔时间、执行时间完善', labels: ['Bug', '后端'], cause: '定时任务间隔不精确', solution: '优化调度器时间精度' },
  { title: '批次完成后电话触发时间过久', labels: ['Bug', '后端'], cause: '可能与偶发未外呼相关', solution: '排查任务队列延迟' },
  { title: '用户仪表盘及单次策略作业数据完善', labels: ['需求', '前端'], cause: '', solution: '已完成等待验收' },
  { title: '前端交互设计优化', labels: ['优化', 'UI/UX', '前端'], cause: '', solution: '已转交设计评审' },
  { title: '策略匹配条件优化', labels: ['优化', '后端'], cause: '条件匹配不够精细', solution: '已优化，策略匹配更精确' },
  { title: '多个案件编号重量，导致案件详情页显示相同', labels: ['Bug', '前端'], cause: '没有去重机制', solution: '已优化去重逻辑' },
  { title: '缺少角色管理页面', labels: ['需求', '前端'], cause: '', solution: '参考外呼智能体平台实现' },
  { title: '打断机制太敏感', labels: ['Bug', '后端'], cause: '环境音/公告导致频繁打断', solution: '打断参数设置较低，已优化完成' },
  { title: '延迟不正常（偶发约2s回复）', labels: ['Bug', '后端', '性能'], cause: '需要排查请求日志', solution: '排查中' },
  { title: '系统整体功能不完整，页面功能偏少', labels: ['需求', '前端'], cause: '需要增加接口或功能', solution: '已将前端分离出来方便落实需求' },
  { title: '意图识别不准', labels: ['Bug', '后端'], cause: '意图分析识别模式不够精确', solution: '已引入LLM实时分析，准确率大幅提升' },
  { title: 'API调用外呼接口时信息冲突', labels: ['Bug', '后端'], cause: '同时内外部调用API', solution: '实现用户信息隔离，API独立两套流程' },
  { title: '实时外呼通话时无法快速调用RAG', labels: ['优化', '后端', '性能'], cause: '语音模型不支持 Function Calling', solution: '升级为三通道注入架构' },
  { title: 'SKILL层的话术知识库内容不足', labels: ['优化', '后端'], cause: '专业领域知识覆盖不足', solution: '添加金融贷后领域14个术语库和26部法律法规' },
  { title: '贷后智能体策略智能化生成', labels: ['需求', '后端'], cause: '', solution: '已完成方案设计和开发' },
  { title: '登录页面样式调整', labels: ['优化', 'UI/UX', '前端'], cause: '', solution: '对齐设计稿' },
  { title: 'Docker 部署脚本优化', labels: ['优化', 'CI/CD'], cause: '镜像体积过大', solution: '使用多阶段构建减小镜像' },
  { title: '数据库索引缺失导致查询慢', labels: ['Bug', '后端', '性能'], cause: '高频查询字段未建索引', solution: '添加复合索引' },
  { title: '用户权限校验不完整', labels: ['Bug', '安全', '后端'], cause: '部分API缺少权限中间件', solution: '统一添加权限装饰器' },
  { title: 'WebSocket 连接偶发断开', labels: ['Bug', '后端'], cause: '心跳机制不完善', solution: '增加自动重连和心跳检测' },
]

const priorities = ['P0', 'P1', 'P2', 'P3'] as const
const statuses = ['待处理', '进行中', '已解决', '已关闭'] as const
const assignees = ['u1', 'u2', 'u3', 'u4', 'u5', 'u6', 'u7', 'u8', 'u9', 'u10']
const reporters = ['u1', 'u2', 'u5', 'u10']

function randomFrom<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function generateIssues() {
  const result = []
  for (let i = 0; i < issueTemplates.length; i++) {
    const t = issueTemplates[i]
    const status = randomFrom(statuses)
    const priority = randomFrom(priorities)
    const assignee = randomFrom(assignees)
    const reporter = randomFrom(reporters)
    const projectId = i < 20 ? 'p1' : i < 25 ? 'p2' : randomFrom(['p1', 'p2', 'p3'])
    const createdDate = new Date(2026, 2, Math.floor(Math.random() * 20) + 1)
    const resolved = status === '已解决' || status === '已关闭'
    const resolvedDate = resolved ? new Date(createdDate.getTime() + Math.random() * 7 * 86400000) : null
    const branchMerged = resolved && Math.random() > 0.3
    const branchCreated = resolved || status === '进行中' ? new Date(createdDate.getTime() + Math.random() * 86400000) : null

    result.push({
      id: `ISS-${String(i + 1).padStart(3, '0')}`,
      project_id: projectId,
      title: t.title,
      description: `${t.title}的详细描述。该问题影响了系统的正常运行，需要尽快处理。`,
      priority,
      status,
      labels: t.labels,
      reporter,
      assignee,
      cause: t.cause,
      solution: t.solution,
      created_at: createdDate.toISOString(),
      resolved_at: resolvedDate?.toISOString() || null,
      resolution_hours: resolvedDate ? Math.round((resolvedDate.getTime() - createdDate.getTime()) / 3600000) : null,
      branch_name: branchCreated ? `fix/iss-${i + 1}-${t.title.slice(0, 10).replace(/\s/g, '-')}` : null,
      branch_created_at: branchCreated?.toISOString() || null,
      branch_merged_at: branchMerged ? new Date(branchCreated!.getTime() + Math.random() * 5 * 86400000).toISOString() : null,
      linked_commits: resolved ? [`abc${String(i).padStart(4, '0')}`, `def${String(i).padStart(4, '0')}`] : [],
      linked_prs: resolved ? [100 + i] : [],
      ai_analysis: Math.random() > 0.3 ? {
        suggested_priority: randomFrom(priorities),
        suggested_labels: t.labels.slice(0, 2),
        resolution_hints: [
          `建议检查${t.labels[0]}相关模块`,
          '可以参考类似问题的解决方案',
          '建议进行回归测试确认修复效果',
        ],
        related_files: [
          `src/${t.labels.includes('前端') ? 'components' : 'services'}/${t.title.slice(0, 6)}.${t.labels.includes('前端') ? 'vue' : 'py'}`,
          `tests/test_${t.title.slice(0, 6)}.py`,
        ],
      } : null,
    })
  }
  // Pad to 50+ with generated issues
  for (let i = issueTemplates.length; i < 55; i++) {
    const status = randomFrom(statuses)
    const resolved = status === '已解决' || status === '已关闭'
    const createdDate = new Date(2026, 2, Math.floor(Math.random() * 20) + 1)
    const resolvedDate = resolved ? new Date(createdDate.getTime() + Math.random() * 7 * 86400000) : null
    result.push({
      id: `ISS-${String(i + 1).padStart(3, '0')}`,
      project_id: randomFrom(['p1', 'p2', 'p3']),
      title: `系统优化任务 #${i + 1}`,
      description: `常规优化任务，需要处理相关模块的性能和稳定性问题。`,
      priority: randomFrom(priorities),
      status,
      labels: [randomFrom(labelOptions), randomFrom(labelOptions)],
      reporter: randomFrom(reporters),
      assignee: randomFrom(assignees),
      cause: '',
      solution: resolved ? '已修复' : '',
      created_at: createdDate.toISOString(),
      resolved_at: resolvedDate?.toISOString() || null,
      resolution_hours: resolvedDate ? Math.round((resolvedDate.getTime() - createdDate.getTime()) / 3600000) : null,
      branch_name: null,
      branch_created_at: null,
      branch_merged_at: null,
      linked_commits: [],
      linked_prs: [],
      ai_analysis: null,
    })
  }
  return result
}

export const issues = generateIssues()

// ===== GitHub Repos =====
export const repos = [
  {
    id: 'r1',
    name: 'postloan-backend',
    full_name: 'matrix/postloan-backend',
    url: 'https://github.com/matrix/postloan-backend',
    description: '贷后智能体平台后端服务',
    default_branch: 'main',
    language: 'Python',
    stars: 12,
    connected_at: '2026-01-20T10:00:00Z',
    status: '在线',
    recent_commits: [
      { sha: 'a1b2c3d', message: 'feat: add strategy execution engine', author: 'zhangsan-dev', date: '2026-03-20T09:30:00Z' },
      { sha: 'e4f5g6h', message: 'fix: resolve call record duplication', author: 'lisi-dev', date: '2026-03-19T16:45:00Z' },
      { sha: 'i7j8k9l', message: 'refactor: optimize database queries', author: 'wangwu-dev', date: '2026-03-19T14:20:00Z' },
      { sha: 'm0n1o2p', message: 'docs: update API documentation', author: 'zhangsan-dev', date: '2026-03-18T11:00:00Z' },
      { sha: 'q3r4s5t', message: 'fix: handle edge case in SMS template', author: 'zhaoliu-dev', date: '2026-03-18T09:15:00Z' },
      { sha: 'u6v7w8x', message: 'feat: add RAG knowledge base integration', author: 'lisi-dev', date: '2026-03-17T15:30:00Z' },
      { sha: 'y9z0a1b', message: 'test: add unit tests for call module', author: 'sunqi-dev', date: '2026-03-17T10:00:00Z' },
      { sha: 'c2d3e4f', message: 'chore: upgrade dependencies', author: 'wangwu-dev', date: '2026-03-16T14:00:00Z' },
    ],
    open_prs: [
      { number: 142, title: 'feat: implement voice cloning API', author: 'lisi-dev', status: 'open', created_at: '2026-03-20T08:00:00Z' },
      { number: 140, title: 'fix: resolve concurrent call conflict', author: 'wangwu-dev', status: 'open', created_at: '2026-03-19T10:00:00Z' },
      { number: 138, title: 'refactor: split strategy module', author: 'zhangsan-dev', status: 'open', created_at: '2026-03-18T09:00:00Z' },
    ],
    open_issues: [
      { number: 89, title: 'Memory leak in WebSocket handler', author: 'sunqi-dev', status: 'open', labels: ['bug', 'priority:high'], created_at: '2026-03-19T11:00:00Z' },
      { number: 87, title: 'Add rate limiting for external APIs', author: 'zhangsan-dev', status: 'open', labels: ['enhancement'], created_at: '2026-03-18T14:00:00Z' },
    ],
  },
  {
    id: 'r2',
    name: 'postloan-frontend',
    full_name: 'matrix/postloan-frontend',
    url: 'https://github.com/matrix/postloan-frontend',
    description: '贷后智能体平台前端应用',
    default_branch: 'main',
    language: 'TypeScript',
    stars: 5,
    connected_at: '2026-01-20T10:05:00Z',
    status: '在线',
    recent_commits: [
      { sha: 'f1g2h3i', message: 'feat: add theme-pm scaffold', author: 'wujiu-dev', date: '2026-03-20T10:00:00Z' },
      { sha: 'j4k5l6m', message: 'fix: resolve runtime errors across themes', author: 'wujiu-dev', date: '2026-03-19T12:00:00Z' },
      { sha: 'n7o8p9q', message: 'feat: add single-port showcase server', author: 'chenming-dev', date: '2026-03-18T16:00:00Z' },
      { sha: 'r0s1t2u', message: 'feat: add Theme C complete', author: 'wujiu-dev', date: '2026-03-17T11:00:00Z' },
      { sha: 'v3w4x5y', message: 'feat: add Theme B complete', author: 'chenming-dev', date: '2026-03-16T15:00:00Z' },
    ],
    open_prs: [
      { number: 28, title: 'feat: implement theme-pm project management tool', author: 'wujiu-dev', status: 'open', created_at: '2026-03-20T09:00:00Z' },
    ],
    open_issues: [
      { number: 15, title: 'Mobile responsive issues on dashboard', author: 'linfang-dev', status: 'open', labels: ['bug', 'UI'], created_at: '2026-03-19T09:00:00Z' },
    ],
  },
]

// ===== Dashboard Stats =====
export const dashboardStats = {
  total_issues: issues.length,
  pending_issues: issues.filter(i => i.status === '待处理').length,
  in_progress_issues: issues.filter(i => i.status === '进行中').length,
  resolved_this_week: issues.filter(i => {
    if (!i.resolved_at) return false
    const resolved = new Date(i.resolved_at)
    const weekAgo = new Date(2026, 2, 14)
    return resolved >= weekAgo
  }).length,
}

// ===== 30-day Issue Trends =====
export const dailyTrends = Array.from({ length: 30 }, (_, i) => {
  const d = new Date(2026, 2, 20)
  d.setDate(d.getDate() - 29 + i)
  return {
    date: d.toISOString().slice(0, 10),
    created: Math.floor(Math.random() * 6 + 1),
    resolved: Math.floor(Math.random() * 5 + 1),
  }
})

// ===== Priority Distribution =====
export const priorityDistribution = [
  { name: 'P0', value: issues.filter(i => i.priority === 'P0').length },
  { name: 'P1', value: issues.filter(i => i.priority === 'P1').length },
  { name: 'P2', value: issues.filter(i => i.priority === 'P2').length },
  { name: 'P3', value: issues.filter(i => i.priority === 'P3').length },
]

// ===== Developer Stats =====
export const developerStats = users
  .filter(u => ['开发者', '前端开发', '后端开发'].includes(u.role))
  .map(u => {
    const userIssues = issues.filter(i => i.assignee === u.id)
    const resolved = userIssues.filter(i => i.status === '已解决' || i.status === '已关闭')
    const withBranch = resolved.filter(i => i.branch_merged_at && i.branch_created_at)
    const avgHours = withBranch.length > 0
      ? Math.round(withBranch.reduce((sum, i) => sum + (new Date(i.branch_merged_at!).getTime() - new Date(i.branch_created_at!).getTime()) / 3600000, 0) / withBranch.length)
      : null
    return {
      user_id: u.id,
      user_name: u.name,
      project_id: 'p1',
      avg_resolution_hours: avgHours,
      monthly_resolved_count: resolved.length,
      priority_distribution: {
        P0: resolved.filter(i => i.priority === 'P0').length,
        P1: resolved.filter(i => i.priority === 'P1').length,
        P2: resolved.filter(i => i.priority === 'P2').length,
        P3: resolved.filter(i => i.priority === 'P3').length,
      },
      resolution_trend: [
        { month: '2026-01', count: Math.floor(Math.random() * 8 + 2) },
        { month: '2026-02', count: Math.floor(Math.random() * 10 + 3) },
        { month: '2026-03', count: resolved.length },
      ],
    }
  })

// ===== AI Insights =====
export const aiInsights = {
  project_id: 'p1',
  generated_at: '2026-03-20T08:00:00Z',
  team_efficiency: {
    avg_resolution_trend: [
      { month: '2026-01', hours: 52 },
      { month: '2026-02', hours: 45 },
      { month: '2026-03', hours: 38 },
    ],
    per_person_output: developerStats.map(d => ({
      name: d.user_name,
      count: d.monthly_resolved_count,
    })),
  },
  bottlenecks: [
    { type: 'assignee' as const, name: '李四', pending_count: 8 },
    { type: 'assignee' as const, name: '王五', pending_count: 6 },
    { type: 'label' as const, name: '后端', pending_count: 15 },
    { type: 'label' as const, name: '性能', pending_count: 7 },
  ],
  trend_alerts: [
    { message: 'P0 问题本周新增 3 个，较上周增长 200%', severity: 'critical' as const, metric: 'P0 新增', change_pct: 200 },
    { message: '后端 Bug 积压量持续增加，建议增加人手', severity: 'warning' as const, metric: '后端积压', change_pct: 45 },
    { message: '平均解决时间持续下降，团队效率提升', severity: 'warning' as const, metric: '解决速度', change_pct: -15 },
  ],
  recommendations: [
    '建议将 P0 问题分配给经验丰富的开发者优先处理',
    '后端标签下积压问题较多，建议进行代码审查找出系统性问题',
    '李四当前积压 8 个问题，建议重新分配部分任务',
    '性能类问题建议集中处理，安排专项优化迭代',
  ],
}

// ===== Recent Activity =====
export const recentActivity = [
  { id: 1, icon: 'i-heroicons-plus-circle', message: '张三 创建了问题 ISS-025「贷后智能体策略智能化生成」', time: '10 分钟前' },
  { id: 2, icon: 'i-heroicons-check-circle', message: '李四 解决了问题 ISS-005「音色为默认音色」', time: '30 分钟前' },
  { id: 3, icon: 'i-heroicons-code-bracket', message: '王五 关联了 PR #142 到 ISS-010', time: '1 小时前' },
  { id: 4, icon: 'i-heroicons-arrow-path', message: '赵六 将 ISS-018「打断机制太敏感」状态改为已解决', time: '2 小时前' },
  { id: 5, icon: 'i-heroicons-cpu-chip', message: 'AI 分析完成：ISS-023「实时外呼通话调用RAG」建议优先级 P1', time: '3 小时前' },
  { id: 6, icon: 'i-heroicons-user-plus', message: '张三 将 ISS-012 分配给 孙七', time: '4 小时前' },
  { id: 7, icon: 'i-heroicons-flag', message: '林芳 将 ISS-001 优先级调整为 P0', time: '5 小时前' },
  { id: 8, icon: 'i-heroicons-code-bracket', message: '吴九 为 ISS-016 创建了分支 fix/iss-16-缺少角色管理', time: '6 小时前' },
]

// Helper: get user name by id
export function getUserName(id: string): string {
  return users.find(u => u.id === id)?.name ?? id
}
```

- [ ] **Step 2: Commit**

```bash
git add theme-pm/data/
git commit -m "feat(theme-pm): add comprehensive mock data (users, projects, issues, repos, AI insights)"
```

---

## Task 8: Login Page

**Files:**
- Create: `theme-pm/pages/index.vue`

- [ ] **Step 1: Create login page**

Based on theme-a's `pages/login.vue` pattern, adapted for DevTrack:

```vue
<template>
  <div class="w-full max-w-sm">
    <div class="text-center mb-8">
      <div class="w-14 h-14 rounded-2xl bg-crystal-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-crystal-200">
        <span class="text-white font-bold text-2xl">D</span>
      </div>
      <h1 class="text-2xl font-semibold text-gray-900">DevTrack</h1>
      <p class="text-sm text-gray-400 mt-1">项目管理平台</p>
    </div>

    <div class="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8">
      <h2 class="text-lg font-semibold text-gray-900 mb-6">登录</h2>
      <div class="space-y-4">
        <UFormGroup label="用户名">
          <UInput v-model="username" placeholder="请输入用户名" icon="i-heroicons-user" size="lg" />
        </UFormGroup>
        <UFormGroup label="密码">
          <UInput v-model="password" type="password" placeholder="请输入密码" icon="i-heroicons-lock-closed" size="lg" />
        </UFormGroup>
        <UButton block size="lg" color="violet" @click="handleLogin">登录</UButton>
      </div>
    </div>

    <p class="text-center text-xs text-gray-400 mt-6">&copy; 2026 DevTrack 项目管理平台</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })
const username = ref('admin')
const password = ref('')
async function handleLogin() { await navigateTo('/app/dashboard') }
</script>
```

- [ ] **Step 2: Verify login page renders**

```bash
cd theme-pm && npm run dev
```

Open `http://localhost:3004/theme-pm/` — should see the login form with "DevTrack" branding.

- [ ] **Step 3: Commit**

```bash
git add theme-pm/pages/index.vue
git commit -m "feat(theme-pm): add login page"
```

---

## Task 9: Dashboard Page

**Files:**
- Create: `theme-pm/pages/app/dashboard.vue`

- [ ] **Step 1: Create dashboard page**

4 stat cards, trend line chart (created vs resolved), priority pie chart, developer leaderboard, recent activity.

```vue
<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-semibold text-gray-900">项目概览</h1>

    <!-- Stat Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <DashboardStatCard label="总 Issue 数" :value="stats.total_issues" icon="i-heroicons-bug-ant" icon-bg="bg-crystal-50" icon-color="text-crystal-500" />
      <DashboardStatCard label="待处理" :value="stats.pending_issues" icon="i-heroicons-clock" icon-bg="bg-amber-50" icon-color="text-amber-500" />
      <DashboardStatCard label="进行中" :value="stats.in_progress_issues" icon="i-heroicons-arrow-path" icon-bg="bg-blue-50" icon-color="text-blue-500" />
      <DashboardStatCard label="本周已解决" :value="stats.resolved_this_week" icon="i-heroicons-check-circle" icon-bg="bg-emerald-50" icon-color="text-emerald-500" />
    </div>

    <!-- Charts -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">30 日 Issue 趋势</h3>
        <ChartsLineChart
          :x-data="trendDates"
          :series="[
            { name: '新增', data: trendCreated },
            { name: '解决', data: trendResolved },
          ]"
          :height="280"
        />
      </div>
      <div class="bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">优先级分布</h3>
        <ChartsPieChart :data="priorityDistribution" :height="280" />
      </div>
    </div>

    <!-- Developer Leaderboard -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-4">开发者排行榜（本月解决数）</h3>
      <div class="space-y-3">
        <div v-for="(dev, idx) in topDevs" :key="dev.user_id" class="flex items-center">
          <span class="w-6 text-sm font-medium" :class="idx < 3 ? 'text-crystal-500' : 'text-gray-400'">{{ idx + 1 }}</span>
          <div class="w-8 h-8 rounded-full bg-crystal-100 flex items-center justify-center ml-2">
            <span class="text-crystal-600 text-xs font-medium">{{ dev.user_name.slice(0, 1) }}</span>
          </div>
          <span class="ml-3 text-sm text-gray-700 flex-1">{{ dev.user_name }}</span>
          <span class="text-sm font-semibold text-gray-900">{{ dev.monthly_resolved_count }}</span>
        </div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-4">最近动态</h3>
      <div class="divide-y divide-gray-50">
        <div v-for="item in recentActivity" :key="item.id" class="flex items-center py-3 first:pt-0 last:pb-0">
          <div class="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0">
            <UIcon :name="item.icon" class="w-4 h-4 text-gray-400" />
          </div>
          <span class="ml-3 text-sm text-gray-700 flex-1">{{ item.message }}</span>
          <span class="text-xs text-gray-400 ml-4 whitespace-nowrap">{{ item.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { dashboardStats, dailyTrends, priorityDistribution, developerStats, recentActivity } from '~/data/mock'

const stats = dashboardStats
const trendDates = dailyTrends.map(d => d.date.slice(5))
const trendCreated = dailyTrends.map(d => d.created)
const trendResolved = dailyTrends.map(d => d.resolved)
const topDevs = [...developerStats].sort((a, b) => b.monthly_resolved_count - a.monthly_resolved_count).slice(0, 5)
</script>
```

- [ ] **Step 2: Verify dashboard renders**

Navigate to dashboard after login — should see stat cards, charts, leaderboard, and activity feed.

- [ ] **Step 3: Commit**

```bash
git add theme-pm/pages/app/dashboard.vue
git commit -m "feat(theme-pm): add dashboard page with stats, charts, leaderboard, activity"
```

---

## Task 10: Project List & Detail (Kanban) Pages

**Files:**
- Create: `theme-pm/pages/app/projects/index.vue`
- Create: `theme-pm/pages/app/projects/[id].vue`
- Create: `theme-pm/components/projects/KanbanBoard.vue`

- [ ] **Step 1: Create project list page**

Card grid showing 3 projects with name, description, status badge, member count, issue count.

```vue
<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-semibold text-gray-900">项目管理</h1>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <NuxtLink
        v-for="project in projects"
        :key="project.id"
        :to="`/app/projects/${project.id}`"
        class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-sm transition-shadow block"
      >
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold text-gray-900">{{ project.name }}</h3>
          <UBadge
            :color="project.status === '进行中' ? 'violet' : project.status === '已完成' ? 'green' : 'gray'"
            variant="subtle"
            size="xs"
          >
            {{ project.status }}
          </UBadge>
        </div>
        <p class="text-sm text-gray-500 mb-4 line-clamp-2">{{ project.description }}</p>
        <div class="flex items-center text-xs text-gray-400 space-x-4">
          <span class="flex items-center">
            <UIcon name="i-heroicons-users" class="w-3.5 h-3.5 mr-1" />
            {{ project.members.length }} 成员
          </span>
          <span class="flex items-center">
            <UIcon name="i-heroicons-bug-ant" class="w-3.5 h-3.5 mr-1" />
            {{ getProjectIssueCount(project.id) }} Issues
          </span>
          <span class="flex items-center">
            <UIcon name="i-heroicons-code-bracket" class="w-3.5 h-3.5 mr-1" />
            {{ project.linked_repos.length }} 仓库
          </span>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { projects, issues } from '~/data/mock'

function getProjectIssueCount(projectId: string) {
  return issues.filter(i => i.project_id === projectId).length
}
</script>
```

- [ ] **Step 2: Create KanbanBoard component**

Three-column static kanban:

```vue
<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div v-for="col in columns" :key="col.status" class="bg-gray-50 rounded-xl p-4">
      <div class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-semibold text-gray-700">{{ col.label }}</h4>
        <UBadge color="gray" variant="subtle" size="xs">{{ col.items.length }}</UBadge>
      </div>
      <div class="space-y-2">
        <NuxtLink
          v-for="issue in col.items"
          :key="issue.id"
          :to="`/app/issues/${issue.id}`"
          class="block bg-white rounded-lg border border-gray-100 p-3 hover:shadow-sm transition-shadow"
        >
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs text-gray-400">{{ issue.id }}</span>
            <UBadge
              :color="issue.priority === 'P0' ? 'red' : issue.priority === 'P1' ? 'orange' : issue.priority === 'P2' ? 'yellow' : 'gray'"
              variant="subtle"
              size="xs"
            >
              {{ issue.priority }}
            </UBadge>
          </div>
          <p class="text-sm text-gray-900 font-medium line-clamp-2">{{ issue.title }}</p>
          <div class="mt-2 flex items-center">
            <div class="w-5 h-5 rounded-full bg-crystal-100 flex items-center justify-center">
              <span class="text-crystal-600 text-[10px] font-medium">{{ getUserName(issue.assignee).slice(0, 1) }}</span>
            </div>
            <span class="ml-1.5 text-xs text-gray-400">{{ getUserName(issue.assignee) }}</span>
          </div>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getUserName } from '~/data/mock'

const props = defineProps<{
  issues: any[]
}>()

const columns = computed(() => [
  { status: '待处理', label: '待处理', items: props.issues.filter(i => i.status === '待处理') },
  { status: '进行中', label: '进行中', items: props.issues.filter(i => i.status === '进行中') },
  { status: '已解决', label: '已解决', items: props.issues.filter(i => i.status === '已解决') },
])
</script>
```

- [ ] **Step 3: Create project detail page**

Shows project info, members, and kanban view of its issues.

```vue
<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">{{ project?.name }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ project?.description }}</p>
      </div>
      <UBadge
        :color="project?.status === '进行中' ? 'violet' : project?.status === '已完成' ? 'green' : 'gray'"
        variant="subtle"
      >
        {{ project?.status }}
      </UBadge>
    </div>

    <!-- Members -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">项目成员</h3>
      <div class="flex flex-wrap gap-3">
        <div v-for="m in projectMembers" :key="m.user_id" class="flex items-center bg-gray-50 rounded-lg px-3 py-2">
          <div class="w-7 h-7 rounded-full bg-crystal-100 flex items-center justify-center">
            <span class="text-crystal-600 text-xs font-medium">{{ getUserName(m.user_id).slice(0, 1) }}</span>
          </div>
          <span class="ml-2 text-sm text-gray-700">{{ getUserName(m.user_id) }}</span>
          <UBadge class="ml-2" color="gray" variant="subtle" size="xs">{{ m.role }}</UBadge>
        </div>
      </div>
    </div>

    <!-- Kanban -->
    <div>
      <h3 class="text-sm font-semibold text-gray-900 mb-3">看板</h3>
      <ProjectsKanbanBoard :issues="projectIssues" />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { projects, issues, getUserName } from '~/data/mock'

const route = useRoute()
const project = computed(() => projects.find(p => p.id === route.params.id))
const projectMembers = computed(() => project.value?.members ?? [])
const projectIssues = computed(() => issues.filter(i => i.project_id === route.params.id && i.status !== '已关闭'))
</script>
```

- [ ] **Step 4: Verify project pages render**

Check project list loads, clicking a project shows detail with kanban.

- [ ] **Step 5: Commit**

```bash
git add theme-pm/pages/app/projects/ theme-pm/components/projects/
git commit -m "feat(theme-pm): add project list, detail, and kanban pages"
```

---

## Task 11: Issue List Page

**Files:**
- Create: `theme-pm/pages/app/issues/index.vue`

- [ ] **Step 1: Create issue list page**

Table with filters (priority, status, label, assignee), sorting, batch operations, pagination. Based on theme-a's `cases.vue` pattern.

**Note on sorting:** UTable's `sortable: true` uses string comparison by default. Priority (P0-P3) sorts correctly alphabetically since P0 < P1 < P2 < P3. Dates and numbers also sort acceptably as strings for a demo. No custom sort function needed.

```vue
<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">问题跟踪</h1>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl border border-gray-100 p-4">
      <div class="flex flex-wrap gap-3">
        <UInput v-model="search" placeholder="搜索标题/ID" icon="i-heroicons-magnifying-glass" size="sm" class="w-60" />
        <USelect v-model="filterPriority" :options="priorityOptions" placeholder="优先级" size="sm" class="w-28" />
        <USelect v-model="filterStatus" :options="statusOptions" placeholder="状态" size="sm" class="w-28" />
        <USelect v-model="filterLabel" :options="labelFilterOptions" placeholder="标签" size="sm" class="w-28" />
        <USelect v-model="filterAssignee" :options="assigneeOptions" placeholder="负责人" size="sm" class="w-32" />
      </div>
    </div>

    <!-- Batch Actions -->
    <div v-if="selectedRows.length > 0" class="bg-crystal-50 rounded-xl border border-crystal-100 p-3 flex items-center justify-between">
      <span class="text-sm text-crystal-700">已选择 {{ selectedRows.length }} 项</span>
      <div class="flex items-center space-x-2">
        <UDropdown :items="batchAssignItems" :popper="{ placement: 'bottom-end' }">
          <UButton size="xs" color="violet" variant="outline">批量分配</UButton>
        </UDropdown>
        <UDropdown :items="batchPriorityItems" :popper="{ placement: 'bottom-end' }">
          <UButton size="xs" color="violet" variant="outline">修改优先级</UButton>
        </UDropdown>
      </div>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
      <UTable
        v-model="selectedRows"
        :rows="paginatedIssues"
        :columns="columns"
        :ui="{ th: { base: 'text-xs' }, td: { base: 'text-sm' } }"
      >
        <template #id-data="{ row }">
          <NuxtLink :to="`/app/issues/${row.id}`" class="text-crystal-500 hover:text-crystal-700 font-medium">{{ row.id }}</NuxtLink>
        </template>
        <template #title-data="{ row }">
          <NuxtLink :to="`/app/issues/${row.id}`" class="text-gray-900 hover:text-crystal-600 line-clamp-1">{{ row.title }}</NuxtLink>
        </template>
        <template #priority-data="{ row }">
          <UBadge :color="priorityColor(row.priority)" variant="subtle" size="xs">{{ row.priority }}</UBadge>
        </template>
        <template #status-data="{ row }">
          <UBadge :color="statusColor(row.status)" variant="subtle" size="xs">{{ row.status }}</UBadge>
        </template>
        <template #assignee-data="{ row }">
          {{ getUserName(row.assignee) }}
        </template>
        <template #reporter-data="{ row }">
          {{ getUserName(row.reporter) }}
        </template>
        <template #created_at-data="{ row }">
          {{ row.created_at.slice(0, 10) }}
        </template>
        <template #resolution_hours-data="{ row }">
          {{ row.resolution_hours ? row.resolution_hours + 'h' : '-' }}
        </template>
      </UTable>
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50">
        <span class="text-xs text-gray-400">共 {{ filteredIssues.length }} 条</span>
        <div class="flex items-center space-x-2">
          <UButton size="xs" variant="ghost" color="gray" :disabled="page <= 1" @click="page--">上一页</UButton>
          <span class="text-xs text-gray-500">{{ page }} / {{ totalPages }}</span>
          <UButton size="xs" variant="ghost" color="gray" :disabled="page >= totalPages" @click="page++">下一页</UButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { issues, users, labelOptions, getUserName } from '~/data/mock'

const search = ref('')
const filterPriority = ref('')
const filterStatus = ref('')
const filterLabel = ref('')
const filterAssignee = ref('')
const page = ref(1)
const pageSize = 15
const selectedRows = ref<any[]>([])

const priorityOptions = [{ label: '全部', value: '' }, { label: 'P0', value: 'P0' }, { label: 'P1', value: 'P1' }, { label: 'P2', value: 'P2' }, { label: 'P3', value: 'P3' }]
const statusOptions = [{ label: '全部', value: '' }, { label: '待处理', value: '待处理' }, { label: '进行中', value: '进行中' }, { label: '已解决', value: '已解决' }, { label: '已关闭', value: '已关闭' }]
const labelFilterOptions = [{ label: '全部', value: '' }, ...labelOptions.map(l => ({ label: l, value: l }))]
const assigneeOptions = [{ label: '全部', value: '' }, ...users.map(u => ({ label: u.name, value: u.id }))]

const columns = [
  { key: 'id', label: 'ID', sortable: true },
  { key: 'title', label: '标题' },
  { key: 'priority', label: '优先级', sortable: true },
  { key: 'status', label: '状态' },
  { key: 'assignee', label: '负责人' },
  { key: 'reporter', label: '提出人' },
  { key: 'created_at', label: '创建时间', sortable: true },
  { key: 'resolution_hours', label: '解决耗时', sortable: true },
]

function priorityColor(p: string) {
  return p === 'P0' ? 'red' : p === 'P1' ? 'orange' : p === 'P2' ? 'yellow' : 'gray'
}
function statusColor(s: string) {
  return s === '待处理' ? 'amber' : s === '进行中' ? 'blue' : s === '已解决' ? 'green' : 'gray'
}

const filteredIssues = computed(() => {
  return issues.filter(i => {
    if (search.value && !i.title.includes(search.value) && !i.id.includes(search.value)) return false
    if (filterPriority.value && i.priority !== filterPriority.value) return false
    if (filterStatus.value && i.status !== filterStatus.value) return false
    if (filterLabel.value && !i.labels.includes(filterLabel.value)) return false
    if (filterAssignee.value && i.assignee !== filterAssignee.value) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredIssues.value.length / pageSize)))
const paginatedIssues = computed(() => filteredIssues.value.slice((page.value - 1) * pageSize, page.value * pageSize))

watch([filterPriority, filterStatus, filterLabel, filterAssignee, search], () => { page.value = 1 })

// Batch operations (mock: mutate in-memory data)
const batchAssignItems = [users.map(u => ({
  label: u.name,
  click: () => { selectedRows.value.forEach(row => { row.assignee = u.id }); selectedRows.value = [] },
}))]

const batchPriorityItems = [['P0', 'P1', 'P2', 'P3'].map(p => ({
  label: p,
  click: () => { selectedRows.value.forEach(row => { row.priority = p }); selectedRows.value = [] },
}))]
</script>
```

- [ ] **Step 2: Verify issue list renders with filtering**

- [ ] **Step 3: Commit**

```bash
git add theme-pm/pages/app/issues/index.vue
git commit -m "feat(theme-pm): add issue list page with filters and pagination"
```

---

## Task 12: Issue Detail Page

**Files:**
- Create: `theme-pm/pages/app/issues/[id].vue`

- [ ] **Step 1: Create issue detail page**

Sections: basic info, action bar (create branch, status), GitHub association (with offline fallback), AI analysis (with offline fallback), timeline.

```vue
<template>
  <div v-if="issue" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <div class="flex items-center space-x-3">
          <h1 class="text-2xl font-semibold text-gray-900">{{ issue.id }}</h1>
          <UBadge :color="priorityColor(issue.priority)" variant="subtle">{{ issue.priority }}</UBadge>
          <UBadge :color="statusColor(issue.status)" variant="subtle">{{ issue.status }}</UBadge>
        </div>
        <p class="text-lg text-gray-700 mt-1">{{ issue.title }}</p>
      </div>
    </div>

    <!-- Action Bar -->
    <div class="flex items-center space-x-3">
      <UButton
        v-if="!issue.branch_name"
        color="violet"
        size="sm"
        icon="i-heroicons-code-bracket"
        @click="createBranch"
      >
        创建分支
      </UButton>
      <div v-else class="flex items-center bg-crystal-50 text-crystal-700 rounded-lg px-3 py-1.5 text-sm">
        <UIcon name="i-heroicons-code-bracket" class="w-4 h-4 mr-2" />
        {{ issue.branch_name }}
      </div>
      <UButton
        v-for="action in statusActions"
        :key="action.label"
        variant="outline"
        color="gray"
        size="sm"
        @click="action.handler"
      >
        {{ action.label }}
      </UButton>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main Content -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Description -->
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">问题描述</h3>
          <p class="text-sm text-gray-600 leading-relaxed">{{ issue.description }}</p>
        </div>

        <!-- AI Analysis -->
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-gray-900">AI 分析</h3>
            <ServiceStatusDot :online="isOnline('ai')" />
          </div>
          <template v-if="isOnline('ai') && issue.ai_analysis">
            <div class="space-y-3">
              <div>
                <span class="text-xs text-gray-400">建议优先级</span>
                <UBadge :color="priorityColor(issue.ai_analysis.suggested_priority)" variant="subtle" size="xs" class="ml-2">
                  {{ issue.ai_analysis.suggested_priority }}
                </UBadge>
              </div>
              <div>
                <span class="text-xs text-gray-400">建议标签</span>
                <div class="flex gap-1 mt-1">
                  <UBadge v-for="l in issue.ai_analysis.suggested_labels" :key="l" color="violet" variant="subtle" size="xs">{{ l }}</UBadge>
                </div>
              </div>
              <div>
                <span class="text-xs text-gray-400">解决建议</span>
                <ul class="mt-1 space-y-1">
                  <li v-for="h in issue.ai_analysis.resolution_hints" :key="h" class="text-sm text-gray-600 flex items-start">
                    <UIcon name="i-heroicons-light-bulb" class="w-4 h-4 text-amber-400 mr-1.5 mt-0.5 flex-shrink-0" />
                    {{ h }}
                  </li>
                </ul>
              </div>
              <div>
                <span class="text-xs text-gray-400">关联代码文件</span>
                <div class="mt-1 space-y-1">
                  <div v-for="f in issue.ai_analysis.related_files" :key="f" class="text-sm text-crystal-600 font-mono">{{ f }}</div>
                </div>
              </div>
            </div>
          </template>
          <div v-else-if="!isOnline('ai')" class="text-sm text-gray-400 flex items-center">
            <UIcon name="i-heroicons-exclamation-circle" class="w-4 h-4 mr-2" />
            AI 服务暂不可用
          </div>
          <div v-else class="text-sm text-gray-400">暂无 AI 分析结果</div>
        </div>

        <!-- GitHub Association -->
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-gray-900">GitHub 关联</h3>
            <ServiceStatusDot :online="isOnline('github')" />
          </div>
          <template v-if="isOnline('github')">
            <div v-if="issue.linked_commits.length || issue.linked_prs.length" class="space-y-3">
              <div v-if="issue.linked_prs.length">
                <span class="text-xs text-gray-400">关联 PR</span>
                <div class="mt-1 space-y-1">
                  <div v-for="pr in issue.linked_prs" :key="pr" class="text-sm text-crystal-600 flex items-center">
                    <UIcon name="i-heroicons-arrow-up-tray" class="w-4 h-4 mr-1.5" />
                    PR #{{ pr }}
                  </div>
                </div>
              </div>
              <div v-if="issue.linked_commits.length">
                <span class="text-xs text-gray-400">关联 Commit</span>
                <div class="mt-1 space-y-1">
                  <div v-for="sha in issue.linked_commits" :key="sha" class="text-sm text-gray-600 font-mono">{{ sha }}</div>
                </div>
              </div>
            </div>
            <div v-else class="text-sm text-gray-400">暂无关联的 GitHub 记录</div>
          </template>
          <div v-else class="text-sm text-gray-400 flex items-center">
            <UIcon name="i-heroicons-exclamation-circle" class="w-4 h-4 mr-2" />
            GitHub 连接不可用
          </div>
        </div>

        <!-- Timeline -->
        <div v-if="issue.cause || issue.solution" class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">分析记录</h3>
          <div class="space-y-3">
            <div v-if="issue.cause">
              <span class="text-xs text-gray-400">原因分析</span>
              <p class="text-sm text-gray-600 mt-1">{{ issue.cause }}</p>
            </div>
            <div v-if="issue.solution">
              <span class="text-xs text-gray-400">解决办法</span>
              <p class="text-sm text-gray-600 mt-1">{{ issue.solution }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
          <div>
            <span class="text-xs text-gray-400">负责人</span>
            <p class="text-sm text-gray-900 mt-0.5">{{ getUserName(issue.assignee) }}</p>
          </div>
          <div>
            <span class="text-xs text-gray-400">提出人</span>
            <p class="text-sm text-gray-900 mt-0.5">{{ getUserName(issue.reporter) }}</p>
          </div>
          <div>
            <span class="text-xs text-gray-400">标签</span>
            <div class="flex flex-wrap gap-1 mt-1">
              <UBadge v-for="l in issue.labels" :key="l" color="gray" variant="subtle" size="xs">{{ l }}</UBadge>
            </div>
          </div>
          <div>
            <span class="text-xs text-gray-400">创建时间</span>
            <p class="text-sm text-gray-900 mt-0.5">{{ issue.created_at.slice(0, 10) }}</p>
          </div>
          <div v-if="issue.resolved_at">
            <span class="text-xs text-gray-400">解决时间</span>
            <p class="text-sm text-gray-900 mt-0.5">{{ issue.resolved_at.slice(0, 10) }}</p>
          </div>
          <div v-if="issue.resolution_hours">
            <span class="text-xs text-gray-400">解决耗时</span>
            <p class="text-sm text-gray-900 mt-0.5">{{ issue.resolution_hours }} 小时</p>
          </div>
          <div v-if="issue.branch_merged_at">
            <span class="text-xs text-gray-400">分支合并时间</span>
            <p class="text-sm text-gray-900 mt-0.5">{{ issue.branch_merged_at.slice(0, 10) }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { issues, getUserName } from '~/data/mock'

const route = useRoute()
const { isOnline } = useServiceStatus()

const issue = computed(() => issues.find(i => i.id === route.params.id))

function priorityColor(p: string) {
  return p === 'P0' ? 'red' : p === 'P1' ? 'orange' : p === 'P2' ? 'yellow' : 'gray'
}
function statusColor(s: string) {
  return s === '待处理' ? 'amber' : s === '进行中' ? 'blue' : s === '已解决' ? 'green' : 'gray'
}

function createBranch() {
  if (!issue.value) return
  const slug = issue.value.title.slice(0, 15).replace(/\s+/g, '-')
  const num = issue.value.id.replace('ISS-', '')
  issue.value.branch_name = `fix/iss-${num}-${slug}`
  issue.value.branch_created_at = new Date().toISOString()
}

const statusActions = computed(() => {
  if (!issue.value) return []
  const s = issue.value.status
  const actions = []
  if (s === '待处理') actions.push({ label: '开始处理', handler: () => { issue.value!.status = '进行中' } })
  if (s === '进行中') actions.push({ label: '标记已解决', handler: () => { issue.value!.status = '已解决'; issue.value!.resolved_at = new Date().toISOString() } })
  if (s === '已解决') actions.push({ label: '关闭', handler: () => { issue.value!.status = '已关闭' } })
  return actions
})
</script>
```

- [ ] **Step 2: Verify issue detail renders**

Click an issue from the list — should see full detail with AI analysis, GitHub section, create branch button, and sidebar metadata.

- [ ] **Step 3: Commit**

```bash
git add theme-pm/pages/app/issues/
git commit -m "feat(theme-pm): add issue detail page with AI analysis, GitHub association, branch creation"
```

---

## Task 13: GitHub Repo Pages

**Files:**
- Create: `theme-pm/pages/app/repos/index.vue`
- Create: `theme-pm/pages/app/repos/[id].vue`

- [ ] **Step 1: Create repo list page**

```vue
<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">GitHub 仓库</h1>
      <ServiceStatusDot :online="isOnline('github')" />
    </div>

    <template v-if="isOnline('github')">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <NuxtLink
          v-for="repo in repos"
          :key="repo.id"
          :to="`/app/repos/${repo.id}`"
          class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-sm transition-shadow block"
        >
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-gray-900">{{ repo.full_name }}</h3>
            <UBadge :color="repo.status === '在线' ? 'green' : 'gray'" variant="subtle" size="xs">{{ repo.status }}</UBadge>
          </div>
          <p class="text-sm text-gray-500 mb-3">{{ repo.description }}</p>
          <div class="flex items-center text-xs text-gray-400 space-x-4">
            <span class="flex items-center">
              <UIcon name="i-heroicons-code-bracket" class="w-3.5 h-3.5 mr-1" />
              {{ repo.language }}
            </span>
            <span class="flex items-center">
              <UIcon name="i-heroicons-star" class="w-3.5 h-3.5 mr-1" />
              {{ repo.stars }}
            </span>
            <span>绑定于 {{ repo.connected_at.slice(0, 10) }}</span>
          </div>
        </NuxtLink>
      </div>
    </template>
    <div v-else class="bg-white rounded-xl border border-gray-100 p-12 text-center">
      <UIcon name="i-heroicons-exclamation-circle" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">GitHub 连接不可用</p>
      <p class="text-sm text-gray-400 mt-1">请检查 GitHub API 连接配置</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { repos } from '~/data/mock'
const { isOnline } = useServiceStatus()
</script>
```

- [ ] **Step 2: Create repo detail page**

```vue
<template>
  <div v-if="repo" class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">{{ repo.full_name }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ repo.description }}</p>
      </div>
      <div class="flex items-center space-x-3">
        <UBadge color="gray" variant="subtle">{{ repo.language }}</UBadge>
        <UBadge color="gray" variant="subtle">
          <UIcon name="i-heroicons-star" class="w-3 h-3 mr-1" />
          {{ repo.stars }}
        </UBadge>
      </div>
    </div>

    <!-- Recent Commits -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">最近提交</h3>
      <div class="divide-y divide-gray-50">
        <div v-for="commit in repo.recent_commits" :key="commit.sha" class="py-3 first:pt-0 last:pb-0">
          <div class="flex items-center justify-between">
            <p class="text-sm text-gray-900">{{ commit.message }}</p>
            <span class="text-xs text-gray-400 font-mono ml-4 flex-shrink-0">{{ commit.sha }}</span>
          </div>
          <div class="flex items-center mt-1 text-xs text-gray-400 space-x-3">
            <span>{{ commit.author }}</span>
            <span>{{ commit.date.slice(0, 10) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Open PRs -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">Open Pull Requests ({{ repo.open_prs.length }})</h3>
      <div v-if="repo.open_prs.length" class="divide-y divide-gray-50">
        <div v-for="pr in repo.open_prs" :key="pr.number" class="py-3 first:pt-0 last:pb-0 flex items-center justify-between">
          <div>
            <span class="text-sm text-crystal-600 font-medium">#{{ pr.number }}</span>
            <span class="text-sm text-gray-900 ml-2">{{ pr.title }}</span>
          </div>
          <div class="text-xs text-gray-400">{{ pr.author }} &middot; {{ pr.created_at.slice(0, 10) }}</div>
        </div>
      </div>
      <p v-else class="text-sm text-gray-400">暂无 Open PR</p>
    </div>

    <!-- Open Issues -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">Open Issues ({{ repo.open_issues.length }})</h3>
      <div v-if="repo.open_issues.length" class="divide-y divide-gray-50">
        <div v-for="issue in repo.open_issues" :key="issue.number" class="py-3 first:pt-0 last:pb-0 flex items-center justify-between">
          <div>
            <span class="text-sm text-crystal-600 font-medium">#{{ issue.number }}</span>
            <span class="text-sm text-gray-900 ml-2">{{ issue.title }}</span>
          </div>
          <div class="flex items-center space-x-2">
            <UBadge v-for="l in issue.labels" :key="l" color="gray" variant="subtle" size="xs">{{ l }}</UBadge>
          </div>
        </div>
      </div>
      <p v-else class="text-sm text-gray-400">暂无 Open Issue</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { repos } from '~/data/mock'

const route = useRoute()
const repo = computed(() => repos.find(r => r.id === route.params.id))
</script>
```

- [ ] **Step 3: Verify repo pages render**

- [ ] **Step 4: Commit**

```bash
git add theme-pm/pages/app/repos/
git commit -m "feat(theme-pm): add GitHub repo list and detail pages"
```

---

## Task 14: AI Insights Page

**Files:**
- Create: `theme-pm/pages/app/ai-insights.vue`

- [ ] **Step 1: Create AI insights page**

```vue
<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">AI 洞察</h1>
      <div class="flex items-center space-x-2">
        <ServiceStatusDot :online="isOnline('ai')" />
        <span class="text-sm" :class="isOnline('ai') ? 'text-emerald-500' : 'text-gray-400'">
          {{ isOnline('ai') ? 'AI 服务在线' : 'AI 服务离线' }}
        </span>
      </div>
    </div>

    <template v-if="isOnline('ai')">
      <!-- Trend Alerts -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          v-for="alert in insights.trend_alerts"
          :key="alert.message"
          class="rounded-xl border p-4"
          :class="alert.severity === 'critical' ? 'bg-red-50 border-red-100' : 'bg-amber-50 border-amber-100'"
        >
          <div class="flex items-center mb-1">
            <UIcon
              :name="alert.severity === 'critical' ? 'i-heroicons-exclamation-triangle' : 'i-heroicons-information-circle'"
              class="w-4 h-4 mr-2"
              :class="alert.severity === 'critical' ? 'text-red-500' : 'text-amber-500'"
            />
            <span class="text-sm font-medium" :class="alert.severity === 'critical' ? 'text-red-700' : 'text-amber-700'">
              {{ alert.metric }}
            </span>
          </div>
          <p class="text-sm" :class="alert.severity === 'critical' ? 'text-red-600' : 'text-amber-600'">{{ alert.message }}</p>
        </div>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">平均解决时间趋势</h3>
          <ChartsBarChart
            :x-data="insights.team_efficiency.avg_resolution_trend.map(t => t.month)"
            :series="[{ name: '平均小时', data: insights.team_efficiency.avg_resolution_trend.map(t => t.hours) }]"
            :height="260"
          />
        </div>
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">人均处理量</h3>
          <ChartsBarChart
            :x-data="insights.team_efficiency.per_person_output.map(p => p.name)"
            :series="[{ name: '解决数', data: insights.team_efficiency.per_person_output.map(p => p.count) }]"
            :height="260"
          />
        </div>
      </div>

      <!-- Developer Stats Table -->
      <div class="bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">开发者统计</h3>
        <UTable :rows="developerStats" :columns="devColumns" :ui="{ th: { base: 'text-xs' }, td: { base: 'text-sm' } }">
          <template #avg_resolution_hours-data="{ row }">
            {{ row.avg_resolution_hours ? row.avg_resolution_hours + 'h' : '-' }}
          </template>
          <template #priority_distribution-data="{ row }">
            <div class="flex gap-1">
              <UBadge v-if="row.priority_distribution.P0" color="red" variant="subtle" size="xs">P0: {{ row.priority_distribution.P0 }}</UBadge>
              <UBadge v-if="row.priority_distribution.P1" color="orange" variant="subtle" size="xs">P1: {{ row.priority_distribution.P1 }}</UBadge>
              <UBadge v-if="row.priority_distribution.P2" color="yellow" variant="subtle" size="xs">P2: {{ row.priority_distribution.P2 }}</UBadge>
              <UBadge v-if="row.priority_distribution.P3" color="gray" variant="subtle" size="xs">P3: {{ row.priority_distribution.P3 }}</UBadge>
            </div>
          </template>
        </UTable>
      </div>

      <!-- Bottlenecks -->
      <div class="bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">瓶颈识别</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div v-for="b in insights.bottlenecks" :key="b.name" class="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
            <div class="flex items-center">
              <UIcon :name="b.type === 'assignee' ? 'i-heroicons-user' : 'i-heroicons-tag'" class="w-4 h-4 text-gray-400 mr-2" />
              <span class="text-sm text-gray-700">{{ b.name }}</span>
              <UBadge class="ml-2" color="gray" variant="subtle" size="xs">{{ b.type === 'assignee' ? '负责人' : '标签' }}</UBadge>
            </div>
            <span class="text-sm font-semibold text-amber-600">{{ b.pending_count }} 积压</span>
          </div>
        </div>
      </div>

      <!-- Recommendations -->
      <div class="bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">AI 建议</h3>
        <div class="space-y-2">
          <div v-for="(rec, idx) in insights.recommendations" :key="idx" class="flex items-start">
            <UIcon name="i-heroicons-light-bulb" class="w-4 h-4 text-crystal-500 mr-2 mt-0.5 flex-shrink-0" />
            <span class="text-sm text-gray-600">{{ rec }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- Offline State -->
    <div v-else class="bg-white rounded-xl border border-gray-100 p-12 text-center">
      <UIcon name="i-heroicons-cpu-chip" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">AI 服务暂不可用</p>
      <p class="text-sm text-gray-400 mt-1">AI 洞察功能需要 AI 服务在线才能使用</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { aiInsights, developerStats } from '~/data/mock'
const { isOnline } = useServiceStatus()

const insights = aiInsights

const devColumns = [
  { key: 'user_name', label: '开发者' },
  { key: 'monthly_resolved_count', label: '本月解决数', sortable: true },
  { key: 'avg_resolution_hours', label: '平均处理时间', sortable: true },
  { key: 'priority_distribution', label: '优先级分布' },
]
</script>
```

- [ ] **Step 2: Verify AI insights page renders**

- [ ] **Step 3: Commit**

```bash
git add theme-pm/pages/app/ai-insights.vue
git commit -m "feat(theme-pm): add AI insights page with stats, alerts, bottlenecks, recommendations"
```

---

## Task 15: Integration & Showcase Server Update

**Files:**
- Modify: `server.mjs` (root showcase server — add theme-pm route)
- Modify: `index.html` (root landing page — add theme-pm card)

- [ ] **Step 1: Check current server.mjs and index.html to understand the pattern**

Read `server.mjs` and `index.html` at project root to see how theme-a/b/c are registered.

- [ ] **Step 2: Add theme-pm to showcase server**

Add a proxy route for `/theme-pm/` pointing to port 3004 in `server.mjs`, following the existing pattern for theme-a/b/c.

- [ ] **Step 3: Add theme-pm card to landing page**

Add a card for "DevTrack - 项目管理平台" in `index.html`, following the existing card pattern.

- [ ] **Step 4: Verify full navigation**

Start theme-pm dev server and showcase server. Verify:
- Login page renders
- Dashboard shows stats, charts, leaderboard, activity
- Project list shows 3 projects
- Project detail shows kanban
- Issue list with filtering/pagination works
- Issue detail shows AI analysis, GitHub association, branch creation
- Repo list and detail pages work
- AI insights page works
- Sidebar navigation highlights active page
- Breadcrumbs update correctly
- Service status dots show in sidebar

- [ ] **Step 5: Commit**

```bash
git add server.mjs index.html
git commit -m "feat: add theme-pm to showcase server and landing page"
```
