<template>
  <div class="space-y-6">
    <MyPendingTasks />
    <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <h1 class="text-xl md:text-2xl font-semibold text-gray-900 dark:text-gray-100">问题跟踪</h1>
      <div class="flex items-center justify-between md:justify-end space-x-3">
        <label class="flex items-center gap-1.5 cursor-pointer select-none">
          <USwitch v-model="showCompleted" size="xs" />
          <span class="text-xs text-gray-500 dark:text-gray-400">查看已完成</span>
        </label>
        <div class="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
          <button
            class="px-4 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="viewMode === 'kanban' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
            @click="viewMode = 'kanban'"
          >
            看板
          </button>
          <button
            class="px-4 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="viewMode === 'table' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
            @click="viewMode = 'table'"
          >
            列表
          </button>
        </div>
        <UButton icon="i-heroicons-plus" size="sm" @click="showCreateModal = true">
          <span class="hidden md:inline">新建问题</span>
        </UButton>
      </div>
    </div>

    <!-- Create Issue Modal -->
    <UModal v-model:open="showCreateModal" title="新建问题" :ui="{ content: 'sm:max-w-[960px]' }">
      <template #content>
        <div class="modal-form">
          <div class="modal-header">
            <h3>新建问题</h3>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="closeCreateModal" />
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label>项目</label>
              <USelect v-model="newIssue.project" :items="projectOptions" placeholder="选择项目" value-key="value" />
            </div>
            <div v-if="projectRepos.length > 1" class="form-row">
              <label>关联仓库</label>
              <USelect v-model="newIssue.repo" :items="projectRepoOptions" placeholder="选择仓库" value-key="value" />
            </div>
            <div class="form-row">
              <label>标题 <span class="text-red-400">*</span></label>
              <UInput v-model="newIssue.title" placeholder="输入问题标题" />
            </div>
            <div class="form-row">
              <label>描述</label>
              <MarkdownEditor v-model="newIssue.description" placeholder="详细描述问题" />
            </div>
            <div class="form-grid-2">
              <div class="form-row">
                <label>优先级</label>
                <USelect v-model="newIssue.priority" :items="createPriorityOptions" value-key="value" />
              </div>
              <div class="form-row">
                <label>状态</label>
                <USelect v-model="newIssue.status" :items="createStatusOptions" value-key="value" />
              </div>
            </div>
            <div class="form-grid-2">
              <div class="form-row">
                <label>标签</label>
                <USelectMenu v-model="newIssue.labels" :items="labelOptions" multiple placeholder="选择标签" />
              </div>
              <div class="form-row">
                <label>负责人</label>
                <USelect v-model="newIssue.assignee" :items="createAssigneeOptions" placeholder="选择负责人" value-key="value" />
              </div>
            </div>
            <p v-if="createError" class="text-sm text-red-500">{{ createError }}</p>
          </div>
          <div class="modal-footer">
            <UButton variant="outline" color="neutral" @click="closeCreateModal">取消</UButton>
            <UButton :loading="creating" @click="handleCreateIssue">创建</UButton>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Batch Actions -->
    <div v-if="selectedRowsData.length > 0" class="hidden md:flex bg-crystal-50 dark:bg-crystal-950 rounded-xl border border-crystal-100 dark:border-crystal-800 p-3 items-center justify-between">
      <span class="text-sm text-crystal-700 dark:text-crystal-300">已选择 {{ selectedRowsData.length }} 项</span>
      <div class="flex items-center space-x-2">
        <UDropdownMenu :items="batchAssignItems" :content="{ align: 'end' as const }">
          <UButton size="xs" color="primary" variant="outline">批量分配</UButton>
        </UDropdownMenu>
        <UDropdownMenu :items="batchPriorityItems" :content="{ align: 'end' as const }">
          <UButton size="xs" color="primary" variant="outline">修改优先级</UButton>
        </UDropdownMenu>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <!-- Mobile Card List -->
    <div v-else-if="isMobile && viewMode === 'table'" class="space-y-2">
      <IssueCard v-for="issue in issues" :key="issue.id" :issue="issue" />
      <div class="flex items-center justify-between pt-2">
        <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ totalCount }} 条</span>
        <div class="flex items-center space-x-2">
          <UButton size="xs" variant="ghost" color="neutral" :disabled="page <= 1" @click="page--">上一页</UButton>
          <span class="text-xs text-gray-500 dark:text-gray-400">{{ page }} / {{ totalPages }}</span>
          <UButton size="xs" variant="ghost" color="neutral" :disabled="page >= totalPages" @click="page++">下一页</UButton>
        </div>
      </div>
    </div>

    <!-- Kanban View -->
    <SharedKanbanBoard
      v-else-if="viewMode === 'kanban'"
      :columns="kanbanColumns"
      :item-key="(item: any) => item.id"
      @drop="onKanbanDrop"
    >
      <template #card="{ item }">
        <NuxtLink :to="`/app/issues/${item.id}`" class="block">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs text-gray-400 dark:text-gray-500">#{{ item.id }}</span>
            <UBadge
              :color="item.priority === 'P0' ? 'error' : item.priority === 'P1' ? 'warning' : item.priority === 'P2' ? 'warning' : 'neutral'"
              variant="subtle"
              size="xs"
            >
              {{ item.priority }}
            </UBadge>
          </div>
          <p class="text-sm text-gray-900 dark:text-gray-100 font-medium line-clamp-2">{{ item.title }}</p>
          <div class="mt-2 flex items-center">
            <div class="w-5 h-5 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center">
              <span class="text-crystal-600 dark:text-crystal-400 text-[10px] font-medium">{{ (item.assignee_name || '?').slice(0, 1) }}</span>
            </div>
            <span class="ml-1.5 text-xs text-gray-400 dark:text-gray-500">{{ item.assignee_name || '-' }}</span>
          </div>
        </NuxtLink>
      </template>
    </SharedKanbanBoard>

    <!-- Table View -->
    <div v-else class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
      <div class="flex justify-end px-4 py-2 border-b border-gray-50 dark:border-gray-800">
        <label class="flex items-center gap-1.5 cursor-pointer select-none">
          <USwitch v-model="showGHColumn" size="xs" />
          <span class="text-xs text-gray-500 dark:text-gray-400">GitHub Issues</span>
        </label>
      </div>
      <UTable
        v-model:row-selection="rowSelection"
        :data="issues"
        :columns="columns"
        :ui="{ th: 'text-xs whitespace-nowrap', td: 'text-sm' }"
      >
        <template #select-header="{ table }">
          <UCheckbox
            :model-value="table.getIsAllPageRowsSelected()"
            @update:model-value="(v: boolean) => table.toggleAllPageRowsSelected(!!v)"
          />
        </template>
        <template #select-cell="{ row }">
          <UCheckbox
            :model-value="row.getIsSelected()"
            @update:model-value="(v: boolean) => row.toggleSelected(!!v)"
          />
        </template>
        <template #id-cell="{ row }">
          <NuxtLink :to="`/app/issues/${row.original.id}`" class="text-crystal-500 dark:text-crystal-400 hover:text-crystal-700 dark:hover:text-crystal-300 font-medium">{{ row.original.id }}</NuxtLink>
        </template>
        <template #title-cell="{ row }">
          <EditableCell :value="row.original.title" @save="(v: string) => inlineUpdate(row.original.id, 'title', v)" />
        </template>
        <template #priority-cell="{ row }">
          <UBadge :color="priorityColor(row.original.priority)" variant="subtle" size="sm">{{ row.original.priority }}</UBadge>
        </template>
        <template #status-cell="{ row }">
          <div class="flex flex-col items-start gap-1">
            <UBadge :color="statusColor(row.original.status)" variant="subtle" size="sm">{{ row.original.status }}</UBadge>
            <UBadge v-if="analyzingIssueIds.has(row.original.id)" color="info" variant="subtle" size="sm" class="whitespace-nowrap">
              <UIcon name="i-heroicons-cpu-chip" class="w-3.5 h-3.5 animate-spin mr-0.5" />AI 分析中
            </UBadge>
          </div>
        </template>
        <template #assignee_name-cell="{ row }">
          {{ row.original.assignee_name || '-' }}
        </template>
        <template #reporter_name-cell="{ row }">
          {{ row.original.reporter_name || '-' }}
        </template>
        <template #remark-cell="{ row }">
          <EditableCell :value="row.original.remark" @save="(v: string) => inlineUpdate(row.original.id, 'remark', v)" />
        </template>
        <template #cause-cell="{ row }">
          <EditableCell :value="row.original.cause" @save="(v: string) => inlineUpdate(row.original.id, 'cause', v)" />
        </template>
        <template #solution-cell="{ row }">
          <EditableCell :value="row.original.solution" @save="(v: string) => inlineUpdate(row.original.id, 'solution', v)" />
        </template>
        <template #created_at-cell="{ row }">
          {{ row.original.created_at ? row.original.created_at.slice(0, 10) : '-' }}
        </template>
        <template #resolution_hours-cell="{ row }">
          {{ row.original.resolution_hours ? row.original.resolution_hours + 'h' : '-' }}
        </template>
        <template #github_issues-cell="{ row }">
          <div v-if="row.original.github_issues?.length" class="flex flex-wrap gap-1">
            <NuxtLink
              v-for="gh in row.original.github_issues"
              :key="gh.id"
              :to="`/app/repos/${gh.repo}/issues/${gh.id}`"
              class="text-xs text-crystal-500 dark:text-crystal-400 hover:underline"
            >#{{ gh.github_id }}</NuxtLink>
          </div>
          <span v-else class="text-gray-300 dark:text-gray-600">-</span>
        </template>
      </UTable>
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50 dark:border-gray-800">
        <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ totalCount }} 条</span>
        <div class="flex items-center space-x-2">
          <UButton size="xs" variant="ghost" color="neutral" :disabled="page <= 1" @click="page--">上一页</UButton>
          <span class="text-xs text-gray-500 dark:text-gray-400">{{ page }} / {{ totalPages }}</span>
          <UButton size="xs" variant="ghost" color="neutral" :disabled="page >= totalPages" @click="page++">下一页</UButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { user } = useAuth()
