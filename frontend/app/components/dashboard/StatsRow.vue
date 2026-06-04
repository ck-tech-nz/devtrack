<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <DashboardStatCard
      label="本周已解决" :value="stats.resolved_this_week" icon="i-heroicons-check-circle"
      tone="success" :delta="resolvedDelta" delta-label="较上周" delta-unit="percent"
      positive-direction="up" to="/app/issues?status=已解决"
    />
    <DashboardStatCard
      label="待分配" :value="stats.pending" icon="i-heroicons-clock"
      tone="warning" :delta="pendingDelta" delta-label="较昨日" delta-unit="absolute"
      positive-direction="down" to="/app/issues?status=待分配"
    />
    <DashboardStatCard
      label="进行中" :value="stats.in_progress" icon="i-heroicons-arrow-path"
      tone="info" :delta="null" to="/app/issues?status=进行中"
    />
    <DashboardStatCard
      label="总 Issue 数" :value="stats.total" icon="i-heroicons-bug-ant"
      tone="primary" :delta="totalAddedDelta" delta-label="本周新增" delta-unit="absolute"
      positive-direction="up" to="/app/issues"
    />
  </div>
</template>

<script setup lang="ts">
interface Stats {
  total: number
  pending: number
  in_progress: number
  resolved_this_week: number
  resolved_prev_week: number
  pending_yesterday: number
  total_added_this_week: number
}
const props = defineProps<{ stats: Stats }>()

// 已解决环比:(本周 - 上周) / 上周 * 100
const resolvedDelta = computed<number | null>(() => {
  const cur = props.stats.resolved_this_week
  const prev = props.stats.resolved_prev_week
  if (!prev) return cur > 0 ? 100 : null
  return Math.round(((cur - prev) / prev) * 100)
})
// 待分配日环比(绝对差)
const pendingDelta = computed<number | null>(() => {
  const diff = props.stats.pending - props.stats.pending_yesterday
  return diff === 0 ? null : diff
})
// 总数本周新增(绝对值)
const totalAddedDelta = computed<number | null>(() =>
  props.stats.total_added_this_week > 0 ? props.stats.total_added_this_week : null,
)
</script>
