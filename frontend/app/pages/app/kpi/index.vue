<template>
  <div class="space-y-6">
    <!-- 头部 -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">KPI 分析</h1>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- 周期选择 -->
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

        <!-- 自定义日期 -->
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

        <!-- 角色筛选 -->
        <USelect
          v-model="selectedRole"
          :items="roleOptions"
          size="sm"
          class="w-32"
        />

        <!-- 刷新 -->
        <UButton
          size="sm"
          variant="outline"
          color="neutral"
          icon="i-heroicons-arrow-path"
          :loading="refreshing"
          @click="handleRefresh"
        >
          刷新
        </UButton>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <template v-else-if="data">
      <!-- 汇总卡片 -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="card in summaryCards"
          :key="card.label"
          class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5"
        >
          <div class="text-xs text-gray-400 dark:text-gray-500 mb-1">{{ card.label }}</div>
          <div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ card.value }}</div>
        </div>
      </div>

      <!-- 排名表格 -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        <UTable :data="tableRows" :columns="columns" :ui="{ th: 'text-xs', td: 'text-sm' }">
          <template #rank-cell="{ row }">
            <span
              class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold"
              :class="rankClass(r(row).rank)"
            >
              {{ r(row).rank }}
            </span>
          </template>
          <template #developer-cell="{ row }">
            <NuxtLink
              :to="`/app/kpi/${r(row).user_id}`"
              class="flex items-center gap-2 text-crystal-500 dark:text-crystal-400 hover:text-crystal-700 dark:hover:text-crystal-300 font-medium"
            >
              <img
                v-if="r(row).avatar"
                :src="resolveAvatarUrl(r(row).avatar)"
                class="w-6 h-6 rounded-full"
              />
              <div
                v-else
                class="w-6 h-6 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center text-xs font-semibold text-crystal-600 dark:text-crystal-400"
              >
                {{ (r(row).user_name || '?').slice(0, 1) }}
              </div>
              {{ r(row).user_name }}
            </NuxtLink>
          </template>
          <template #overall-cell="{ row }">
            <span class="font-semibold text-gray-900 dark:text-gray-100">{{ formatScore(r(row).overall) }}</span>
          </template>
          <template #efficiency-cell="{ row }">
            {{ formatScore(r(row).efficiency) }}
          </template>
          <template #output-cell="{ row }">
            {{ formatScore(r(row).output) }}
          </template>
          <template #quality-cell="{ row }">
            {{ formatScore(r(row).quality) }}
          </template>
          <template #capability-cell="{ row }">
            {{ formatScore(r(row).capability) }}
          </template>
          <template #growth-cell="{ row }">
            {{ formatScore(r(row).growth) }}
          </template>
          <template #trend-cell="{ row }">
            <span v-if="r(row).trend > 0" class="text-emerald-500">+{{ r(row).trend.toFixed(1) }}</span>
            <span v-else-if="r(row).trend < 0" class="text-red-500">{{ r(row).trend.toFixed(1) }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
          <template #action-cell="{ row }">
            <NuxtLink :to="`/app/kpi/${r(row).user_id}`">
              <UButton size="xs" variant="ghost" color="primary" trailing-icon="i-heroicons-arrow-right">
                查看详情
              </UButton>
            </NuxtLink>
          </template>
        </UTable>
        <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50 dark:border-gray-800">
          <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ tableRows.length }} 位开发者</span>
        </div>
      </div>
    </template>

    <!-- 无数据 -->
    <div v-else class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-12 text-center">
      <UIcon name="i-heroicons-chart-bar" class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
      <p class="text-gray-500 dark:text-gray-400">暂无 KPI 数据</p>
      <UButton class="mt-4" size="sm" @click="handleRefresh">立即生成</UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { resolveAvatarUrl } = useAvatars()
const toast = useToast()

const loading = ref(true)
const refreshing = ref(false)
const data = ref<any>(null)
const activePeriod = ref('month')
const customStart = ref('')
const customEnd = ref('')
const selectedRole = ref('开发者')