const { isMobile } = useMobile()
const { settings, update: updateSettings } = useUserSettings()

const viewMode = computed({
  get: () => settings.value.issues_view_mode,
  set: (v: 'kanban' | 'table') => updateSettings('issues_view_mode', v),
})
const showCompleted = ref(false)
const page = ref(1)
const pageSize = 15
const rowSelection = ref<Record<string, boolean>>({})

const loading = ref(true)
const issues = ref<any[]>([])
const analyzingIssueIds = ref<Set<number>>(new Set())
const totalCount = ref(0)
const users = ref<any[]>([])
const labelOptions = ref<string[]>([])
const projects = ref<any[]>([])
const repos = ref<any[]>([])

// Create issue modal state
const showCreateModal = ref(false)
const creating = ref(false)
const createError = ref('')
const defaultAssignee = computed(() => user.value?.id ? String(user.value.id) : '_none')
const newIssue = ref({
  project: '',
  title: '',
  description: '',
  priority: 'P2',
  status: '待处理',
  labels: [] as string[],
  assignee: defaultAssignee.value,
  repo: null as string | null,
})

const projectRepos = ref<any[]>([])

watch(() => newIssue.value.project, (projectId) => {
  if (!projectId) {
    projectRepos.value = []
    newIssue.value.repo = null
    return
  }
  const project = projects.value.find(p => String(p.id) === String(projectId))
  const repoIds: string[] = (project?.repos || []).map((r: any) => String(r))
  projectRepos.value = repos.value.filter(r => repoIds.includes(String(r.id)))
  if (projectRepos.value.length === 1) {
    newIssue.value.repo = String(projectRepos.value[0].id)
  } else {
    newIssue.value.repo = null
  }
})

