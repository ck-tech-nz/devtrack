<template>
  <div class="space-y-6">
    <!-- 头部 -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">团队计划管理</h1>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- 月份选择 -->
        <UButtonGroup>
          <UButton
            size="sm"
            variant="outline"
            color="neutral"
            icon="i-heroicons-chevron-left"
            @click="prevMonth"
          />
          <UButton size="sm" variant="outline" color="neutral" class="min-w-28 pointer-events-none">
            {{ period }}
          </UButton>
          <UButton
            size="sm"
            variant="outline"
            color="neutral"
            icon="i-heroicons-chevron-right"
            @click="nextMonth"
          />
        </UButtonGroup>

        <!-- 批量生成 -->
        <UButton
          size="sm"
          icon="i-heroicons-sparkles"
          :loading="batchGenerating"
          @click="batchGenerate"
        >
          批量生成草案
        </UButton>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <!-- 计划列表 -->
    <div v-else class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
      <UTable :data="tableRows" :columns="columns" :ui="{ th: 'text-xs', td: 'text-sm' }">
        <!-- 用户列 -->
        <template #user-cell="{ row }">
          <div class="flex items-center gap-2">
            <img
              v-if="r(row).avatar"
              :src="resolveAvatarUrl(r(row).avatar)"
              class="w-7 h-7 rounded-full flex-shrink-0"
            />
            <div
              v-else
              class="w-7 h-7 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center text-xs font-semibold text-crystal-600 dark:text-crystal-400 flex-shrink-0"
            >
              {{ (r(row).user_name || '?').slice(0, 1) }}
            </div>
            <span class="font-medium text-gray-900 dark:text-gray-100">{{ r(row).user_name }}</span>
          </div>
        </template>

        <!-- 状态列 -->
        <template #status-cell="{ row }">
          <UBadge
            v-if="r(row).plan_id"
            :color="statusColor(r(row).status)"
            variant="subtle"
            size="xs"
          >
            {{ statusLabel(r(row).status) }}
          </UBadge>
          <span v-else class="text-gray-300 dark:text-gray-600 text-xs">暂无计划</span>
        </template>

        <!-- 行动项数 -->
        <template #items_count-cell="{ row }">
          <span v-if="r(row).plan_id" class="text-gray-700 dark:text-gray-300">
            {{ r(row).items_count ?? '-' }}
          </span>
          <span v-else class="text-gray-300 dark:text-gray-600">-</span>
        </template>

        <!-- 总积分 -->
        <template #total_points-cell="{ row }">
          <span v-if="r(row).plan_id" class="font-medium text-gray-900 dark:text-gray-100">
            {{ r(row).total_points ?? '-' }}
          </span>
          <span v-else class="text-gray-300 dark:text-gray-600">-</span>
        </template>

        <!-- 已得积分 -->
        <template #earned_points-cell="{ row }">
          <span v-if="r(row).plan_id" class="font-medium text-emerald-600 dark:text-emerald-400">
            {{ r(row).earned_points ?? '-' }}
          </span>
          <span v-else class="text-gray-300 dark:text-gray-600">-</span>
        </template>

        <!-- 操作列 -->
        <template #actions-cell="{ row }">
          <div class="flex items-center gap-1.5 flex-wrap">
            <!-- 无计划：生成 -->
            <UButton
              v-if="!r(row).plan_id"
              size="xs"
              variant="outline"
              color="primary"
              icon="i-heroicons-sparkles"
              :loading="generatingIds.has(r(row).user_id)"
              @click="generatePlan(r(row).user_id)"
            >
              生成
            </UButton>

            <!-- draft: 编辑 + 发布 -->
            <template v-else-if="r(row).status === 'draft'">
              <NuxtLink :to="`/app/ai/plans/${r(row).plan_id}`">
                <UButton size="xs" variant="outline" color="neutral" icon="i-heroicons-pencil-square">
                  编辑
                </UButton>
              </NuxtLink>
              <UButton
                size="xs"
                variant="outline"
                color="success"
                icon="i-heroicons-paper-airplane"
                :loading="publishingIds.has(r(row).plan_id)"
                @click="publishPlan(r(row).plan_id)"
              >
                发布
              </UButton>
            </template>

            <!-- published: 编辑 + 归档 -->
            <template v-else-if="r(row).status === 'published'">
              <NuxtLink :to="`/app/ai/plans/${r(row).plan_id}`">
                <UButton size="xs" variant="outline" color="neutral" icon="i-heroicons-pencil-square">
                  编辑
                </UButton>
              </NuxtLink>
              <UButton
                size="xs"
                variant="outline"
                color="neutral"
                icon="i-heroicons-archive-box"
                :loading="archivingIds.has(r(row).plan_id)"
                @click="archivePlan(r(row).plan_id)"
              >
                归档
              </UButton>
            </template>

            <!-- archived: 查看 -->
            <template v-else-if="r(row).status === 'archived'">
              <NuxtLink :to="`/app/ai/plans/${r(row).plan_id}`">
                <UButton size="xs" variant="ghost" color="neutral" icon="i-heroicons-eye">
                  查看
                </UButton>
              </NuxtLink>
            </template>
          </div>
        </template>
      </UTable>

      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50 dark:border-gray-800">
        <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ tableRows.length }} 位成员</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { resolveAvatarUrl } = useAvatars()
