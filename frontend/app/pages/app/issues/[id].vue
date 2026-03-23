<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
  </div>

  <div v-else-if="issue" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <NuxtLink to="/app/issues" class="text-gray-400 dark:text-gray-500 hover:text-gray-600">
          <UIcon name="i-heroicons-arrow-left" class="w-5 h-5" />
        </NuxtLink>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">#{{ issue.id }}</h1>
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
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
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

        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">分析记录</h3>
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
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">信息</h3>
          <div class="text-sm">
            <span class="text-gray-400 dark:text-gray-500">提出人</span>
            <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.reporter_name || '-' }}</p>
          </div>
          <div class="text-sm">
            <span class="text-gray-400 dark:text-gray-500">创建时间</span>
            <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.created_at?.slice(0, 10) }}</p>
          </div>
          <div v-if="issue.resolved_at" class="text-sm">
            <span class="text-gray-400 dark:text-gray-500">解决时间</span>
            <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.resolved_at.slice(0, 10) }}</p>
          </div>
          <div v-if="issue.resolution_hours" class="text-sm">
            <span class="text-gray-400 dark:text-gray-500">解决耗时</span>
            <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.resolution_hours }}h</p>
          </div>
          <div class="form-row">
            <label class="text-gray-400 dark:text-gray-500">预计完成</label>
            <UInput v-model="form.estimated_completion" type="date" />
          </div>
          <div class="form-row">
            <label class="text-gray-400 dark:text-gray-500">实际工时</label>
            <UInput v-model="form.actual_hours" type="number" placeholder="小时" />
          </div>
        </div>

        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">AI 分析</h3>
            <ServiceStatusDot :online="isOnline('ai')" />
          </div>
          <p class="text-sm text-gray-400 dark:text-gray-500">暂无 AI 分析结果</p>
        </div>

        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">GitHub 关联</h3>
            <ServiceStatusDot :online="isOnline('github')" />
          </div>

          <!-- 已关联的 GitHub Issues -->
          <div v-if="issue.github_issues?.length" class="space-y-2">
            <div v-for="gh in issue.github_issues" :key="gh.id" class="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg px-3 py-2">
              <div class="min-w-0 flex-1">
                <div class="flex items-center space-x-2">
                  <UBadge :color="gh.state === 'open' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ gh.state }}</UBadge>
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{ gh.repo_full_name }}#{{ gh.github_id }}</span>
                </div>
                <p class="text-sm text-gray-900 dark:text-gray-100 truncate mt-0.5">{{ gh.title }}</p>
              </div>
              <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="xs" @click="unlinkGitHubIssue(gh.id)" />
            </div>
          </div>
          <p v-else class="text-sm text-gray-400 dark:text-gray-500">暂无关联记录</p>

          <!-- 操作按钮 -->
          <div class="flex flex-col gap-2 pt-1">
            <UButton size="xs" variant="outline" color="neutral" icon="i-heroicons-plus" @click="showCreateGH = true" block>
              创建 GitHub Issue
            </UButton>
            <UButton size="xs" variant="outline" color="neutral" icon="i-heroicons-link" @click="showLinkGH = true" block>
              关联已有 Issue
            </UButton>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建 GitHub Issue 弹窗 -->
    <UModal v-model:open="showCreateGH" title="创建 GitHub Issue" :ui="{ width: 'sm:max-w-md' }">
      <template #content>
        <div class="modal-form">
          <div class="modal-header">
            <h3>创建 GitHub Issue</h3>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showCreateGH = false" />
          </div>
          <div class="modal-body">
            <p class="text-sm text-gray-500 dark:text-gray-400">将根据当前问题的标题和描述在 GitHub 仓库创建 Issue，并自动关联。</p>
            <div class="form-row">
              <label>目标仓库 <span class="text-red-400">*</span></label>
              <USelect v-model="ghCreateRepo" :items="repoOptions" placeholder="选择仓库" value-key="value" />
            </div>
            <p v-if="ghCreateError" class="text-sm text-red-500">{{ ghCreateError }}</p>
          </div>
          <div class="modal-footer">
            <UButton variant="outline" color="neutral" @click="showCreateGH = false">取消</UButton>
            <UButton :loading="ghCreating" @click="handleCreateGH">创建</UButton>
          </div>
        </div>
      </template>
    </UModal>

    <!-- 关联已有 GitHub Issue 弹窗 -->
    <UModal v-model:open="showLinkGH" title="关联 GitHub Issue" :ui="{ width: 'sm:max-w-lg' }">
      <template #content>
        <div class="modal-form">
          <div class="modal-header">
            <h3>关联 GitHub Issue</h3>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showLinkGH = false" />
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label>筛选仓库</label>
              <USelect v-model="ghLinkRepoFilter" :items="[{ label: '全部', value: '' }, ...repoOptions]" value-key="value" />
            </div>
            <div class="max-h-60 overflow-y-auto space-y-1 mt-2">
              <div v-for="gh in availableGHIssues" :key="gh.id" class="flex items-center space-x-2 px-2 py-1.5 rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer" @click="toggleGHSelection(gh.id)">
                <UCheckbox :model-value="ghSelectedIds.includes(gh.id)" />
                <div class="min-w-0 flex-1">
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{ gh.repo_full_name }}#{{ gh.github_id }}</span>
                  <p class="text-sm text-gray-900 dark:text-gray-100 truncate">{{ gh.title }}</p>
                </div>
                <UBadge :color="gh.state === 'open' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ gh.state }}</UBadge>
              </div>
              <p v-if="!availableGHIssues.length" class="text-sm text-gray-400 dark:text-gray-500 text-center py-4">没有可关联的 GitHub Issue</p>
            </div>
          </div>
          <div class="modal-footer">
            <UButton variant="outline" color="neutral" @click="showLinkGH = false">取消</UButton>
            <UButton :disabled="!ghSelectedIds.length" :loading="ghLinking" @click="handleLinkGH">关联 ({{ ghSelectedIds.length }})</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>

  <div v-else class="text-center py-20 text-sm text-gray-400 dark:text-gray-500">问题不存在</div>
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
const repos = ref<any[]>([])
const allGHIssues = ref<any[]>([])

