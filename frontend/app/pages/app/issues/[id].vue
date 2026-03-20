<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400">加载中...</div>
  </div>

  <div v-else-if="issue" class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <div class="flex items-center space-x-3">
          <h1 class="text-2xl font-semibold text-gray-900">{{ issue.display_id }}</h1>
          <UBadge :color="priorityColor(issue.priority)" variant="subtle">{{ issue.priority }}</UBadge>
          <UBadge :color="statusColor(issue.status)" variant="subtle">{{ issue.status }}</UBadge>
        </div>
        <p class="text-lg text-gray-700 mt-1">{{ issue.title }}</p>
      </div>
    </div>
    <div class="flex items-center space-x-3">
      <UButton v-for="action in statusActions" :key="action.label" variant="outline" color="neutral" size="sm" @click="action.handler">{{ action.label }}</UButton>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">问题描述</h3>
          <p class="text-sm text-gray-600 leading-relaxed">{{ issue.description || '暂无描述' }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-gray-900">AI 分析</h3>
            <ServiceStatusDot :online="isOnline('ai')" />
          </div>
          <div class="text-sm text-gray-400">暂无 AI 分析结果</div>
        </div>
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-gray-900">GitHub 关联</h3>
            <ServiceStatusDot :online="isOnline('github')" />
          </div>
          <div class="text-sm text-gray-400">暂无关联的 GitHub 记录</div>
        </div>
        <div v-if="issue.cause || issue.solution" class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">分析记录</h3>
          <div class="space-y-3">
            <div v-if="issue.cause"><span class="text-xs text-gray-400">原因分析</span><p class="text-sm text-gray-600 mt-1">{{ issue.cause }}</p></div>
            <div v-if="issue.solution"><span class="text-xs text-gray-400">解决办法</span><p class="text-sm text-gray-600 mt-1">{{ issue.solution }}</p></div>
          </div>
        </div>
      </div>
      <div class="space-y-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
          <div><span class="text-xs text-gray-400">负责人</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.assignee_name || '-' }}</p></div>
          <div><span class="text-xs text-gray-400">提出人</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.reporter_name || '-' }}</p></div>
          <div><span class="text-xs text-gray-400">标签</span><div class="flex flex-wrap gap-1 mt-1"><UBadge v-for="l in (issue.labels || [])" :key="l" color="neutral" variant="subtle" size="xs">{{ l }}</UBadge></div></div>
          <div><span class="text-xs text-gray-400">创建时间</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.created_at ? issue.created_at.slice(0, 10) : '-' }}</p></div>
          <div v-if="issue.resolved_at"><span class="text-xs text-gray-400">解决时间</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.resolved_at.slice(0, 10) }}</p></div>
          <div v-if="issue.resolution_hours"><span class="text-xs text-gray-400">解决耗时</span><p class="text-sm text-gray-900 mt-0.5">{{ issue.resolution_hours }} 小时</p></div>
          <div v-if="issue.remark"><span class="text-xs text-gray-400">备注</span><p class="text-sm text-gray-700 mt-0.5">{{ issue.remark }}</p></div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="text-center py-20 text-sm text-gray-400">问题不存在</div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const route = useRoute()
const { isOnline } = useServiceStatus()

const loading = ref(true)
const issue = ref<any>(null)

function priorityColor(p: string) {
  return p === 'P0' ? 'error' : p === 'P1' ? 'warning' : p === 'P2' ? 'warning' : 'neutral'
}
function statusColor(s: string) {
  return s === '待处理' ? 'warning' : s === '进行中' ? 'info' : s === '已解决' ? 'success' : 'neutral'
}

async function loadIssue() {
  try {
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
  } catch (e) {
    console.error('Failed to load issue:', e)
    issue.value = null
  }
}

async function updateStatus(newStatus: string) {
  if (!issue.value) return
  try {
    await api(`/api/issues/${issue.value.id}/`, {
      method: 'PATCH',
      body: { status: newStatus },
    })
    await loadIssue()
  } catch (e) {
    console.error('Failed to update status:', e)
  }
}

const statusActions = computed(() => {
  if (!issue.value) return []
  const s = issue.value.status
  const actions: { label: string; handler: () => void }[] = []
  if (s === '待处理') actions.push({ label: '开始处理', handler: () => updateStatus('进行中') })
  if (s === '进行中') actions.push({ label: '标记已解决', handler: () => updateStatus('已解决') })
  if (s === '已解决') actions.push({ label: '关闭', handler: () => updateStatus('已关闭') })
  return actions
})

onMounted(async () => {
  await loadIssue()
  loading.value = false
})
</script>
