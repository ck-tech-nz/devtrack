<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">问题跟踪</h1>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl border border-gray-100 p-4">
      <div class="flex flex-wrap gap-3">
        <UInput v-model="search" placeholder="搜索标题/ID" icon="i-heroicons-magnifying-glass" size="sm" class="w-60" />
        <USelect v-model="filterPriority" :items="priorityOptions" placeholder="优先级" size="sm" class="w-28" value-key="value" />
        <USelect v-model="filterStatus" :items="statusOptions" placeholder="状态" size="sm" class="w-28" value-key="value" />
        <USelect v-model="filterLabel" :items="labelFilterOptions" placeholder="标签" size="sm" class="w-28" value-key="value" />
        <USelect v-model="filterAssignee" :items="assigneeOptions" placeholder="负责人" size="sm" class="w-32" value-key="value" />
      </div>
    </div>

    <!-- Batch Actions -->
    <div v-if="selectedRowsData.length > 0" class="bg-crystal-50 rounded-xl border border-crystal-100 p-3 flex items-center justify-between">
      <span class="text-sm text-crystal-700">已选择 {{ selectedRowsData.length }} 项</span>
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
      <div class="text-sm text-gray-400">加载中...</div>
    </div>

    <!-- Table -->
    <div v-else class="bg-white rounded-xl border border-gray-100 overflow-hidden">
      <UTable
        v-model:row-selection="rowSelection"
        :data="issues"
        :columns="columns"
        :ui="{ th: 'text-xs', td: 'text-sm' }"
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
        <template #display_id-cell="{ row }">
          <NuxtLink :to="`/app/issues/${row.original.id}`" class="text-crystal-500 hover:text-crystal-700 font-medium">{{ row.original.display_id }}</NuxtLink>
        </template>
        <template #title-cell="{ row }">
          <NuxtLink :to="`/app/issues/${row.original.id}`" class="text-gray-900 hover:text-crystal-600 line-clamp-1">{{ row.original.title }}</NuxtLink>
        </template>
        <template #priority-cell="{ row }">
          <UBadge :color="priorityColor(row.original.priority)" variant="subtle" size="xs">{{ row.original.priority }}</UBadge>
        </template>
        <template #status-cell="{ row }">
          <UBadge :color="statusColor(row.original.status)" variant="subtle" size="xs">{{ row.original.status }}</UBadge>
        </template>
        <template #assignee_name-cell="{ row }">
          {{ row.original.assignee_name || '-' }}
        </template>
        <template #reporter_name-cell="{ row }">
          {{ row.original.reporter_name || '-' }}
        </template>
        <template #created_at-cell="{ row }">
          {{ row.original.created_at ? row.original.created_at.slice(0, 10) : '-' }}
        </template>
        <template #resolution_hours-cell="{ row }">
          {{ row.original.resolution_hours ? row.original.resolution_hours + 'h' : '-' }}
        </template>
      </UTable>
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50">
        <span class="text-xs text-gray-400">共 {{ totalCount }} 条</span>
        <div class="flex items-center space-x-2">
          <UButton size="xs" variant="ghost" color="neutral" :disabled="page <= 1" @click="page--">上一页</UButton>
          <span class="text-xs text-gray-500">{{ page }} / {{ totalPages }}</span>
          <UButton size="xs" variant="ghost" color="neutral" :disabled="page >= totalPages" @click="page++">下一页</UButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()

const search = ref('')
const filterPriority = ref('')
const filterStatus = ref('')
const filterLabel = ref('')
const filterAssignee = ref('')
const page = ref(1)
const pageSize = 15
const rowSelection = ref<Record<string, boolean>>({})

const loading = ref(true)
const issues = ref<any[]>([])
const totalCount = ref(0)
const users = ref<any[]>([])
const labelOptions = ref<string[]>([])

const selectedRowsData = computed(() => {
  return Object.entries(rowSelection.value)
    .filter(([_, selected]) => selected)
    .map(([idx]) => issues.value[parseInt(idx)])
    .filter(Boolean)
})

const priorityOptions = [{ label: '全部', value: '' }, { label: 'P0', value: 'P0' }, { label: 'P1', value: 'P1' }, { label: 'P2', value: 'P2' }, { label: 'P3', value: 'P3' }]
const statusOptions = [{ label: '全部', value: '' }, { label: '待处理', value: '待处理' }, { label: '进行中', value: '进行中' }, { label: '已解决', value: '已解决' }, { label: '已关闭', value: '已关闭' }]
const labelFilterOptions = computed(() => [{ label: '全部', value: '' }, ...labelOptions.value.map(l => ({ label: l, value: l }))])
const assigneeOptions = computed(() => [{ label: '全部', value: '' }, ...users.value.map(u => ({ label: u.name || u.username, value: String(u.id) }))])

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))

const columns = [
  { id: 'select', header: '', cell: '' },
  { accessorKey: 'display_id', header: 'ID' },
  { accessorKey: 'title', header: '标题' },
  { accessorKey: 'priority', header: '优先级' },
  { accessorKey: 'status', header: '状态' },
  { accessorKey: 'assignee_name', header: '负责人' },
  { accessorKey: 'reporter_name', header: '提出人' },
  { accessorKey: 'created_at', header: '创建时间' },
  { accessorKey: 'resolution_hours', header: '解决耗时' },
]

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
    if (search.value) params.set('search', search.value)
    if (filterPriority.value) params.set('priority', filterPriority.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterLabel.value) params.set('label', filterLabel.value)
    if (filterAssignee.value) params.set('assignee', filterAssignee.value)

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

watch([filterPriority, filterStatus, filterLabel, filterAssignee, search], () => {
  page.value = 1
  rowSelection.value = {}
  fetchIssues()
})

watch(page, () => {
  rowSelection.value = {}
  fetchIssues()
})

onMounted(async () => {
  const [, usersData, settingsData] = await Promise.all([
    fetchIssues(),
    api<any[]>('/api/users/').catch(() => []),
    api<any>('/api/settings/').catch(() => ({ labels: [] })),
  ])
  users.value = usersData || []
  labelOptions.value = settingsData?.labels || []
})
</script>
