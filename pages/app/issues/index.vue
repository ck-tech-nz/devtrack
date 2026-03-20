<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">问题跟踪</h1>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl border border-gray-100 p-4">
      <div class="flex flex-wrap gap-3">
        <UInput v-model="search" placeholder="搜索标题/ID" icon="i-heroicons-magnifying-glass" size="sm" class="w-60" />
        <USelect v-model="filterPriority" :options="priorityOptions" placeholder="优先级" size="sm" class="w-28" />
        <USelect v-model="filterStatus" :options="statusOptions" placeholder="状态" size="sm" class="w-28" />
        <USelect v-model="filterLabel" :options="labelFilterOptions" placeholder="标签" size="sm" class="w-28" />
        <USelect v-model="filterAssignee" :options="assigneeOptions" placeholder="负责人" size="sm" class="w-32" />
      </div>
    </div>

    <!-- Batch Actions -->
    <div v-if="selectedRows.length > 0" class="bg-crystal-50 rounded-xl border border-crystal-100 p-3 flex items-center justify-between">
      <span class="text-sm text-crystal-700">已选择 {{ selectedRows.length }} 项</span>
      <div class="flex items-center space-x-2">
        <UDropdown :items="batchAssignItems" :popper="{ placement: 'bottom-end' }">
          <UButton size="xs" color="violet" variant="outline">批量分配</UButton>
        </UDropdown>
        <UDropdown :items="batchPriorityItems" :popper="{ placement: 'bottom-end' }">
          <UButton size="xs" color="violet" variant="outline">修改优先级</UButton>
        </UDropdown>
      </div>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
      <UTable
        v-model="selectedRows"
        :rows="paginatedIssues"
        :columns="columns"
        :ui="{ th: { base: 'text-xs' }, td: { base: 'text-sm' } }"
      >
        <template #id-data="{ row }">
          <NuxtLink :to="`/app/issues/${row.id}`" class="text-crystal-500 hover:text-crystal-700 font-medium">{{ row.id }}</NuxtLink>
        </template>
        <template #title-data="{ row }">
          <NuxtLink :to="`/app/issues/${row.id}`" class="text-gray-900 hover:text-crystal-600 line-clamp-1">{{ row.title }}</NuxtLink>
        </template>
        <template #priority-data="{ row }">
          <UBadge :color="priorityColor(row.priority)" variant="subtle" size="xs">{{ row.priority }}</UBadge>
        </template>
        <template #status-data="{ row }">
          <UBadge :color="statusColor(row.status)" variant="subtle" size="xs">{{ row.status }}</UBadge>
        </template>
        <template #assignee-data="{ row }">
          {{ getUserName(row.assignee) }}
        </template>
        <template #reporter-data="{ row }">
          {{ getUserName(row.reporter) }}
        </template>
        <template #created_at-data="{ row }">
          {{ row.created_at.slice(0, 10) }}
        </template>
        <template #resolution_hours-data="{ row }">
          {{ row.resolution_hours ? row.resolution_hours + 'h' : '-' }}
        </template>
      </UTable>
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50">
        <span class="text-xs text-gray-400">共 {{ filteredIssues.length }} 条</span>
        <div class="flex items-center space-x-2">
          <UButton size="xs" variant="ghost" color="gray" :disabled="page <= 1" @click="page--">上一页</UButton>
          <span class="text-xs text-gray-500">{{ page }} / {{ totalPages }}</span>
          <UButton size="xs" variant="ghost" color="gray" :disabled="page >= totalPages" @click="page++">下一页</UButton>
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
const selectedRows = ref<any[]>([])

const priorityOptions = [{ label: '全部', value: '' }, { label: 'P0', value: 'P0' }, { label: 'P1', value: 'P1' }, { label: 'P2', value: 'P2' }, { label: 'P3', value: 'P3' }]
const statusOptions = [{ label: '全部', value: '' }, { label: '待处理', value: '待处理' }, { label: '进行中', value: '进行中' }, { label: '已解决', value: '已解决' }, { label: '已关闭', value: '已关闭' }]
const labelFilterOptions = [{ label: '全部', value: '' }, ...labelOptions.map(l => ({ label: l, value: l }))]
const assigneeOptions = [{ label: '全部', value: '' }, ...users.map(u => ({ label: u.name, value: u.id }))]

const columns = [
  { key: 'id', label: 'ID', sortable: true },
  { key: 'title', label: '标题' },
  { key: 'priority', label: '优先级', sortable: true },
  { key: 'status', label: '状态' },
  { key: 'assignee', label: '负责人' },
  { key: 'reporter', label: '提出人' },
  { key: 'created_at', label: '创建时间', sortable: true },
  { key: 'resolution_hours', label: '解决耗时', sortable: true },
]

function priorityColor(p: string) {
  return p === 'P0' ? 'red' : p === 'P1' ? 'orange' : p === 'P2' ? 'yellow' : 'gray'
}
function statusColor(s: string) {
  return s === '待处理' ? 'amber' : s === '进行中' ? 'blue' : s === '已解决' ? 'green' : 'gray'
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

watch([filterPriority, filterStatus, filterLabel, filterAssignee, search], () => { page.value = 1 })

// Batch operations (mock: mutate in-memory data)
const batchAssignItems = [users.map(u => ({
  label: u.name,
  click: () => { selectedRows.value.forEach(row => { row.assignee = u.id }); selectedRows.value = [] },
}))]

const batchPriorityItems = [['P0', 'P1', 'P2', 'P3'].map(p => ({
  label: p,
  click: () => { selectedRows.value.forEach(row => { row.priority = p }); selectedRows.value = [] },
}))]
</script>
