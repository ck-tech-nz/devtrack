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
                  v-if="isTester && issue.status === '已解决'"
                  class="text-xs px-1.5 py-0.5 rounded flex-shrink-0 bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400"
                >待验证</span>
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
              <NuxtLink
                v-for="n in mentions"
                :key="n.id"
                :to="n.source_issue_id ? `/app/issues/${n.source_issue_id}` : `/app/notifications/${n.id}`"
                class="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0 hover:bg-gray-50 dark:hover:bg-gray-800 -mx-2 px-2 rounded-lg transition-colors"
              >
                <div class="w-7 h-7 rounded-lg bg-crystal-50 dark:bg-crystal-950 flex items-center justify-center flex-shrink-0">
                  <UIcon name="i-heroicons-bell" class="w-3.5 h-3.5 text-crystal-500" />
                </div>
                <span class="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{{ n.title }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">{{ timeAgo(n.created_at) }}</span>
              </NuxtLink>
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

          <!-- 我的提升计划 -->
          <div v-if="planData" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">我的提升计划</h3>
              <NuxtLink to="/app/ai/my-plan" class="text-xs text-crystal-500 hover:text-crystal-700">
                查看全部 →
              </NuxtLink>
            </div>
            <div class="flex items-center gap-4 mb-3 text-sm">
              <span class="text-gray-500 dark:text-gray-400">{{ planData.done }}/{{ planData.total }} 已完成</span>
              <span class="text-gray-500 dark:text-gray-400">{{ planData.earned }} / {{ planData.total_points }} 分</span>
            </div>
            <UProgress :value="planData.total > 0 ? planData.done / planData.total * 100 : 0" size="xs" class="mb-3" />
            <div class="space-y-2">
              <div v-for="item in planData.pending_items" :key="item.id" class="flex items-center justify-between text-sm">
                <span class="text-gray-700 dark:text-gray-300 truncate">{{ item.title }}</span>
                <span class="text-gray-400 dark:text-gray-500 flex-shrink-0 ml-2">{{ item.points }}分</span>
              </div>
            </div>
          </div>

          <!-- Recent Activity -->
          <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">最近动态</h3>
            <div v-if="recentActivity.length" class="divide-y divide-gray-50 dark:divide-gray-800 max-h-80 overflow-y-auto">
              <NuxtLink
                v-for="item in recentActivity"
                :key="item.id"
                :to="item.issue_id ? `/app/issues/${item.issue_id}` : '#'"
                class="flex items-center py-2.5 first:pt-0 last:pb-0 hover:bg-gray-50 dark:hover:bg-gray-800 -mx-2 px-2 rounded-lg transition-colors"
              >
                <div class="w-7 h-7 rounded-lg bg-gray-50 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                  <UIcon :name="item.icon" class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500" />
                </div>
                <span class="ml-3 text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{{ item.message }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-500 ml-3 whitespace-nowrap">{{ item.time }}</span>
              </NuxtLink>
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
const { user, hasGroup } = useAuth()

const loading = ref(true)
const searchQuery = ref('')
const myIssues = ref<any[]>([])
const mentions = ref<any[]>([])
const stats = ref({ total: 0, pending: 0, in_progress: 0, resolved_this_week: 0 })
const recentActivity = ref<any[]>([])
const planData = ref<any>(null)
const isTester = computed(() => hasGroup('测试'))

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

async function fetchPlanSummary() {
  try {
    const res = await api<any>('/api/kpi/plans/me/')
    if (res.current) {
      const items = res.current.action_items || []
      const done = items.filter((i: any) => i.status === 'verified').length
      const earned = items.reduce((s: number, i: any) => s + (i.earned_points || 0), 0)
      const total_points = items.reduce((s: number, i: any) => s + i.points, 0)
      const pending_items = items
        .filter((i: any) => !['verified', 'not_achieved'].includes(i.status))
        .slice(0, 3)
      planData.value = { done, total: items.length, earned, total_points, pending_items }
    }
  } catch { /* plan not available */ }
}

async function fetchTesterTodos(): Promise<any[]> {
  const userId = user.value?.id
  const [assignedData, resolvedData] = await Promise.all([
    api<any>(`/api/issues/?assignee=${userId}&exclude_statuses=已关闭&ordering=-priority&page_size=10`),
    api<any>('/api/issues/?status=已解决&ordering=-priority&page_size=20'),
  ])
  const assigned = (assignedData.results || assignedData || []) as any[]
  const resolved = (resolvedData.results || resolvedData || []) as any[]
  const assignedIds = new Set(assigned.map((i: any) => i.id))
  const merged = [...assigned, ...resolved.filter((i: any) => !assignedIds.has(i.id))]
  return merged.slice(0, 15)
}

async function fetchDefaultTodos(): Promise<any[]> {
  const userId = user.value?.id
  const data = await api<any>(`/api/issues/?assignee=${userId}&exclude_statuses=已解决,已关闭&ordering=-priority&page_size=10`)
  return (data.results || data || []).slice(0, 10)
}

onMounted(async () => {
  try {
    const [issueResults, notifData, statsData, activityData] = await Promise.all([
      isTester.value ? fetchTesterTodos() : fetchDefaultTodos(),
      api<any[]>('/api/notifications/?is_read=false'),
      api<any>('/api/dashboard/stats/'),
      api<any[]>('/api/dashboard/recent-activity/'),
    ])
    fetchPlanSummary()

    myIssues.value = issueResults

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
      issue_id: item.issue_id,
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
