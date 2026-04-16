<template>
  <div class="space-y-6">
    <!-- 返回按钮 -->
    <NuxtLink to="/app/kpi" class="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
      <UIcon name="i-heroicons-arrow-left" class="w-4 h-4" />
      返回团队 KPI
    </NuxtLink>

    <!-- 加载中 -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <template v-else-if="summary">
      <!-- 用户信息卡片 -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
        <div class="flex items-center gap-4 flex-wrap">
          <img
            v-if="summary.avatar"
            :src="resolveAvatarUrl(summary.avatar)"
            class="w-16 h-16 rounded-full"
          />
          <div
            v-else
            class="w-16 h-16 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center text-xl font-semibold text-crystal-600 dark:text-crystal-400"
          >
            {{ (summary.user_name || '?').slice(0, 1) }}
          </div>
          <div class="flex-1 min-w-0">
            <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">{{ summary.user_name }}</h1>
            <div class="flex gap-1.5 mt-1.5 flex-wrap">
              <UBadge
                v-for="g in (summary.groups || [])"
                :key="g"
                color="neutral"
                variant="subtle"
                size="xs"
              >
                {{ g }}
              </UBadge>
            </div>
          </div>
          <div class="text-right">
            <div class="text-xs text-gray-400 dark:text-gray-500 mb-1">综合评分</div>
            <div class="text-4xl font-bold text-crystal-600 dark:text-crystal-400">
              {{ summary.scores?.overall != null ? Number(summary.scores.overall).toFixed(1) : '-' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 周期选择 -->
      <div class="flex items-center gap-2 flex-wrap">
        <UButtonGroup>
          <UButton
            v-for="p in periods"
            :key="p.value"
            size="sm"
            :variant="activePeriod === p.value ? 'solid' : 'outline'"
            :color="activePeriod === p.value ? 'primary' : 'neutral'"
            @click="activePeriod = p.value; customStart = ''; customEnd = ''"
          >
            {{ p.label }}
          </UButton>
        </UButtonGroup>
        <UPopover>
          <UButton size="sm" variant="outline" color="neutral" icon="i-heroicons-calendar-days">
            {{ customStart && customEnd ? `${customStart} ~ ${customEnd}` : '自定义' }}
          </UButton>
          <template #content>
            <div class="p-3 space-y-3">
              <div class="space-y-1">
                <label class="text-xs text-gray-500 dark:text-gray-400">开始日期</label>
                <UInput v-model="customStart" type="date" size="sm" />
              </div>
              <div class="space-y-1">
                <label class="text-xs text-gray-500 dark:text-gray-400">结束日期</label>
                <UInput v-model="customEnd" type="date" size="sm" />
              </div>
              <UButton size="sm" block @click="applyCustomRange">应用</UButton>
            </div>
          </template>
        </UPopover>
      </div>

      <!-- 标签页 -->
      <UTabs :items="tabs" class="w-full">
        <template #content="{ item }">
          <!-- 问题指标 -->
          <div v-if="item.value === 'issues'" class="space-y-6 pt-4">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- 雷达图 -->
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">能力雷达</h3>
                <ChartsRadarChart
                  :indicators="radarIndicators"
                  :values="radarValues"
                  :height="280"
                />
              </div>
              <!-- 指标卡片 -->
              <div class="grid grid-cols-2 gap-3 content-start">
                <div
                  v-for="card in issueMetricCards"
                  :key="card.label"
                  class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4"
                >
                  <div class="text-xs text-gray-400 dark:text-gray-500 mb-1">{{ card.label }}</div>
                  <div class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ card.value }}</div>
                  <div v-if="card.sub" class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ card.sub }}</div>
                </div>
              </div>
            </div>
            <!-- 优先级分布表 -->
            <div
              v-if="issues?.priority_breakdown?.length"
              class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden"
            >
              <div class="px-5 py-3 border-b border-gray-50 dark:border-gray-800">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">优先级分布</h3>
              </div>
              <UTable :data="issues.priority_breakdown" :columns="priorityColumns" :ui="{ th: 'text-xs', td: 'text-sm' }" />
            </div>
          </div>

          <!-- Commit 分析 -->
          <div v-if="item.value === 'commits'" class="space-y-6 pt-4">
            <!-- 汇总卡片 -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div
                v-for="card in commitSummaryCards"
                :key="card.label"
                class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4"
              >
                <div class="text-xs text-gray-400 dark:text-gray-500 mb-1">{{ card.label }}</div>
                <div class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ card.value }}</div>
              </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- 提交类型分布 -->
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">提交类型分布</h3>
                <ChartsPieChart
                  :data="commitTypePieData"
                  :height="260"
                />
              </div>
              <!-- 提交大小分布 -->
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">提交大小分布</h3>
                <ChartsBarChart
                  :x-data="['小(<50行)', '中(50-200行)', '大(>200行)']"
                  :series="[{ name: '提交数', data: commitSizeData }]"
                  :height="260"
                />
              </div>
            </div>

            <!-- 技术栈 -->
            <div
              v-if="commits?.tech_stack_breadth?.length"
              class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5"
            >
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">技术栈广度</h3>
              <div class="flex flex-wrap gap-2">
                <UBadge
                  v-for="tech in commits.tech_stack_breadth"
                  :key="tech"
                  color="primary"
                  variant="subtle"
                  size="sm"
                >
                  {{ tech }}
                </UBadge>
              </div>
            </div>

            <!-- 工作节奏 -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">每日提交分布</h3>
                <ChartsBarChart
                  :x-data="hourLabels"
                  :series="[{ name: '提交数', data: byHourData }]"
                  :height="220"
                />
              </div>
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">每周提交分布</h3>
                <ChartsBarChart
                  :x-data="weekdayLabels"
                  :series="[{ name: '提交数', data: byWeekdayData }]"
                  :height="220"
                />
              </div>
            </div>

            <!-- 仓库覆盖 -->
            <div
              v-if="commits?.repo_coverage?.length"
              class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5"
            >
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">仓库覆盖</h3>
              <div class="space-y-2">
                <div
                  v-for="repo in commits.repo_coverage"
                  :key="repo.repo_name || repo.name"
                  class="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg px-4 py-2.5"
                >
                  <span class="text-sm text-gray-700 dark:text-gray-300">{{ repo.repo_name || repo.name }}</span>
                  <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ repo.commit_count ?? repo.count }} 次提交</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 趋势变化 -->
          <div v-if="item.value === 'trends'" class="space-y-6 pt-4">
            <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">各维度趋势</h3>
              <ChartsLineChart
                v-if="trendXData.length"
                :x-data="trendXData"
                :series="trendSeries"
                :height="340"
              />
              <div v-else class="py-12 text-center text-sm text-gray-400 dark:text-gray-500">
                暂无趋势数据
              </div>
            </div>
          </div>

          <!-- 改进建议 -->
          <div v-if="item.value === 'suggestions'" class="space-y-6 pt-4">
            <!-- 画像 -->
            <div
              v-if="suggestions?.profile"
              class="rounded-xl p-6 text-center bg-gradient-to-r from-crystal-500 to-violet-500"
            >
              <div class="text-lg font-semibold text-white">{{ suggestions.profile }}</div>
            </div>

            <!-- 不足 -->
            <div
              v-if="suggestions?.shortcomings?.length"
              class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5"
            >
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">待改进项</h3>
              <div class="space-y-3">
                <div
                  v-for="(item, idx) in suggestions.shortcomings"
                  :key="idx"
                  class="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800"
                >
                  <span
                    class="inline-block w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                    :class="severityDotClass(item.severity)"
                  />
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ item.title || item.dimension }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ item.description || item.detail }}</div>
                  </div>
                  <UBadge
                    :color="severityBadgeColor(item.severity)"
                    variant="subtle"
                    size="xs"
                  >
                    {{ severityLabel(item.severity) }}
                  </UBadge>
                </div>
              </div>
            </div>

            <!-- 趋势建议 -->
            <div
              v-if="suggestions?.trends?.length"
              class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5"
            >
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">趋势观察</h3>
              <div class="space-y-3">
                <div
                  v-for="(t, idx) in suggestions.trends"
                  :key="idx"
                  class="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800"
                >
                  <UIcon
                    :name="t.direction === 'up' ? 'i-heroicons-arrow-trending-up' : 'i-heroicons-arrow-trending-down'"
                    class="w-5 h-5 mt-0.5 flex-shrink-0"
                    :class="t.direction === 'up' ? 'text-emerald-500' : 'text-red-500'"
                  />
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ t.dimension || t.title }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ t.description || t.detail }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 无建议 -->
            <div
              v-if="!suggestions?.shortcomings?.length && !suggestions?.trends?.length && !suggestions?.profile"
              class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-12 text-center"
            >
              <UIcon name="i-heroicons-light-bulb" class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p class="text-gray-500 dark:text-gray-400">暂无改进建议</p>
            </div>
          </div>
        </template>
      </UTabs>
    </template>

    <!-- 无数据 -->
    <div
      v-else-if="!loading"
      class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-12 text-center"
    >
      <UIcon name="i-heroicons-chart-bar" class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
      <p class="text-gray-500 dark:text-gray-400">暂无该用户的 KPI 数据</p>
      <NuxtLink to="/app/kpi">
        <UButton class="mt-4" size="sm" variant="outline" color="neutral">返回团队 KPI</UButton>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { api } = useApi()
