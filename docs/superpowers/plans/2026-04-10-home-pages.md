# Home Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public landing page at `/` and an authenticated home ("工作台") at `/app/home`.

**Architecture:** The current login form at `/` moves to `/login`. The root becomes a split-layout landing page (branding + app preview). A new `/app/home` page becomes the post-login destination — a command center showing personal tasks, mentions, project stats, and team activity. All data comes from existing backend endpoints.

**Tech Stack:** Nuxt 4, Vue 3, Nuxt UI, Tailwind CSS, existing backend REST API

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/app/pages/login.vue` | Create | Login form (moved from `index.vue`) |
| `frontend/app/pages/index.vue` | Rewrite | Public landing page |
| `frontend/app/pages/app/home.vue` | Create | Authenticated command center |
| `frontend/app/middleware/auth.global.ts` | Modify | Add `/login` to public routes, redirect auth users from `/` to `/app/home` |
| `frontend/app/composables/useNavigation.ts` | Modify | Add "工作台" nav item, update breadcrumb home link |
| `frontend/app/pages/register.vue` | Modify | Update "返回登录" link from `/` to `/login` |

---

### Task 1: Move Login Form to `/login`

**Files:**
- Create: `frontend/app/pages/login.vue`
- Modify: `frontend/app/middleware/auth.global.ts` (line 2)

- [ ] **Step 1: Create `login.vue` with the existing login form**

Copy the current `index.vue` login form to a new file. The only change is the redirect target after login: `/app/home` instead of `/app/issues`.

```vue
<template>
  <div class="w-full max-w-sm">
    <div class="text-center mb-8">
      <img src="~/assets/images/logo-icon.svg" alt="DevTrakr" class="w-14 h-14 mx-auto mb-4" />
      <h1 class="text-2xl font-semibold text-gray-900">DevTrakr</h1>
      <p class="text-sm text-gray-400 mt-1">项目管理平台</p>
    </div>

    <form class="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8" @submit.prevent="handleLogin">
      <h2 class="text-lg font-semibold text-gray-900 mb-6">登录</h2>
      <div v-if="registered" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
        注册成功，请等待管理员审批后登录
      </div>
      <div class="space-y-4">
        <UFormField label="用户名">
          <UInput v-model="username" placeholder="请输入用户名" icon="i-heroicons-user" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="密码">
          <UInput v-model="password" type="password" placeholder="请输入密码" icon="i-heroicons-lock-closed" size="lg" class="w-full" />
        </UFormField>
        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <UButton block size="lg" color="primary" :loading="loading" type="submit">登录</UButton>
      </div>
    </form>

    <p class="text-center text-sm text-gray-500 mt-4">
      还没有账号？
      <NuxtLink to="/register" class="text-crystal-500 hover:text-crystal-700 font-medium">去注册</NuxtLink>
    </p>
    <p class="text-center text-xs text-gray-400 mt-6">&copy; 2026 DevTrakr 项目管理平台</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const route = useRoute()
