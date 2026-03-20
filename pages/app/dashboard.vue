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
