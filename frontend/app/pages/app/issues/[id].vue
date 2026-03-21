<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400">加载中...</div>
  </div>

  <div v-else-if="issue" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <NuxtLink to="/app/issues" class="text-gray-400 hover:text-gray-600">
          <UIcon name="i-heroicons-arrow-left" class="w-5 h-5" />
        </NuxtLink>
        <h1 class="text-2xl font-semibold text-gray-900">#{{ issue.id }}</h1>
        <UBadge :color="priorityColor(issue.priority)" variant="subtle">{{ issue.priority }}</UBadge>
        <UBadge :color="statusColor(issue.status)" variant="subtle">{{ issue.status }}</UBadge>
      </div>
      <div class="flex items-center space-x-2">
        <UButton v-for="action in statusActions" :key="action.label" variant="outline" color="neutral" size="sm" @click="action.handler">{{ action.label }}</UButton>
        <UButton v-if="hasChanges" color="primary" size="sm" :loading="saving" @click="saveAll">保存修改</UButton>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main content -->
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <div class="space-y-4">
            <div class="form-row">
              <label>标题</label>
              <UInput v-model="form.title" />
            </div>
            <div class="form-row">
              <label>描述</label>
              <UTextarea v-model="form.description" :rows="5" />
            </div>
            <div class="form-grid-2">
              <div class="form-row">
                <label>优先级</label>
                <USelect v-model="form.priority" :items="priorityItems" value-key="value" />
              </div>
              <div class="form-row">
                <label>状态</label>
                <USelect v-model="form.status" :items="statusItems" value-key="value" />
              </div>
            </div>
            <div class="form-grid-2">
              <div class="form-row">
                <label>负责人</label>
                <USelect v-model="form.assignee" :items="assigneeItems" placeholder="选择负责人" value-key="value" />
              </div>
              <div class="form-row">
                <label>标签</label>
                <USelectMenu v-model="form.labels" :items="labelItems" multiple placeholder="选择标签" />
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-100 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">分析记录</h3>
          <div class="space-y-4">
            <div class="form-row">
              <label>备注</label>
              <UTextarea v-model="form.remark" :rows="2" placeholder="备注信息" />
            </div>
            <div class="form-row">
              <label>原因分析</label>
              <UTextarea v-model="form.cause" :rows="3" placeholder="问题原因" />
            </div>
            <div class="form-row">
              <label>解决方案</label>
              <UTextarea v-model="form.solution" :rows="3" placeholder="解决办法" />
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-4">
        <div class="bg-white rounded-xl border border-gray-100 p-5 space-y-3">
          <h3 class="text-sm font-semibold text-gray-900">信息</h3>
          <div class="text-sm">
            <span class="text-gray-400">提出人</span>
            <p class="text-gray-900 mt-0.5">{{ issue.reporter_name || '-' }}</p>
          </div>
          <div class="text-sm">
            <span class="text-gray-400">创建时间</span>
            <p class="text-gray-900 mt-0.5">{{ issue.created_at?.slice(0, 10) }}</p>
          </div>
          <div v-if="issue.resolved_at" class="text-sm">
            <span class="text-gray-400">解决时间</span>
            <p class="text-gray-900 mt-0.5">{{ issue.resolved_at.slice(0, 10) }}</p>
          </div>
          <div v-if="issue.resolution_hours" class="text-sm">
            <span class="text-gray-400">解决耗时</span>
            <p class="text-gray-900 mt-0.5">{{ issue.resolution_hours }}h</p>
          </div>
          <div class="form-row">
            <label class="text-gray-400">预计完成</label>
            <UInput v-model="form.estimated_completion" type="date" />
          </div>
          <div class="form-row">
            <label class="text-gray-400">实际工时</label>
            <UInput v-model="form.actual_hours" type="number" placeholder="小时" />
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-100 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900">AI 分析</h3>
            <ServiceStatusDot :online="isOnline('ai')" />
          </div>
          <p class="text-sm text-gray-400">暂无 AI 分析结果</p>
        </div>

        <div class="bg-white rounded-xl border border-gray-100 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900">GitHub 关联</h3>
            <ServiceStatusDot :online="isOnline('github')" />
          </div>
          <p class="text-sm text-gray-400">暂无关联记录</p>
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
const saving = ref(false)
const issue = ref<any>(null)
const users = ref<any[]>([])
const labelItems = ref<string[]>([])

