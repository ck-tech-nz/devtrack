<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400">加载中...</div>
  </div>

  <div v-else-if="project" class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">{{ project.name }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ project.description }}</p>
      </div>
      <UBadge
        :color="project.status === '进行中' ? 'primary' : project.status === '已完成' ? 'success' : 'neutral'"
        variant="subtle"
      >
        {{ project.status }}
      </UBadge>
    </div>

    <!-- Project Info -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">项目信息</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">预计完成时间</p>
          <p class="text-sm font-medium text-gray-900">{{ project.estimated_completion ? project.estimated_completion.slice(0, 10) : '-' }}</p>
        </div>
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">实际完成耗时</p>
          <p class="text-sm font-medium text-gray-900">{{ project.actual_hours ? formatHours(project.actual_hours) : '-' }}</p>
        </div>
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">创建时间</p>
          <p class="text-sm font-medium text-gray-900">{{ project.created_at?.slice(0, 10) }}</p>
        </div>
      </div>
      <div v-if="project.remark" class="mt-4 bg-gray-50 rounded-lg px-4 py-3">
        <p class="text-xs text-gray-400 mb-1">备注</p>
        <p class="text-sm text-gray-700">{{ project.remark }}</p>
      </div>
    </div>

    <!-- Members -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">项目成员</h3>
      <div v-if="projectMembers.length" class="flex flex-wrap gap-3">
        <div v-for="m in projectMembers" :key="m.user_id" class="flex items-center bg-gray-50 rounded-lg px-3 py-2">
          <div class="w-7 h-7 rounded-full bg-crystal-100 flex items-center justify-center">
            <span class="text-crystal-600 text-xs font-medium">{{ (m.user_name || '?').slice(0, 1) }}</span>
          </div>
          <span class="ml-2 text-sm text-gray-700">{{ m.user_name || '未知' }}</span>
          <UBadge class="ml-2" color="neutral" variant="subtle" size="xs">{{ m.role }}</UBadge>
        </div>
      </div>
      <div v-else class="text-sm text-gray-400">暂无成员</div>
    </div>

    <!-- Issues View -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-gray-900">Issues</h3>
        <div class="flex items-center bg-gray-100 rounded-lg p-0.5">
          <button
            class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
            :class="viewMode === 'kanban' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
            @click="viewMode = 'kanban'"
          >
            看板
          </button>
          <button
            class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
            :class="viewMode === 'table' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
            @click="viewMode = 'table'"
          >
            列表
          </button>
        </div>
      </div>

      <ProjectsKanbanBoard v-if="viewMode === 'kanban'" :issues="projectIssues" />

      <div v-else class="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <UTable
          :data="projectIssues"
          :columns="tableColumns"
          :ui="{ th: 'text-xs', td: 'text-sm' }"
        >
          <template #id-cell="{ row }">
            <NuxtLink :to="`/app/issues/${row.original.id}`" class="text-crystal-500 hover:text-crystal-700 font-medium">{{ row.original.id }}</NuxtLink>
          </template>
          <template #title-cell="{ row }">
            <NuxtLink :to="`/app/issues/${row.original.id}`" class="text-gray-900 hover:text-crystal-600 line-clamp-1">{{ row.original.title }}</NuxtLink>
          </template>
          <template #priority-cell="{ row }">
            <UBadge :color="row.original.priority === 'P0' ? 'error' : row.original.priority === 'P1' ? 'warning' : row.original.priority === 'P2' ? 'warning' : 'neutral'" variant="subtle" size="xs">{{ row.original.priority }}</UBadge>
          </template>
          <template #status-cell="{ row }">
            <UBadge :color="row.original.status === '待处理' ? 'warning' : row.original.status === '进行中' ? 'info' : 'success'" variant="subtle" size="xs">{{ row.original.status }}</UBadge>
          </template>
          <template #assignee_name-cell="{ row }">
            {{ row.original.assignee_name || '-' }}
          </template>
          <template #created_at-cell="{ row }">
            {{ row.original.created_at ? row.original.created_at.slice(0, 10) : '-' }}
          </template>
        </UTable>
      </div>
    </div>
  </div>

  <div v-else class="text-center py-20 text-sm text-gray-400">项目不存在</div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const route = useRoute()

const loading = ref(true)
const project = ref<any>(null)
const projectIssues = ref<any[]>([])
const viewMode = ref<'kanban' | 'table'>('kanban')

const projectMembers = computed(() => project.value?.members ?? [])

function formatHours(hours: number): string {
  if (hours >= 24) {
    const days = Math.floor(hours / 8)
    return `${days} 人天 (${hours}h)`
  }
  return `${hours}h`
}

const tableColumns = [
  { accessorKey: 'id', header: 'ID' },
  { accessorKey: 'title', header: '标题' },
  { accessorKey: 'priority', header: '优先级' },
  { accessorKey: 'status', header: '状态' },
  { accessorKey: 'assignee_name', header: '负责人' },
  { accessorKey: 'created_at', header: '创建时间' },
]

onMounted(async () => {
  const id = route.params.id
  try {
    const [projectData, issuesData] = await Promise.all([
      api<any>(`/api/projects/${id}/`),
      api<any>(`/api/projects/${id}/issues/`),
    ])
    project.value = projectData
    const issues = issuesData.results || issuesData || []
    projectIssues.value = issues.filter((i: any) => i.status !== '已关闭')
  } catch (e) {
    console.error('Failed to load project:', e)
  } finally {
    loading.value = false
  }
})
</script>
