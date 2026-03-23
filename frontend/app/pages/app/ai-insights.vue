<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">AI 洞察</h1>
      <div class="flex items-center space-x-3">
        <ServiceStatusDot :online="isOnline('ai')" />
        <span class="text-sm" :class="isOnline('ai') ? 'text-emerald-500' : 'text-gray-400'">
          {{ isOnline('ai') ? 'AI 服务在线' : 'AI 服务离线' }}
        </span>
        <UButton
          size="sm"
          variant="ghost"
          icon="i-heroicons-arrow-path"
          :loading="refreshing"
          @click="handleRefresh"
        >
          刷新
        </UButton>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="pending || refreshing" class="bg-white rounded-xl border border-gray-100 p-12 text-center">
      <UIcon name="i-heroicons-cpu-chip" class="w-10 h-10 text-crystal-400 mx-auto mb-3 animate-pulse" />
      <p class="text-gray-600 font-medium">AI 正在分析数据，请稍候...</p>
      <p class="text-sm text-gray-400 mt-1">首次分析可能需要 30 秒左右</p>
    </div>

    <!-- 失败 -->
    <div v-else-if="data?.status === 'failed' || error" class="bg-red-50 rounded-xl border border-red-100 p-6">
      <div class="flex items-center mb-2">
        <UIcon name="i-heroicons-exclamation-circle" class="w-5 h-5 text-red-500 mr-2" />
        <span class="font-medium text-red-700">分析失败</span>
      </div>
      <p class="text-sm text-red-600">{{ data?.error_message || error?.message || '请联系管理员检查 AI 配置' }}</p>
    </div>

    <!-- 无数据 -->
    <div v-else-if="!insights" class="bg-white rounded-xl border border-gray-100 p-12 text-center">
      <UIcon name="i-heroicons-cpu-chip" class="w-12 h-12 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">暂无分析数据</p>
      <UButton class="mt-4" size="sm" @click="handleRefresh">立即生成</UButton>
    </div>

    <!-- 正常展示 -->
    <template v-else>
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

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">平均解决时间趋势</h3>
          <ChartsBarChart
            :x-data="insights.team_efficiency?.avg_resolution_trend?.map((t: any) => t.month) ?? []"
            :series="[{ name: '平均小时', data: insights.team_efficiency?.avg_resolution_trend?.map((t: any) => t.hours) ?? [] }]"
            :height="260"
          />
        </div>
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">人均处理量</h3>
          <ChartsBarChart
            :x-data="insights.team_efficiency?.per_person_output?.map((p: any) => p.name) ?? []"
            :series="[{ name: '解决数', data: insights.team_efficiency?.per_person_output?.map((p: any) => p.count) ?? [] }]"
            :height="260"
          />
        </div>
      </div>

      <div class="bg-white rounded-xl border border-gray-100 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">瓶颈识别</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div
            v-for="b in insights.bottlenecks"
            :key="b.name"
            class="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3"
          >
            <div class="flex items-center">
              <UIcon :name="b.type === 'assignee' ? 'i-heroicons-user' : 'i-heroicons-tag'" class="w-4 h-4 text-gray-400 mr-2" />
              <span class="text-sm text-gray-700">{{ b.name }}</span>
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
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { isOnline } = useServiceStatus()
const { api } = useApi()

const data = ref<any>(null)
const pending = ref(false)
const error = ref<any>(null)
const refreshing = ref(false)

async function fetchInsights() {
  pending.value = true
  error.value = null
  try {
    data.value = await api('/api/ai/insights/?type=team_insights')
  } catch (e) {
    error.value = e
  } finally {
    pending.value = false
  }
}

const insights = computed(() => data.value?.result ?? null)

async function handleRefresh() {
  refreshing.value = true
  try {
    await api('/api/ai/insights/refresh/', { method: 'POST', body: { type: 'team_insights' } })
    await fetchInsights()
  } finally {
    refreshing.value = false
  }
}

onMounted(fetchInsights)
</script>
