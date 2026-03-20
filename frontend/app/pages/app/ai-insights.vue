<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">AI 洞察</h1>
      <div class="flex items-center space-x-2">
        <ServiceStatusDot :online="isOnline('ai')" />
        <span class="text-sm" :class="isOnline('ai') ? 'text-emerald-500' : 'text-gray-400'">{{ isOnline('ai') ? 'AI 服务在线' : 'AI 服务离线' }}</span>
      </div>
    </div>
    <template v-if="isOnline('ai')">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div v-for="alert in insights.trend_alerts" :key="alert.message" class="rounded-xl border p-4" :class="alert.severity === 'critical' ? 'bg-red-50 border-red-100' : 'bg-amber-50 border-amber-100'">
          <div class="flex items-center mb-1">
            <UIcon :name="alert.severity === 'critical' ? 'i-heroicons-exclamation-triangle' : 'i-heroicons-information-circle'" class="w-4 h-4 mr-2" :class="alert.severity === 'critical' ? 'text-red-500' : 'text-amber-500'" />
            <span class="text-sm font-medium" :class="alert.severity === 'critical' ? 'text-red-700' : 'text-amber-700'">{{ alert.metric }}</span>
          </div>
          <p class="text-sm" :class="alert.severity === 'critical' ? 'text-red-600' : 'text-amber-600'">{{ alert.message }}</p>
        </div>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">平均解决时间趋势</h3>
          <ChartsBarChart :x-data="insights.team_efficiency.avg_resolution_trend.map(t => t.month)" :series="[{ name: '平均小时', data: insights.team_efficiency.avg_resolution_trend.map(t => t.hours) }]" :height="260" />
        </div>
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">人均处理量</h3>
          <ChartsBarChart :x-data="insights.team_efficiency.per_person_output.map(p => p.name)" :series="[{ name: '解决数', data: insights.team_efficiency.per_person_output.map(p => p.count) }]" :height="260" />
        </div>
      </div>
      <div class="bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">开发者统计</h3>
        <UTable :data="developerStats" :columns="devColumns" :ui="{ th: 'text-xs', td: 'text-sm' }">
          <template #avg_resolution_hours-cell="{ row }">{{ row.original.avg_resolution_hours ? row.original.avg_resolution_hours + 'h' : '-' }}</template>
          <template #priority_distribution-cell="{ row }">
            <div class="flex gap-1">
              <UBadge v-if="row.original.priority_distribution.P0" color="error" variant="subtle" size="xs">P0: {{ row.original.priority_distribution.P0 }}</UBadge>
              <UBadge v-if="row.original.priority_distribution.P1" color="warning" variant="subtle" size="xs">P1: {{ row.original.priority_distribution.P1 }}</UBadge>
              <UBadge v-if="row.original.priority_distribution.P2" color="warning" variant="subtle" size="xs">P2: {{ row.original.priority_distribution.P2 }}</UBadge>
              <UBadge v-if="row.original.priority_distribution.P3" color="neutral" variant="subtle" size="xs">P3: {{ row.original.priority_distribution.P3 }}</UBadge>
            </div>
          </template>
        </UTable>
      </div>
      <div class="bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">瓶颈识别</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div v-for="b in insights.bottlenecks" :key="b.name" class="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
            <div class="flex items-center">
              <UIcon :name="b.type === 'assignee' ? 'i-heroicons-user' : 'i-heroicons-tag'" class="w-4 h-4 text-gray-400 mr-2" />
              <span class="text-sm text-gray-700">{{ b.name }}</span>
              <UBadge class="ml-2" color="neutral" variant="subtle" size="xs">{{ b.type === 'assignee' ? '负责人' : '标签' }}</UBadge>
            </div>
            <span class="text-sm font-semibold text-amber-600">{{ b.pending_count }} 积压</span>
          </div>
        </div>
      </div>
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
  { accessorKey: 'user_name', header: '开发者' },
  { accessorKey: 'monthly_resolved_count', header: '本月解决数' },
  { accessorKey: 'avg_resolution_hours', header: '平均处理时间' },
  { accessorKey: 'priority_distribution', header: '优先级分布' },
]
</script>
