<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
  </div>
  <div v-else-if="repo" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">{{ repo.name }}</h1>
        <p class="text-sm text-gray-400 dark:text-gray-500 mt-0.5">{{ repo.full_name }}</p>
      </div>
      <div class="flex items-center space-x-2">
        <UBadge :color="repo.status === '在线' ? 'success' : 'neutral'" variant="subtle">{{ repo.status }}</UBadge>
        <UButton
          icon="i-heroicons-arrow-path"
          variant="outline"
          color="neutral"
          size="sm"
          :loading="syncing"
          @click="handleSync"
        >
          同步
        </UButton>
        <UButton
          icon="i-heroicons-information-circle"
          variant="ghost"
          color="neutral"
          size="sm"
          @click="showInfo = true"
        />
      </div>
    </div>

    <!-- Dashboard Stats -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <DashboardStatCard
        label="Open Issues"
        :value="repo.open_issues_count ?? 0"
        icon="i-heroicons-exclamation-circle"
        icon-bg="bg-amber-50 dark:bg-amber-950"
        icon-color="text-amber-500"
      />
      <DashboardStatCard
        label="Closed Issues"
        :value="repo.closed_issues_count ?? 0"
        icon="i-heroicons-check-circle"
        icon-bg="bg-emerald-50 dark:bg-emerald-950"
        icon-color="text-emerald-500"
      />
      <div v-if="priorityStats.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
        <span class="text-sm text-gray-500 dark:text-gray-400">优先级分布</span>
        <div class="mt-2 flex flex-wrap gap-2">
          <UBadge
            v-for="p in priorityStats"
            :key="p.label"
            :color="p.label === 'P0' ? 'error' : p.label === 'P1' ? 'warning' : 'neutral'"
            variant="subtle"
            size="sm"
          >
            {{ p.label }}: {{ p.count }}
          </UBadge>
        </div>
      </div>
    </div>

    <!-- View Toggle -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
          <button
            class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
            :class="viewMode === 'kanban' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
            @click="viewMode = 'kanban'"
          >
            看板
          </button>
          <button
            class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
            :class="viewMode === 'table' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
            @click="viewMode = 'table'"
          >
            列表
          </button>
        </div>
        <USelect
          v-if="viewMode === 'kanban'"
          v-model="kanbanGroup"
          :items="[{ label: '按状态', value: 'state' }, { label: '按标签', value: 'label' }]"
          value-key="value"
          size="xs"
        />
      </div>
      <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ ghIssues.length }} 条</span>
    </div>

    <!-- Loading Issues -->
    <div v-if="issuesLoading" class="flex items-center justify-center py-10">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载 Issues 中...</div>
    </div>

    <!-- Kanban View -->
    <SharedKanbanBoard
      v-else-if="viewMode === 'kanban'"
      :columns="kanbanColumns"
      :item-key="(item: any) => item.id"
      :draggable="false"
    >
      <template #card="{ item }">
        <NuxtLink :to="`/app/repos/${route.params.id}/issues/${item.id}`" class="block">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs text-gray-400 dark:text-gray-500">#{{ item.github_id }}</span>
            <div class="flex items-center gap-1">
              <UBadge
                :color="item.state === 'open' ? 'warning' : 'success'"
                variant="subtle"
                size="xs"
              >
                {{ item.state === 'open' ? '开放' : '已关闭' }}
              </UBadge>
              <UBadge
                v-if="extractPriority(item.labels)"
                :color="extractPriority(item.labels)!.startsWith('P0') ? 'error' : extractPriority(item.labels)!.startsWith('P1') ? 'warning' : 'neutral'"
                variant="subtle"
                size="xs"
              >
                {{ extractPriority(item.labels) }}
              </UBadge>
            </div>
          </div>
          <p class="text-sm text-gray-900 dark:text-gray-100 font-medium line-clamp-2">{{ item.title }}</p>
          <div v-if="item.assignees?.length" class="mt-2 flex items-center">
            <div class="w-5 h-5 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center">
              <span class="text-crystal-600 dark:text-crystal-400 text-[10px] font-medium">{{ item.assignees[0].slice(0, 1).toUpperCase() }}</span>
            </div>
            <span class="ml-1.5 text-xs text-gray-400 dark:text-gray-500">{{ item.assignees[0] }}</span>
          </div>
        </NuxtLink>
      </template>
    </SharedKanbanBoard>

    <!-- Table View -->
    <div v-else-if="!issuesLoading" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
      <UTable
        :data="ghIssues"
        :columns="tableColumns"
        :ui="{ th: 'text-xs', td: 'text-sm' }"
      >
        <template #github_id-cell="{ row }">
          <span class="text-gray-500 dark:text-gray-400">#{{ row.original.github_id }}</span>
        </template>
        <template #title-cell="{ row }">
          <NuxtLink :to="`/app/repos/${route.params.id}/issues/${row.original.id}`" class="text-gray-900 dark:text-gray-100 hover:text-crystal-600 line-clamp-1">{{ row.original.title }}</NuxtLink>
        </template>
        <template #state-cell="{ row }">
          <UBadge :color="row.original.state === 'open' ? 'warning' : 'success'" variant="subtle" size="xs">
            {{ row.original.state === 'open' ? '开放' : '已关闭' }}
          </UBadge>
        </template>
        <template #labels-cell="{ row }">
          <div class="flex flex-wrap gap-1">
            <UBadge v-for="label in row.original.labels" :key="label" color="neutral" variant="subtle" size="xs">{{ label }}</UBadge>
          </div>
        </template>
        <template #assignees-cell="{ row }">
          {{ row.original.assignees?.join(', ') || '-' }}
        </template>
        <template #github_created_at-cell="{ row }">
          {{ row.original.github_created_at?.slice(0, 10) || '-' }}
        </template>
      </UTable>
    </div>

    <!-- Info Slideover -->
    <USlideover v-model:open="showInfo" title="仓库信息" side="right">
      <template #content>
        <div class="p-6 space-y-4">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">仓库信息</h3>
          <div class="space-y-3">
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">GitHub URL</p>
              <a :href="repo.url" target="_blank" class="text-sm text-crystal-500 hover:text-crystal-700 break-all">{{ repo.url }}</a>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">默认分支</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.default_branch }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">状态</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.status }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">绑定时间</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.connected_at?.slice(0, 10) }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">最近同步</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.last_synced_at?.slice(0, 16)?.replace('T', ' ') || '从未同步' }}</p>
            </div>
          </div>
        </div>
      </template>
    </USlideover>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { api } = useApi()