const projectRepoOptions = computed(() => projectRepos.value.map(r => ({ label: r.name, value: String(r.id) })))

const projectOptions = computed(() => projects.value.map(p => ({ label: p.name, value: String(p.id) })))
const createPriorityOptions = [{ label: 'P0', value: 'P0' }, { label: 'P1', value: 'P1' }, { label: 'P2', value: 'P2' }, { label: 'P3', value: 'P3' }]
const createStatusOptions = [{ label: '待处理', value: '待处理' }, { label: '进行中', value: '进行中' }, { label: '已解决', value: '已解决' }, { label: '已关闭', value: '已关闭' }]
const createAssigneeOptions = computed(() => [{ label: '无', value: '_none' }, ...users.value.map(u => ({ label: u.name || u.username, value: String(u.id) }))])

function closeCreateModal() {
  showCreateModal.value = false
  newIssue.value = { project: '', title: '', description: '', priority: 'P2', status: '待处理', labels: [], assignee: defaultAssignee.value, repo: null }
  projectRepos.value = []
}

async function handleCreateIssue() {
  if (!newIssue.value.title.trim()) {
    createError.value = '标题不能为空'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const body: any = {
      title: newIssue.value.title,
      description: newIssue.value.description,
      priority: newIssue.value.priority,
      status: newIssue.value.status,
      labels: newIssue.value.labels,
    }
    if (newIssue.value.project) body.project = newIssue.value.project
    if (newIssue.value.assignee && newIssue.value.assignee !== '_none') body.assignee = newIssue.value.assignee
    if (newIssue.value.repo) body.repo = newIssue.value.repo
    await api('/api/issues/', { method: 'POST', body, format: 'json' })
    showCreateModal.value = false
    newIssue.value = { project: '', title: '', description: '', priority: 'P2', status: '待处理', labels: [], assignee: defaultAssignee.value, repo: null }
    projectRepos.value = []
    await fetchIssues()
  } catch (e: any) {
    createError.value = formatApiError(e, '创建失败，请重试')
  } finally {
    creating.value = false
  }
}