const { resolveAvatarUrl } = useAvatars()
const { user: authUser } = useAuth()

const loading = ref(true)
const activePeriod = ref('month')
const customStart = ref('')
const customEnd = ref('')

const summary = ref<any>(null)
const issues = ref<any>(null)
const commits = ref<any>(null)
const trends = ref<any>(null)
const suggestions = ref<any>(null)

const periods = [
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '季度', value: 'quarter' },
]

const tabs = [
  { label: '问题指标', value: 'issues' },
  { label: 'Commit 分析', value: 'commits' },
  { label: '趋势变化', value: 'trends' },
  { label: '改进建议', value: 'suggestions' },
]

// 解析用户 ID，支持 'me' 别名
const userId = computed(() => {
  const id = route.params.id as string
  if (id === 'me') return authUser.value?.id
  return id
})

// 雷达图数据
const radarIndicators = computed(() => [
  { name: '效率', max: 100 },
  { name: '产出', max: 100 },
  { name: '质量', max: 100 },
  { name: '能力', max: 100 },
  { name: '成长', max: 100 },
])

const radarValues = computed(() => {
  const s = summary.value?.scores
  if (!s) return [0, 0, 0, 0, 0]
  return [
    Number(s.efficiency) || 0,
    Number(s.output) || 0,
    Number(s.quality) || 0,
    Number(s.capability) || 0,
    Number(s.growth) || 0,
  ]
})