// GitHub 创建
const showCreateGH = ref(false)
const ghCreateRepo = ref('')
const ghCreating = ref(false)
const ghCreateError = ref('')

// GitHub 关联
const showLinkGH = ref(false)
const ghLinkRepoFilter = ref('')
const ghSelectedIds = ref<number[]>([])
const ghLinking = ref(false)

const repoOptions = computed(() => repos.value.map(r => ({ label: r.full_name, value: String(r.id) })))

const linkedGHIds = computed(() => new Set((issue.value?.github_issues || []).map((g: any) => g.id)))

const availableGHIssues = computed(() => {
  return allGHIssues.value.filter(gh => {
    if (linkedGHIds.value.has(gh.id)) return false
    if (ghLinkRepoFilter.value && String(gh.repo) !== ghLinkRepoFilter.value) return false
    return true
  })
})

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

async function closeWithGitHub() {
  if (!issue.value) return
  try {
    await api(`/api/issues/${issue.value.id}/close-with-github/`, { method: 'POST' })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Close failed:', e)
  }
}

const statusActions = computed(() => {
  if (!issue.value) return []
  const s = issue.value.status
  const actions: { label: string; handler: () => void }[] = []
  if (s === '待处理') actions.push({ label: '开始处理', handler: () => updateStatus('进行中') })
  if (s === '进行中') actions.push({ label: '标记已解决', handler: () => updateStatus('已解决') })
  if (s === '已解决') {
    const hasOpenGH = issue.value.github_issues?.some((gh: any) => gh.state === 'open')
    if (hasOpenGH) {
      actions.push({ label: '关闭（含 GitHub）', handler: closeWithGitHub })
    } else {
      actions.push({ label: '关闭', handler: () => updateStatus('已关闭') })
    }
  }
  return actions
})

function toggleGHSelection(id: number) {
  const idx = ghSelectedIds.value.indexOf(id)
  if (idx >= 0) ghSelectedIds.value.splice(idx, 1)
  else ghSelectedIds.value.push(id)
}

async function handleCreateGH() {
  if (!ghCreateRepo.value) {
    ghCreateError.value = '请选择仓库'
    return
  }
  ghCreating.value = true
  ghCreateError.value = ''
  try {
    await api(`/api/issues/${issue.value.id}/github-create/`, {
      method: 'POST',
      body: { repo: ghCreateRepo.value },
    })
    showCreateGH.value = false
    ghCreateRepo.value = ''
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e: any) {
    ghCreateError.value = e?.data?.detail || 'GitHub 创建失败'
  } finally {
    ghCreating.value = false
  }
}

async function handleLinkGH() {
  if (!ghSelectedIds.value.length) return
  ghLinking.value = true
  try {
    await api(`/api/issues/${issue.value.id}/github-link/`, {
      method: 'POST',
      body: { github_issue_ids: ghSelectedIds.value },
    })
    showLinkGH.value = false
    ghSelectedIds.value = []
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Link failed:', e)
  } finally {
    ghLinking.value = false
  }
}

async function unlinkGitHubIssue(ghId: number) {
  try {
    await api(`/api/issues/${issue.value.id}/github-link/`, {
      method: 'DELETE',
      body: { github_issue_ids: [ghId] },
    })
    issue.value = await api<any>(`/api/issues/${route.params.id}/`)
    populateForm(issue.value)
  } catch (e) {
    console.error('Unlink failed:', e)
  }
}

async function fetchGHIssues() {
  allGHIssues.value = await api<any[]>('/api/repos/github-issues/').catch(() => []) || []
}

onMounted(async () => {
  const [issueData, usersData, settingsData, reposData] = await Promise.all([
    api<any>(`/api/issues/${route.params.id}/`).catch(() => null),
    api<any[]>('/api/users/').catch(() => []),
    api<any>('/api/settings/').catch(() => ({ labels: [] })),
    api<any[]>('/api/repos/').catch(() => []),
  ])
  issue.value = issueData
  users.value = usersData?.results || usersData || []
  labelItems.value = settingsData?.labels || []
  repos.value = reposData?.results || reposData || []
  if (issueData) populateForm(issueData)
  loading.value = false
  // 异步加载 GitHub Issues 列表（用于关联弹窗）
  fetchGHIssues()
})
</script>

<style scoped>
.form-row { display: flex; flex-direction: column; gap: 0.375rem; }
.form-row label { font-size: 0.8125rem; font-weight: 500; color: #374151; }
:root.dark .form-row label { color: #9ca3af; }
.form-row :deep(input),
.form-row :deep(textarea),
.form-row :deep(select),
.form-row :deep(button[role="combobox"]),
.form-row :deep([data-part="trigger"]) { width: 100% !important; }
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.modal-form { padding: 1.5rem 2rem; }
.modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
.modal-header h3 { font-size: 1.125rem; font-weight: 600; color: #111827; }
:root.dark .modal-header h3 { color: #f3f4f6; }
.modal-body { display: flex; flex-direction: column; gap: 1rem; }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #f3f4f6; }
:root.dark .modal-footer { border-top-color: #374151; }
</style>
