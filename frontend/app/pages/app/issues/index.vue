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

    <!-- Table -->
    <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
      <UTable
        v-model:row-selection="rowSelection"
        :data="paginatedIssues"
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
        <template #id-cell="{ row }">
          <NuxtLink :to="`/app/issues/${row.original.id}`" class="text-crystal-500 hover:text-crystal-700 font-medium">{{ row.original.id }}</NuxtLink>
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
        <template #assignee-cell="{ row }">
          {{ getUserName(row.original.assignee) }}
        </template>
        <template #reporter-cell="{ row }">
          {{ getUserName(row.original.reporter) }}
        </template>
        <template #created_at-cell="{ row }">
          {{ row.original.created_at.slice(0, 10) }}
        </template>
        <template #resolution_hours-cell="{ row }">
          {{ row.original.resolution_hours ? row.original.resolution_hours + 'h' : '-' }}
        </template>
      </UTable>
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50">
        <span class="text-xs text-gray-400">共 {{ filteredIssues.length }} 条</span>
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
import { issues, users, labelOptions, getUserName } from '~/data/mock'

const search = ref('')
const filterPriority = ref('')
const filterStatus = ref('')
const filterLabel = ref('')
const filterAssignee = ref('')
const page = ref(1)
const pageSize = 15
const rowSelection = ref<Record<string, boolean>>({})

const selectedRowsData = computed(() => {
  return Object.entries(rowSelection.value)
    .filter(([_, selected]) => selected)
    .map(([idx]) => paginatedIssues.value[parseInt(idx)])
    .filter(Boolean)
})

const priorityOptions = [{ label: '全部', value: '' }, { label: 'P0', value: 'P0' }, { label: 'P1', value: 'P1' }, { label: 'P2', value: 'P2' }, { label: 'P3', value: 'P3' }]
const statusOptions = [{ label: '全部', value: '' }, { label: '待处理', value: '待处理' }, { label: '进行中', value: '进行中' }, { label: '已解决', value: '已解决' }, { label: '已关闭', value: '已关闭' }]
const labelFilterOptions = [{ label: '全部', value: '' }, ...labelOptions.map(l => ({ label: l, value: l }))]
const assigneeOptions = [{ label: '全部', value: '' }, ...users.map(u => ({ label: u.name, value: u.id }))]

const columns = [
  { id: 'select', header: '', cell: '' },
  { accessorKey: 'id', header: 'ID' },
  { accessorKey: 'title', header: '标题' },
  { accessorKey: 'priority', header: '优先级' },
  { accessorKey: 'status', header: '状态' },
  { accessorKey: 'assignee', header: '负责人' },
  { accessorKey: 'reporter', header: '提出人' },
  { accessorKey: 'created_at', header: '创建时间' },
  { accessorKey: 'resolution_hours', header: '解决耗时' },
]

function priorityColor(p: string) {
  return p === 'P0' ? 'error' : p === 'P1' ? 'warning' : p === 'P2' ? 'warning' : 'neutral'
}
function statusColor(s: string) {
  return s === '待处理' ? 'warning' : s === '进行中' ? 'info' : s === '已解决' ? 'success' : 'neutral'
}

const filteredIssues = computed(() => {
  return issues.filter(i => {
    if (search.value && !i.title.includes(search.value) && !i.id.includes(search.value)) return false
    if (filterPriority.value && i.priority !== filterPriority.value) return false
    if (filterStatus.value && i.status !== filterStatus.value) return false
    if (filterLabel.value && !i.labels.includes(filterLabel.value)) return false
    if (filterAssignee.value && i.assignee !== filterAssignee.value) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredIssues.value.length / pageSize)))
const paginatedIssues = computed(() => filteredIssues.value.slice((page.value - 1) * pageSize, page.value * pageSize))

watch([filterPriority, filterStatus, filterLabel, filterAssignee, search], () => { page.value = 1; rowSelection.value = {} })

// Batch operations (mock: mutate in-memory data)
const batchAssignItems = [users.map(u => ({
  label: u.name,
  onSelect: () => { selectedRowsData.value.forEach(row => { row.assignee = u.id }); rowSelection.value = {} },
}))]

const batchPriorityItems = [['P0', 'P1', 'P2', 'P3'].map(p => ({
  label: p,
  onSelect: () => { selectedRowsData.value.forEach(row => { row.priority = p }); rowSelection.value = {} },
}))]
</script>