// 问题指标卡片
const issueMetricCards = computed(() => {
  if (!issues.value) return []
  const d = issues.value
  return [
    { label: '分配问题数', value: d.assigned_count ?? '-' },
    { label: '已解决', value: d.resolved_count ?? '-', sub: d.resolution_rate != null ? `解决率 ${(d.resolution_rate * 100).toFixed(0)}%` : undefined },
    { label: '平均解决时间', value: d.avg_resolution_hours != null ? `${d.avg_resolution_hours.toFixed(1)}h` : '-' },
    { label: '日均解决', value: d.daily_resolved_avg != null ? d.daily_resolved_avg.toFixed(1) : '-' },
    { label: '加权问题价值', value: d.weighted_issue_value != null ? d.weighted_issue_value.toFixed(1) : '-' },
  ]
})

const priorityColumns = [
  { accessorKey: 'priority', header: '优先级' },
  { accessorKey: 'count', header: '数量' },
  { accessorKey: 'resolved', header: '已解决' },
  { accessorKey: 'avg_hours', header: '平均耗时' },
]

// Commit 汇总卡片
const commitSummaryCards = computed(() => {
  if (!commits.value) return []
  const c = commits.value
  return [
    { label: '总提交数', value: c.total_commits ?? '-' },
    { label: '代码变更', value: c.additions != null && c.deletions != null ? `+${c.additions} / -${c.deletions}` : '-' },
    { label: '自引 Bug 率', value: c.self_introduced_bug_rate != null ? `${(c.self_introduced_bug_rate * 100).toFixed(1)}%` : '-' },
    { label: 'Churn 率', value: c.churn_rate != null ? `${(c.churn_rate * 100).toFixed(1)}%` : '-' },
  ]
})