const selectedRowsData = computed(() => {
  return Object.entries(rowSelection.value)
    .filter(([_, selected]) => selected)
    .map(([idx]) => issues.value[parseInt(idx)])
    .filter(Boolean)
})

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))

const showGHColumn = ref(false)

const columns = computed(() => {
  const cols = [
    { id: 'select', header: '', cell: '' },
    { accessorKey: 'id', header: 'ID' },
    { accessorKey: 'title', header: '标题' },
    { accessorKey: 'assignee_name', header: '负责人' },
    { accessorKey: 'cause', header: '原因分析' },
    { accessorKey: 'solution', header: '解决方案' },
    { accessorKey: 'remark', header: '备注' },
    { accessorKey: 'priority', header: '优先级' },
    { accessorKey: 'status', header: '状态' },
    { accessorKey: 'reporter_name', header: '提出人' },
    { accessorKey: 'created_at', header: '创建时间' },
    { accessorKey: 'resolution_hours', header: '解决耗时' },
  ]
  if (showGHColumn.value) {
    cols.push({ accessorKey: 'github_issues', header: 'GitHub Issues' })
  }
  return cols
})

async function onStatusChange({ issueId, newStatus }: { issueId: number, newStatus: string }) {
  const issue = issues.value.find((i: any) => i.id === issueId)
  if (!issue) return

  const oldStatus = issue.status
  issue.status = newStatus

  try {
    await api(`/api/issues/${issueId}/`, {
      method: 'PATCH',
      body: { status: newStatus },
    })
  } catch (e) {
    console.error('Failed to update issue status:', e)
    issue.status = oldStatus
  }
}

const kanbanColumns = computed(() => [
  { key: '待处理', label: '待处理', items: issues.value.filter(i => i.status === '待处理') },
  { key: '进行中', label: '进行中', items: issues.value.filter(i => i.status === '进行中') },
  { key: '已解决', label: '已解决', items: issues.value.filter(i => i.status === '已解决') },
])

function onKanbanDrop({ itemId, toColumn }: { itemId: string | number; fromColumn: string; toColumn: string }) {
  onStatusChange({ issueId: itemId as number, newStatus: toColumn })
}

async function inlineUpdate(issueId: string, field: string, value: string) {
  try {
    await api(`/api/issues/${issueId}/`, {
      method: 'PATCH',
      body: { [field]: value },
    })
    // Update locally without full refetch
    const issue = issues.value.find((i: any) => i.id === issueId)
    if (issue) issue[field] = value
  } catch (e) {
    console.error('Inline update failed:', e)
    await fetchIssues()
  }
}