const toast = useToast()

const loading = ref(true)
const repo = ref<any>(null)
const ghIssues = ref<any[]>([])
const issuesLoading = ref(false)
const syncing = ref(false)
const showInfo = ref(false)
const viewMode = ref<'kanban' | 'table'>('kanban')
const kanbanGroup = ref('state')

const tableColumns = [
  { accessorKey: 'github_id', header: '#' },
  { accessorKey: 'title', header: '标题' },
  { accessorKey: 'state', header: '状态' },
  { accessorKey: 'labels', header: '标签' },
  { accessorKey: 'assignees', header: '负责人' },
  { accessorKey: 'github_created_at', header: '创建时间' },
]

function extractPriority(labels: string[]): string | null {
  if (!labels?.length) return null
  const match = labels.find(l => /^P[0-3]$/i.test(l) || /priority/i.test(l))
  return match || null
}

const priorityStats = computed(() => {
  const counts: Record<string, number> = {}
  for (const issue of ghIssues.value) {
    const p = extractPriority(issue.labels)
    if (p) counts[p] = (counts[p] || 0) + 1
  }
  return Object.entries(counts)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => a.label.localeCompare(b.label))
})

const kanbanColumns = computed(() => {
  if (kanbanGroup.value === 'state') {
    return [
      { key: 'open', label: '开放', items: ghIssues.value.filter(i => i.state === 'open') },
      { key: 'closed', label: '已关闭', items: ghIssues.value.filter(i => i.state === 'closed') },
    ]
  }
  const labelMap: Record<string, any[]> = {}
  for (const issue of ghIssues.value) {
    if (!issue.labels?.length) {
      const key = '无标签'
      if (!labelMap[key]) labelMap[key] = []
      labelMap[key].push(issue)
    } else {
      for (const label of issue.labels) {
        if (!labelMap[label]) labelMap[label] = []
        labelMap[label].push(issue)
      }
    }
  }
  return Object.entries(labelMap).map(([key, items]) => ({
    key,
    label: key,
    items,
  }))
})

async function fetchIssues() {
  issuesLoading.value = true
  try {
    ghIssues.value = await api<any[]>(`/api/repos/github-issues/?repo=${route.params.id}`)
  } catch (e) {
    console.error('Failed to load GitHub issues:', e)
  } finally {
    issuesLoading.value = false
  }
}

async function handleSync() {
  syncing.value = true
  try {
    const data = await api<any>(`/api/repos/${route.params.id}/sync/`, { method: 'POST' })
    repo.value = data
    await fetchIssues()
    toast.add({ title: `已同步 ${ghIssues.value.length} 条 Issue`, color: 'success' })
  } catch (e: any) {
    console.error('Sync failed:', e)
    const detail = e?.data?.detail || e?.response?._data?.detail || '同步失败，请重试'
    toast.add({ title: detail, color: 'error' })
  } finally {
    syncing.value = false
  }
}

onMounted(async () => {
  try {
    const [repoData] = await Promise.all([
      api<any>(`/api/repos/${route.params.id}/`),
    ])
    repo.value = repoData
    await fetchIssues()
  } catch (e) {
    console.error('Failed to load repo:', e)
  } finally {
    loading.value = false
  }
})
</script>