const registered = computed(() => route.query.registered === '1')

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const { setTokens } = useApi()
const { fetchMe } = useAuth()

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const data = await $fetch<{ access: string; refresh: string }>('/api/auth/login/', {
      method: 'POST',
      body: { username: username.value, password: password.value },
    })
    setTokens(data.access, data.refresh)
    await fetchMe()
    await navigateTo('/app/home')
  } catch (e: any) {
    error.value = '用户名或密码错误'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 2: Verify `/login` is already in the auth middleware whitelist**

Check `frontend/app/middleware/auth.global.ts` line 2. It already has:

```ts
if (to.path === '/' || to.path === '/login' || to.path === '/register') return
```

`/login` is already whitelisted — no change needed here.

- [ ] **Step 3: Update register page link**

In `frontend/app/pages/register.vue`, change the "返回登录" link from `/` to `/login` (line 49):

```vue
<!-- old -->
<NuxtLink to="/" class="text-crystal-500 hover:text-crystal-700 font-medium">返回登录</NuxtLink>

<!-- new -->
<NuxtLink to="/login" class="text-crystal-500 hover:text-crystal-700 font-medium">返回登录</NuxtLink>
```

Also update the post-registration redirect in `register.vue` (line 107):

```ts
// old
await navigateTo('/?registered=1')

// new
await navigateTo('/login?registered=1')
```

- [ ] **Step 4: Verify login page works**

Run: `cd frontend && npm run dev`

Navigate to `http://localhost:3004/login` and confirm:
- Login form renders correctly with auth layout
- Successful login redirects to `/app/home` (will 404 for now — that's expected)

- [ ] **Step 5: Commit**

```bash
git add frontend/app/pages/login.vue frontend/app/pages/register.vue
git commit -m "feat: move login form to /login route, update register links"
```

---

### Task 2: Rewrite `/` as Public Landing Page

**Files:**
- Rewrite: `frontend/app/pages/index.vue`
- Modify: `frontend/app/middleware/auth.global.ts` (add auth redirect)

- [ ] **Step 1: Rewrite `index.vue` as the landing page**

Replace the entire contents of `frontend/app/pages/index.vue` with the split landing layout:

```vue
<template>
  <div class="w-full max-w-5xl mx-auto px-6">
    <div class="flex flex-col md:flex-row items-center gap-12 md:gap-16 min-h-[70vh]">
      <!-- Left: Branding + CTAs -->
      <div class="flex-1 flex flex-col items-start">
        <div class="flex items-center gap-3 mb-6">
          <img src="~/assets/images/logo-icon.svg" alt="DevTrakr" class="w-12 h-12" />
          <span class="text-2xl font-bold text-gray-900">DevTrakr</span>
        </div>
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 leading-tight mb-4">
          团队项目管理<br />高效协作
        </h1>
        <p class="text-gray-500 mb-8 text-base leading-relaxed">一站式项目管理平台，让团队协作更简单</p>

        <div class="space-y-3 mb-10 w-full">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-crystal-50 flex items-center justify-center flex-shrink-0">
              <UIcon name="i-heroicons-clipboard-document-list" class="w-4 h-4 text-crystal-500" />
            </div>
            <div>
              <span class="text-sm font-medium text-gray-900">Issue 追踪</span>
              <span class="text-sm text-gray-400 ml-2">创建、分配、跟踪问题</span>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-crystal-50 flex items-center justify-center flex-shrink-0">
              <UIcon name="i-heroicons-chart-bar" class="w-4 h-4 text-crystal-500" />
            </div>
            <div>
              <span class="text-sm font-medium text-gray-900">数据看板</span>
              <span class="text-sm text-gray-400 ml-2">实时统计分析</span>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-crystal-50 flex items-center justify-center flex-shrink-0">
              <UIcon name="i-heroicons-user-group" class="w-4 h-4 text-crystal-500" />
            </div>
            <div>
              <span class="text-sm font-medium text-gray-900">团队协作</span>
              <span class="text-sm text-gray-400 ml-2">权限与角色管理</span>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-crystal-50 flex items-center justify-center flex-shrink-0">
              <UIcon name="i-heroicons-code-bracket" class="w-4 h-4 text-crystal-500" />
            </div>
            <div>
              <span class="text-sm font-medium text-gray-900">仓库集成</span>
              <span class="text-sm text-gray-400 ml-2">Git 仓库关联</span>
            </div>
          </div>
        </div>

        <div class="flex gap-3">
          <UButton to="/login" size="lg" color="primary">登录</UButton>
          <UButton to="/register" size="lg" variant="outline" color="neutral">注册</UButton>
        </div>
      </div>

      <!-- Right: App Preview Mockup -->
      <div class="flex-1 hidden md:block">
        <div class="bg-white rounded-2xl shadow-xl shadow-crystal-100/50 border border-gray-100 p-5">
          <!-- Mini Kanban -->
          <div class="mb-4">
            <div class="text-xs font-semibold text-gray-700 mb-2">Issue 看板</div>
            <div class="flex gap-2">
              <div class="flex-1 bg-amber-50 rounded-lg p-2.5">
                <div class="text-[10px] font-medium text-amber-700 mb-1.5">待处理</div>
                <div class="space-y-1">
                  <div class="bg-white rounded px-2 py-1 text-[10px] text-gray-600 shadow-sm">页面优化</div>
                  <div class="bg-white rounded px-2 py-1 text-[10px] text-gray-600 shadow-sm">权限修复</div>
                </div>
              </div>
              <div class="flex-1 bg-blue-50 rounded-lg p-2.5">
                <div class="text-[10px] font-medium text-blue-700 mb-1.5">进行中</div>
                <div class="space-y-1">
                  <div class="bg-white rounded px-2 py-1 text-[10px] text-gray-600 shadow-sm">API 开发</div>
                  <div class="bg-white rounded px-2 py-1 text-[10px] text-gray-600 shadow-sm">数据迁移</div>
                  <div class="bg-white rounded px-2 py-1 text-[10px] text-gray-600 shadow-sm">单元测试</div>
                </div>
              </div>
              <div class="flex-1 bg-emerald-50 rounded-lg p-2.5">
                <div class="text-[10px] font-medium text-emerald-700 mb-1.5">已完成</div>
                <div class="space-y-1">
                  <div class="bg-white rounded px-2 py-1 text-[10px] text-gray-600 shadow-sm">用户认证</div>
                  <div class="bg-white rounded px-2 py-1 text-[10px] text-gray-600 shadow-sm">部署配置</div>
                </div>
              </div>
            </div>
          </div>
          <!-- Mini Trend -->
          <div>
            <div class="text-xs font-semibold text-gray-700 mb-2">趋势</div>
            <div class="h-16 bg-gradient-to-r from-crystal-50 via-crystal-100 to-crystal-200 rounded-lg flex items-end px-3 pb-2 gap-1.5">
              <div class="w-3 bg-crystal-300 rounded-t" style="height: 30%"></div>
              <div class="w-3 bg-crystal-400 rounded-t" style="height: 50%"></div>
              <div class="w-3 bg-crystal-300 rounded-t" style="height: 40%"></div>
              <div class="w-3 bg-crystal-500 rounded-t" style="height: 70%"></div>
              <div class="w-3 bg-crystal-400 rounded-t" style="height: 55%"></div>
              <div class="w-3 bg-crystal-500 rounded-t" style="height: 80%"></div>
              <div class="w-3 bg-crystal-600 rounded-t" style="height: 65%"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p class="text-center text-xs text-gray-400 mt-12">&copy; 2026 DevTrakr 项目管理平台</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { getToken } = useApi()

onMounted(() => {
  if (getToken()) {
    navigateTo('/app/home')
  }
})
</script>
```

- [ ] **Step 2: Verify the landing page renders**

Run: `cd frontend && npm run dev`

Navigate to `http://localhost:3004/` (logged out). Confirm:
- Split layout renders — branding on left, app preview on right
- Login and register buttons link to `/login` and `/register`
- On mobile width, right preview is hidden

- [ ] **Step 3: Verify auth redirect works**

Log in via `/login`, then navigate back to `/`. Confirm you're redirected to `/app/home` (will 404 for now — expected).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/index.vue
git commit -m "feat: rewrite root as public landing page with split layout"
```

---

### Task 3: Create Authenticated Home (`/app/home`)

**Files:**
- Create: `frontend/app/pages/app/home.vue`

This is the command center page. It fetches data from 4 existing API endpoints in parallel.

- [ ] **Step 1: Create `home.vue` with the command center layout**

```vue
<template>
  <div class="space-y-6">
    <!-- Quick Actions Bar -->
    <div class="flex flex-wrap items-center gap-3">
      <UButton to="/app/issues" icon="i-heroicons-plus" color="primary" size="sm">
        新建 Issue
      </UButton>
      <UInput
        v-model="searchQuery"
        placeholder="搜索 Issue 或项目..."
        icon="i-heroicons-magnifying-glass"
        size="sm"
        class="w-64"
        @keydown.enter="handleSearch"
      />
      <div class="flex gap-2 ml-auto">
        <UButton to="/app/projects" variant="ghost" color="neutral" size="sm" icon="i-heroicons-folder">项目</UButton>
        <UButton to="/app/issues" variant="ghost" color="neutral" size="sm" icon="i-heroicons-bug-ant">Issues</UButton>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <template v-else>
      <!-- Two-Column Command Center -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Left Column: Personal -->
        <div class="space-y-6">
          <!-- My Tasks -->
          <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                我的待办
                <span v-if="myIssues.length" class="ml-1.5 text-xs font-normal text-gray-400">({{ myIssues.length }})</span>
              </h3>
              <NuxtLink to="/app/issues?assignee=me" class="text-xs text-crystal-500 hover:text-crystal-700">查看全部</NuxtLink>
            </div>
            <div v-if="myIssues.length" class="divide-y divide-gray-50 dark:divide-gray-800">
              <NuxtLink
                v-for="issue in myIssues"
                :key="issue.id"
                :to="`/app/issues/${issue.id}`"
                class="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0 hover:bg-gray-50 dark:hover:bg-gray-800 -mx-2 px-2 rounded-lg transition-colors"
              >
                <div
                  class="w-2 h-2 rounded-full flex-shrink-0"
                  :class="priorityColor(issue.priority)"
                />
                <span class="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0 font-mono">{{ formatIssueId(issue.id) }}</span>
                <span class="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{{ issue.title }}</span>
                <span
                  class="text-xs px-1.5 py-0.5 rounded flex-shrink-0"
                  :class="priorityBadge(issue.priority)"
                >{{ issue.priority }}</span>
              </NuxtLink>
            </div>
            <div v-else class="text-sm text-gray-400 dark:text-gray-500 py-4 text-center">没有待办任务</div>
          </div>

          <!-- Mentions -->
          <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                提及我的
                <span v-if="mentions.length" class="ml-1.5 text-xs font-normal text-gray-400">({{ mentions.length }})</span>
              </h3>
              <NuxtLink to="/app/notifications" class="text-xs text-crystal-500 hover:text-crystal-700">查看全部</NuxtLink>
            </div>
            <div v-if="mentions.length" class="divide-y divide-gray-50 dark:divide-gray-800">
              <div
                v-for="n in mentions"
                :key="n.id"
                class="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0"
              >
                <div class="w-7 h-7 rounded-lg bg-crystal-50 dark:bg-crystal-950 flex items-center justify-center flex-shrink-0">
                  <UIcon name="i-heroicons-bell" class="w-3.5 h-3.5 text-crystal-500" />
                </div>
                <span class="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{{ n.title }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">{{ timeAgo(n.created_at) }}</span>
              </div>
            </div>
            <div v-else class="text-sm text-gray-400 dark:text-gray-500 py-4 text-center">没有新通知</div>
          </div>
        </div>

        <!-- Right Column: Team -->
        <div class="space-y-6">
          <!-- Project Health Stats -->
          <div class="grid grid-cols-2 gap-4">
            <DashboardStatCard
              label="本周已解决"
              :value="stats.resolved_this_week"
              icon="i-heroicons-check-circle"
              icon-bg="bg-emerald-50 dark:bg-emerald-950"
              icon-color="text-emerald-500"
            />
            <DashboardStatCard
              label="待处理"
              :value="stats.pending"
              icon="i-heroicons-clock"
              icon-bg="bg-amber-50 dark:bg-amber-950"
              icon-color="text-amber-500"
            />
            <DashboardStatCard
              label="进行中"
              :value="stats.in_progress"
              icon="i-heroicons-arrow-path"
              icon-bg="bg-blue-50 dark:bg-blue-950"
              icon-color="text-blue-500"
            />
            <DashboardStatCard
              label="总 Issue 数"
              :value="stats.total"
              icon="i-heroicons-bug-ant"
              icon-bg="bg-crystal-50 dark:bg-crystal-950"
              icon-color="text-crystal-500"
            />
          </div>

          <!-- Recent Activity -->
          <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">最近动态</h3>
            <div v-if="recentActivity.length" class="divide-y divide-gray-50 dark:divide-gray-800 max-h-80 overflow-y-auto">
              <div
                v-for="item in recentActivity"
                :key="item.id"
                class="flex items-center py-2.5 first:pt-0 last:pb-0"
              >
                <div class="w-7 h-7 rounded-lg bg-gray-50 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                  <UIcon :name="item.icon" class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500" />
                </div>
                <span class="ml-3 text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{{ item.message }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-500 ml-3 whitespace-nowrap">{{ item.time }}</span>
              </div>
            </div>
            <div v-else class="text-sm text-gray-400 dark:text-gray-500 py-4 text-center">暂无动态</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { user } = useAuth()

const loading = ref(true)
const searchQuery = ref('')
const myIssues = ref<any[]>([])
const mentions = ref<any[]>([])
const stats = ref({ total: 0, pending: 0, in_progress: 0, resolved_this_week: 0 })
const recentActivity = ref<any[]>([])

function handleSearch() {
  if (searchQuery.value.trim()) {
    navigateTo(`/app/issues?search=${encodeURIComponent(searchQuery.value.trim())}`)
  }
}

function formatIssueId(id: number): string {
  return `ISS-${String(id).padStart(3, '0')}`
}

function priorityColor(priority: string): string {
  switch (priority) {
    case '紧急': return 'bg-red-500'
    case '高': return 'bg-amber-500'
    case '中': return 'bg-blue-500'
    case '低': return 'bg-gray-400'
    default: return 'bg-gray-300'
  }
}

function priorityBadge(priority: string): string {
  switch (priority) {
    case '紧急': return 'bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-400'
    case '高': return 'bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-400'
    case '中': return 'bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400'
    case '低': return 'bg-gray-50 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
    default: return 'bg-gray-50 text-gray-500'
  }
}

function activityIcon(action: string): string {
  switch (action) {
    case 'created': return 'i-heroicons-plus-circle'
    case 'resolved': return 'i-heroicons-check-circle'
    case 'status_changed': return 'i-heroicons-arrow-path'
    case 'assigned': return 'i-heroicons-user-plus'
    case 'priority_changed': return 'i-heroicons-flag'
    default: return 'i-heroicons-information-circle'
  }
}

function activityMessage(item: any): string {
  const name = item.user_name || '未知用户'
  const issueRef = item.issue_id ? `#${item.issue_id}` : ''
  switch (item.action) {
    case 'created': return `${name} 创建了问题 ${issueRef}${item.issue_title ? '「' + item.issue_title + '」' : ''}`
    case 'resolved': return `${name} 解决了问题 ${issueRef}${item.issue_title ? '「' + item.issue_title + '」' : ''}`
    case 'status_changed': return `${name} 更新了 ${issueRef} 的状态${item.detail ? '：' + item.detail : ''}`
    case 'assigned': return `${name} 分配了问题 ${issueRef}${item.detail ? '给 ' + item.detail : ''}`
    case 'priority_changed': return `${name} 修改了 ${issueRef} 的优先级${item.detail ? '：' + item.detail : ''}`
    default: return `${name} ${item.action} ${issueRef} ${item.detail || ''}`.trim()
  }
}

function timeAgo(isoDate: string): string {
  const now = new Date()
  const then = new Date(isoDate)
  const diffMs = now.getTime() - then.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay} 天前`
}

onMounted(async () => {
  try {
    const userId = user.value?.id
    const [issuesData, notifData, statsData, activityData] = await Promise.all([
      api<any>(`/api/issues/?assignee=${userId}&exclude_statuses=已解决,已关闭&ordering=-priority&page_size=10`),
      api<any[]>('/api/notifications/?is_read=false'),
      api<any>('/api/dashboard/stats/'),
      api<any[]>('/api/dashboard/recent-activity/'),
    ])

    const issueResults = issuesData.results || issuesData || []
    myIssues.value = issueResults.slice(0, 10)

    const notifResults = Array.isArray(notifData) ? notifData : (notifData as any).results || []
    mentions.value = notifResults.slice(0, 5)

    stats.value = {
      total: statsData.total ?? 0,
      pending: statsData.pending ?? 0,
      in_progress: statsData.in_progress ?? 0,
      resolved_this_week: statsData.resolved_this_week ?? 0,
    }

    recentActivity.value = (activityData || []).slice(0, 10).map((item: any) => ({
      id: item.id,
      icon: activityIcon(item.action),
      message: activityMessage(item),
      time: item.created_at ? timeAgo(item.created_at) : '',
    }))
  } catch (e) {
    console.error('Failed to load home data:', e)
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 2: Verify the page renders after login**

Run: `cd frontend && npm run dev`

1. Log in at `/login`
2. Manually navigate to `/app/home`
3. Confirm: quick action bar, two columns, data loads from API

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/home.vue
git commit -m "feat: add authenticated home page (command center at /app/home)"
```

---

### Task 4: Update Navigation and Redirects

**Files:**
- Modify: `frontend/app/composables/useNavigation.ts` (lines 86-93)
- Modify: `frontend/app/middleware/auth.global.ts` (line 18)

- [ ] **Step 1: Add "工作台" as first nav item and update breadcrumb home link**

In `frontend/app/composables/useNavigation.ts`, the nav items come from the backend `routes`. We need to prepend "工作台" as a hardcoded item that's always shown. Update the `filteredNavItems` computed and the breadcrumbs.

First, update `filteredNavItems` to prepend the home item (around line 46):

```ts
// old
const filteredNavItems = computed(() => {
    if (!user.value) return []
    return navItems.value.filter(item => {
      if (item.meta?.superuserOnly && !user.value?.is_superuser) return false
      if (item.permission && !can(item.permission)) return false
      return true
    })
  })

// new
const homeItem: NavItem = { label: '工作台', icon: 'i-heroicons-home', to: '/app/home' }

  const filteredNavItems = computed(() => {
    if (!user.value) return []
    const items = navItems.value.filter(item => {
      if (item.meta?.superuserOnly && !user.value?.is_superuser) return false
      if (item.permission && !can(item.permission)) return false
      return true
    })
    return [homeItem, ...items]
  })
```

Second, update breadcrumbs to use `/app/home` as the home crumb (line 93):

```ts
// old
const crumbs: { label: string; to?: string }[] = [{ label: '首页', to: '/app/issues' }]

// new
const crumbs: { label: string; to?: string }[] = [{ label: '首页', to: '/app/home' }]
```

- [ ] **Step 2: Update auth middleware — redirect unauthenticated to `/login`**

In `frontend/app/middleware/auth.global.ts`, change the fallback redirect from `/` to `/login` so users who lose auth land on the login page, not the landing page. Lines 7 and 18:

```ts
// old (line 7)
return navigateTo('/')

// new
return navigateTo('/login')
```

```ts
// old (line 18)
return navigateTo('/')

// new
return navigateTo('/login')
```

- [ ] **Step 3: Update logout and token-refresh redirects**

In `frontend/app/composables/useAuth.ts`, update the logout function (line 37):

```ts
// old
navigateTo('/')

// new
navigateTo('/login')
```

In `frontend/app/composables/useApi.ts`, update the token refresh failure redirect (line 27):

```ts
// old
navigateTo('/')

// new
navigateTo('/login')
```

- [ ] **Step 4: Verify navigation**

Run: `cd frontend && npm run dev`

1. Log in — confirm redirect goes to `/app/home`
2. Check sidebar — "工作台" should appear as the first item with home icon
3. Click "工作台" — navigates to `/app/home`
4. Check breadcrumbs — "首页" links to `/app/home`
5. Log out — confirm redirect goes to `/login`

- [ ] **Step 5: Commit**

```bash
git add frontend/app/composables/useNavigation.ts frontend/app/middleware/auth.global.ts frontend/app/composables/useAuth.ts frontend/app/composables/useApi.ts
git commit -m "feat: add workspace nav item, update redirects to /login and /app/home"
```

---

### Task 5: Final Verification

- [ ] **Step 1: Full flow test**

Run: `cd frontend && npm run dev`

Test the complete flow:
1. Visit `/` logged out → see landing page with split layout
2. Click "登录" → navigate to `/login`
3. Log in → redirect to `/app/home` (command center)
4. Sidebar shows "工作台" as first nav item
5. Home page shows: quick actions, my tasks, mentions, stats, activity
6. Visit `/` while logged in → auto-redirect to `/app/home`
7. Visit `/app/dashboard` → still works with charts and leaderboard
8. Log out → redirect to `/login`
9. Visit `/register` → "返回登录" links to `/login`

- [ ] **Step 2: Type check**

Run: `cd frontend && npx nuxi typecheck`

Fix any type errors if they appear.

- [ ] **Step 3: Responsive check**

Resize browser to mobile width and confirm:
- Landing page: preview hidden, content stacks vertically
- Home page: two columns collapse to single column

- [ ] **Step 4: Final commit (if any fixes)**

```bash
git add -u frontend/
git commit -m "fix: address type errors and responsive issues"
```