const form = ref({
  title: '',
  description: '',
  priority: 'P2',
  status: '待处理',
  labels: [] as string[],
  assignee: '_none',
  remark: '',
  cause: '',
  solution: '',
  estimated_completion: '',
  actual_hours: '',
})

const priorityItems = [
  { label: 'P0', value: 'P0' },
  { label: 'P1', value: 'P1' },
  { label: 'P2', value: 'P2' },
  { label: 'P3', value: 'P3' },
]
const statusItems = [
  { label: '待处理', value: '待处理' },
  { label: '进行中', value: '进行中' },
  { label: '已解决', value: '已解决' },
  { label: '已关闭', value: '已关闭' },
]
const assigneeItems = computed(() => [
  { label: '无', value: '_none' },
  ...users.value.map(u => ({ label: u.name || u.username, value: String(u.id) })),
])

// Track if form has changes
const originalForm = ref('')
const hasChanges = computed(() => JSON.stringify(form.value) !== originalForm.value)

function populateForm(data: any) {
  form.value = {
    title: data.title || '',
    description: data.description || '',
    priority: data.priority || 'P2',
    status: data.status || '待处理',
    labels: data.labels || [],
    assignee: data.assignee ? String(data.assignee) : '_none',
    remark: data.remark || '',
    cause: data.cause || '',
    solution: data.solution || '',
    estimated_completion: data.estimated_completion || '',
    actual_hours: data.actual_hours != null ? String(data.actual_hours) : '',
  }
  originalForm.value = JSON.stringify(form.value)
}

async function saveAll() {
  if (!issue.value) return
  saving.value = true
  try {
    const body: any = { ...form.value }
    if (body.assignee === '_none') delete body.assignee
    if (!body.estimated_completion) delete body.estimated_completion
    if (body.actual_hours) body.actual_hours = Number(body.actual_hours)
    else delete body.actual_hours
    await api(`/api/issues/${issue.value.id}/`, {
      method: 'PATCH',
      body,
    })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Save failed:', e)
  } finally {
    saving.value = false
  }
}

function priorityColor(p: string) {
  return p === 'P0' ? 'error' : p === 'P1' ? 'warning' : p === 'P2' ? 'warning' : 'neutral'
}
function statusColor(s: string) {
  return s === '待处理' ? 'warning' : s === '进行中' ? 'info' : s === '已解决' ? 'success' : 'neutral'
}

async function updateStatus(newStatus: string) {
  if (!issue.value) return
  try {
    await api(`/api/issues/${issue.value.id}/`, {
      method: 'PATCH',
      body: { status: newStatus },
    })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Status update failed:', e)
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
  const [issueData, usersData, settingsData] = await Promise.all([
    api<any>(`/api/issues/${route.params.id}/`).catch(() => null),
    api<any[]>('/api/users/').catch(() => []),
    api<any>('/api/settings/').catch(() => ({ labels: [] })),
  ])
  issue.value = issueData
  users.value = usersData || []
  labelItems.value = settingsData?.labels || []
  if (issueData) populateForm(issueData)
  loading.value = false
})
</script>

<style scoped>
.form-row { display: flex; flex-direction: column; gap: 0.375rem; }
.form-row label { font-size: 0.8125rem; font-weight: 500; color: #374151; }
.form-row :deep(input),
.form-row :deep(textarea),
.form-row :deep(select),
.form-row :deep(button[role="combobox"]),
.form-row :deep([data-part="trigger"]) { width: 100% !important; }
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
</style>
