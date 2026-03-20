<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">{{ project?.name }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ project?.description }}</p>
      </div>
      <UBadge
        :color="project?.status === '进行中' ? 'primary' : project?.status === '已完成' ? 'success' : 'neutral'"
        variant="subtle"
      >
        {{ project?.status }}
      </UBadge>
    </div>

    <!-- Project Info -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">项目信息</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">预计完成时间</p>
          <p class="text-sm font-medium text-gray-900">{{ project?.estimated_completion ? project.estimated_completion.slice(0, 10) : '-' }}</p>
        </div>
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">实际完成耗时</p>
          <p class="text-sm font-medium text-gray-900">{{ project?.actual_hours ? formatHours(project.actual_hours) : '-' }}</p>
        </div>
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">创建时间</p>
          <p class="text-sm font-medium text-gray-900">{{ project?.created_at?.slice(0, 10) }}</p>
        </div>
      </div>
      <div v-if="project?.remark" class="mt-4 bg-gray-50 rounded-lg px-4 py-3">
        <p class="text-xs text-gray-400 mb-1">备注</p>
        <p class="text-sm text-gray-700">{{ project.remark }}</p>
      </div>
    </div>

    <!-- Members -->
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">项目成员</h3>
      <div class="flex flex-wrap gap-3">
        <div v-for="m in projectMembers" :key="m.user_id" class="flex items-center bg-gray-50 rounded-lg px-3 py-2">
          <div class="w-7 h-7 rounded-full bg-crystal-100 flex items-center justify-center">
            <span class="text-crystal-600 text-xs font-medium">{{ getUserName(m.user_id).slice(0, 1) }}</span>
          </div>
          <span class="ml-2 text-sm text-gray-700">{{ getUserName(m.user_id) }}</span>
          <UBadge class="ml-2" color="neutral" variant="subtle" size="xs">{{ m.role }}</UBadge>
        </div>
      </div>
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
            <NuxtLink :to="`/app/issues/${row.original.id}`" class="text-crystal-500 hover:text-crystal-700 font-medium">{{ row.index + 1 }}</NuxtLink>
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
          <template #assignee-cell="{ row }">
            {{ getUserName(row.original.assignee) }}
          </template>
          <template #remark-cell="{ row }">
            <span class="text-gray-500 line-clamp-1" :title="row.original.remark">{{ row.original.remark || '-' }}</span>
          </template>
          <template #estimated_completion-cell="{ row }">
            {{ row.original.estimated_completion ? row.original.estimated_completion.slice(0, 10) : '-' }}
          </template>
          <template #actual_hours-cell="{ row }">
            <span v-if="row.original.actual_hours != null">{{ row.original.actual_hours }}h</span>
            <span v-else class="text-gray-300">-</span>
          </template>
          <template #created_at-cell="{ row }">
            {{ row.original.created_at.slice(0, 10) }}
          </template>
        </UTable>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })
import { projects, issues, getUserName } from '~/data/mock'

const route = useRoute()
const viewMode = ref<'kanban' | 'table'>('kanban')
const project = computed(() => projects.find(p => p.id === route.params.id))
const projectMembers = computed(() => project.value?.members ?? [])
const projectIssues = computed(() => issues.filter(i => i.project_id === route.params.id && i.status !== '已关闭'))

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
  { accessorKey: 'assignee', header: '负责人' },
  { accessorKey: 'remark', header: '备注' },
  { accessorKey: 'estimated_completion', header: '预计完成' },
  { accessorKey: 'actual_hours', header: '实际耗时' },
  { accessorKey: 'created_at', header: '创建时间' },
]
</script>