const periods = [
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '季度', value: 'quarter' },
]

const roleOptions = [
  { label: '开发者', value: '开发者' },
  { label: '全部', value: '' },
]

const columns = [
  { accessorKey: 'rank', header: '排名' },
  { accessorKey: 'developer', header: '开发者' },
  { accessorKey: 'overall', header: '综合分' },
  { accessorKey: 'efficiency', header: '效率' },
  { accessorKey: 'output', header: '产出' },
  { accessorKey: 'quality', header: '质量' },
  { accessorKey: 'capability', header: '能力' },
  { accessorKey: 'growth', header: '成长' },
  { accessorKey: 'trend', header: '趋势' },
  { accessorKey: 'action', header: '操作' },
]

const summaryCards = computed(() => {
  if (!data.value?.summary) return []
  const s = data.value.summary
  return [
    { label: '活跃人数', value: s.active_count ?? 0 },
    { label: '已解决问题', value: s.resolved_count ?? 0 },
    { label: '平均解决时间', value: s.avg_resolution_hours != null ? `${s.avg_resolution_hours.toFixed(1)}h` : '-' },
    { label: '团队综合分', value: s.avg_overall_score != null ? s.avg_overall_score.toFixed(1) : '-' },
  ]
})

interface TableRow {
  user_id: number
  user_name: string
  avatar: string
  rank: number
  overall: number
  efficiency: number
  output: number
  quality: number
  capability: number
  growth: number
  trend: number
}

const tableRows = computed<TableRow[]>(() => {
  if (!data.value?.developers) return []
  return data.value.developers.map((d: any, i: number) => ({
    user_id: d.user_id,
    user_name: d.user_name ?? '',
    avatar: d.avatar ?? '',
    rank: d.rankings?.overall_rank ?? i + 1,
    overall: d.scores?.overall ?? 0,
    efficiency: d.scores?.efficiency ?? 0,
    output: d.scores?.output ?? 0,
    quality: d.scores?.quality ?? 0,
    capability: d.scores?.capability ?? 0,
    growth: d.scores?.growth ?? 0,
    trend: d.scores?.trend_delta ?? 0,
  }))
})

function formatScore(v: any) {
  return v != null ? Number(v).toFixed(1) : '-'
}

function r(row: any): TableRow {
  return row.original as TableRow
}

function rankClass(rank: number) {
  if (rank === 1) return 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
  if (rank === 2) return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
  if (rank === 3) return 'bg-orange-100 text-orange-600 dark:bg-orange-900 dark:text-orange-300'
  return 'text-gray-400 dark:text-gray-500'
}

function buildQuery() {
  const params = new URLSearchParams()
  if (customStart.value && customEnd.value) {
    params.set('start', customStart.value)
    params.set('end', customEnd.value)
  } else {
    params.set('period', activePeriod.value)
  }
  if (selectedRole.value) params.set('role', selectedRole.value)
  return params.toString()
}

function applyCustomRange() {
  if (!customStart.value || !customEnd.value) return
  activePeriod.value = ''
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    data.value = await api<any>(`/api/kpi/team/?${buildQuery()}`)
  } catch (e: any) {
    console.error('Failed to load KPI data:', e)
    data.value = null
  } finally {
    loading.value = false
  }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await api('/api/kpi/refresh/', { method: 'POST' })
    toast.add({ title: 'KPI 数据已刷新', color: 'success' })
    await fetchData()
  } catch (e: any) {
    toast.add({ title: '刷新失败', description: e?.data?.detail || e?.response?._data?.detail || '请稍后重试', color: 'error' })
  } finally {
    refreshing.value = false
  }
}

watch([activePeriod, selectedRole], () => {
  if (activePeriod.value) {
    customStart.value = ''
    customEnd.value = ''
  }
  fetchData()
})

onMounted(fetchData)
</script>