// 提交类型饼图
const commitTypePieData = computed(() => {
  const dist = commits.value?.commit_type_distribution
  if (!dist || typeof dist !== 'object') return []
  return Object.entries(dist).map(([name, value]) => ({ name, value: value as number }))
})

// 提交大小柱状图
const commitSizeData = computed(() => {
  const dist = commits.value?.commit_size_distribution
  if (!dist) return [0, 0, 0]
  return [dist.small ?? 0, dist.medium ?? 0, dist.large ?? 0]
})

// 工作节奏
const hourLabels = Array.from({ length: 24 }, (_, i) => `${i}时`)
const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const byHourData = computed(() => {
  const bh = commits.value?.by_hour
  if (!bh) return Array(24).fill(0)
  if (Array.isArray(bh)) return bh
  return Array.from({ length: 24 }, (_, i) => bh[String(i)] ?? 0)
})

const byWeekdayData = computed(() => {
  const bw = commits.value?.by_weekday
  if (!bw) return Array(7).fill(0)
  if (Array.isArray(bw)) return bw
  return Array.from({ length: 7 }, (_, i) => bw[String(i)] ?? 0)
})

// 趋势图
const trendXData = computed(() => {
  if (!trends.value?.history?.length) return []
  return trends.value.history.map((h: any) => h.period_start?.slice(5) || '')
})

const trendSeries = computed(() => {
  if (!trends.value?.history?.length) return []
  const dims = ['efficiency', 'output', 'quality', 'capability', 'growth']
  const labels: Record<string, string> = { efficiency: '效率', output: '产出', quality: '质量', capability: '能力', growth: '成长' }
  return dims.map(dim => ({
    name: labels[dim],
    data: trends.value.history.map((h: any) => Number(h.scores?.[dim]) || 0),
  }))
})

// 建议相关
function severityDotClass(severity: string) {
  if (severity === 'high') return 'bg-red-500'
  if (severity === 'medium') return 'bg-amber-500'
  return 'bg-gray-400'
}

function severityBadgeColor(severity: string): any {
  if (severity === 'high') return 'error'
  if (severity === 'medium') return 'warning'
  return 'neutral'
}

function severityLabel(severity: string) {
  if (severity === 'high') return '高'
  if (severity === 'medium') return '中'
  return '低'
}

// 数据加载
function buildQuery() {
  const params = new URLSearchParams()
  if (customStart.value && customEnd.value) {
    params.set('start', customStart.value)
    params.set('end', customEnd.value)
  } else {
    params.set('period', activePeriod.value)
  }
  return params.toString()
}

function applyCustomRange() {
  if (!customStart.value || !customEnd.value) return
  activePeriod.value = ''
  fetchAll()
}

async function fetchAll() {
  const uid = userId.value
  if (!uid) return

  loading.value = true
  const q = buildQuery()

  try {
    const [summaryRes, issuesRes, commitsRes, trendsRes, suggestionsRes] = await Promise.all([
      api<any>(`/api/kpi/users/${uid}/summary/?${q}`).catch(() => null),
      api<any>(`/api/kpi/users/${uid}/issues/?${q}`).catch(() => null),
      api<any>(`/api/kpi/users/${uid}/commits/?${q}`).catch(() => null),
      api<any>(`/api/kpi/users/${uid}/trends/?periods=6`).catch(() => null),
      api<any>(`/api/kpi/users/${uid}/suggestions/?${q}`).catch(() => null),
    ])
    summary.value = summaryRes
    issues.value = issuesRes
    commits.value = commitsRes
    trends.value = trendsRes
    suggestions.value = suggestionsRes
  } catch (e) {
    console.error('Failed to load KPI profile:', e)
  } finally {
    loading.value = false
  }
}

watch([activePeriod], () => {
  if (activePeriod.value) {
    customStart.value = ''
    customEnd.value = ''
  }
  fetchAll()
})

onMounted(fetchAll)
</script>