function formatApiError(e: any, fallback: string): string {
  const data = e?.data || e?.response?._data
  if (data && typeof data === 'object') {
    const msgs = Object.entries(data)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
      .join('; ')
    if (msgs) return msgs
  }
  return e?.message || fallback
}

function priorityColor(p: string) {
  return p === 'P0' ? 'error' : p === 'P1' ? 'warning' : p === 'P2' ? 'warning' : 'neutral'
}
function statusColor(s: string) {
  return s === '待处理' ? 'warning' : s === '进行中' ? 'info' : s === '已解决' ? 'success' : 'neutral'
}

async function fetchIssues() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('page', String(page.value))
    params.set('page_size', String(pageSize))
    if (!showCompleted.value) {
      params.set('exclude_statuses', '已解决,已关闭')
    }

    const data = await api<any>(`/api/issues/?${params.toString()}`)
    issues.value = data.results || data || []
    totalCount.value = data.count ?? issues.value.length
  } catch (e) {
    console.error('Failed to load issues:', e)
  } finally {
    loading.value = false
  }
}

async function batchUpdate(action: string, value: string) {
  const ids = selectedRowsData.value.map((row: any) => row.id)
  if (!ids.length) return
  try {
    await api('/api/issues/batch-update/', {
      method: 'POST',
      body: { ids, action, value },
    })
    rowSelection.value = {}
    await fetchIssues()
  } catch (e) {
    console.error('Batch update failed:', e)
  }
}

const batchAssignItems = computed(() => [users.value.map(u => ({
  label: u.name || u.username,
  onSelect: () => batchUpdate('assign', String(u.id)),
}))])

const batchPriorityItems = [['P0', 'P1', 'P2', 'P3'].map(p => ({
  label: p,
  onSelect: () => batchUpdate('priority', p),
}))]

watch(page, () => {
  rowSelection.value = {}
  fetchIssues()
})

watch(showCompleted, () => {
  page.value = 1
  rowSelection.value = {}
  fetchIssues()
})

onMounted(async () => {
  const [, usersData, settingsData, projectsData, reposData] = await Promise.all([
    fetchIssues(),
    api<any[]>('/api/users/').catch(() => []),
    api<any>('/api/settings/').catch(() => ({ labels: [] })),
    api<any>('/api/projects/').catch(() => ({ results: [] })),
    api<any>('/api/repos/').catch(() => ({ results: [] })),
  ])
  users.value = usersData?.results || usersData || []
  labelOptions.value = settingsData?.labels || []
  projects.value = projectsData?.results || projectsData || []
  repos.value = reposData?.results || reposData || []
  // Check AI analysis status for issues with repos
  checkAnalyzingIssues()
})

async function checkAnalyzingIssues() {
  const issuesWithRepo = issues.value.filter(i => i.repo)
  const checks = await Promise.all(
    issuesWithRepo.map(i =>
      api<any>(`/api/issues/${i.id}/ai-status/`).catch(() => ({ status: 'idle' }))
    )
  )
  const running = new Set<number>()
  issuesWithRepo.forEach((issue, idx) => {
    if (checks[idx]?.status === 'running') running.add(issue.id)
  })
  analyzingIssueIds.value = running
}
</script>

<style scoped>
.modal-form {
  padding: 1.5rem 2rem;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}
.modal-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}
:root.dark .modal-header h3 {
  color: #f3f4f6;
}
.modal-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}
.form-row label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #374151;
}
:root.dark .form-row label {
  color: #9ca3af;
}
.form-row :deep(input),
.form-row :deep(textarea),
.form-row :deep(select),
.form-row :deep(button[role="combobox"]),
.form-row :deep([data-part="trigger"]) {
  width: 100% !important;
}
.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
@media (min-width: 768px) {
  .form-grid-2 {
    grid-template-columns: 1fr 1fr;
  }
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #f3f4f6;
}
:root.dark .modal-footer {
  border-top-color: #374151;
}
</style>