const toast = useToast()

const period = ref(new Date().toISOString().slice(0, 7)) // "2026-04"
const plans = ref<any[]>([])
const loading = ref(true)
const batchGenerating = ref(false)
const generatingIds = ref(new Set<number>())
const publishingIds = ref(new Set<string>())
const archivingIds = ref(new Set<string>())

const columns = [
  { accessorKey: 'user', header: '成员' },
  { accessorKey: 'status', header: '状态' },
  { accessorKey: 'items_count', header: '行动项数' },
  { accessorKey: 'total_points', header: '总积分' },
  { accessorKey: 'earned_points', header: '已得积分' },
  { accessorKey: 'actions', header: '操作' },
]

interface PlanRow {
  user_id: number
  user_name: string
  avatar: string
  plan_id: string | null
  status: string | null
  items_count: number | null
  total_points: number | null
  earned_points: number | null
}

const tableRows = computed<PlanRow[]>(() => {
  return plans.value.map((p: any) => ({
    user_id: p.user?.id ?? p.user_id,
    user_name: p.user?.name || p.user?.username || p.user_name || '',
    avatar: p.user?.avatar || p.avatar || '',
    plan_id: p.id ?? null,
    status: p.status ?? null,
    items_count: p.action_items_count ?? p.items_count ?? null,
    total_points: p.total_points ?? null,
    earned_points: p.earned_points ?? null,
  }))
})

function r(row: any): PlanRow {
  return row.original as PlanRow
}

function statusLabel(status: string | null) {
  const map: Record<string, string> = {
    draft: '草案',
    published: '已发布',
    archived: '已归档',
  }
  return status ? (map[status] ?? status) : '-'
}

function statusColor(status: string | null): any {
  if (status === 'published') return 'success'
  if (status === 'archived') return 'neutral'
  return 'neutral' // draft
}

function prevMonth() {
  const [y, m] = period.value.split('-').map(Number)
  const d = new Date(y, m - 2, 1)
  period.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function nextMonth() {
  const [y, m] = period.value.split('-').map(Number)
  const d = new Date(y, m, 1)
  period.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

async function fetchPlans() {
  loading.value = true
  try {
    plans.value = await api<any[]>(`/api/kpi/plans/?period=${period.value}`)
  } catch {
    plans.value = []
  } finally {
    loading.value = false
  }
}

async function generatePlan(userId: number) {
  generatingIds.value = new Set([...generatingIds.value, userId])
  try {
    await api('/api/kpi/plans/generate/', { method: 'POST', body: { user_id: userId } })
    toast.add({ title: '草案已生成', color: 'success' })
    await fetchPlans()
  } catch (e: any) {
    toast.add({ title: '生成失败', description: e?.data?.detail || '', color: 'error' })
  } finally {
    generatingIds.value = new Set([...generatingIds.value].filter(id => id !== userId))
  }
}

async function publishPlan(planId: string) {
  publishingIds.value = new Set([...publishingIds.value, planId])
  try {
    await api(`/api/kpi/plans/${planId}/publish/`, { method: 'POST' })
    toast.add({ title: '已发布', color: 'success' })
    await fetchPlans()
  } catch (e: any) {
    toast.add({ title: '发布失败', description: e?.data?.detail || '', color: 'error' })
  } finally {
    publishingIds.value = new Set([...publishingIds.value].filter(id => id !== planId))
  }
}

async function archivePlan(planId: string) {
  archivingIds.value = new Set([...archivingIds.value, planId])
  try {
    await api(`/api/kpi/plans/${planId}/archive/`, { method: 'POST' })
    toast.add({ title: '已归档', color: 'success' })
    await fetchPlans()
  } catch (e: any) {
    toast.add({ title: '归档失败', description: e?.data?.detail || '', color: 'error' })
  } finally {
    archivingIds.value = new Set([...archivingIds.value].filter(id => id !== planId))
  }
}

async function batchGenerate() {
  batchGenerating.value = true
  try {
    await api('/api/kpi/plans/generate/', { method: 'POST', body: {} })
    toast.add({ title: '批量草案已生成', color: 'success' })
    await fetchPlans()
  } catch (e: any) {
    toast.add({ title: '批量生成失败', description: e?.data?.detail || '', color: 'error' })
  } finally {
    batchGenerating.value = false
  }
}

watch(period, fetchPlans)
onMounted(fetchPlans)
</script>
