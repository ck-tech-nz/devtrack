<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">{{ project?.name }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ project?.description }}</p>
      </div>
      <UBadge
        :color="project?.status === '进行中' ? 'violet' : project?.status === '已完成' ? 'green' : 'gray'"
        variant="subtle"
      >
        {{ project?.status }}
      </UBadge>
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
          <UBadge class="ml-2" color="gray" variant="subtle" size="xs">{{ m.role }}</UBadge>
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
          :rows="projectIssues"
          :columns="tableColumns"
          :ui="{ th: { base: 'text-xs' }, td: { base: 'text-sm' } }"
        >
          <template #id-data="{ row }">
            <NuxtLink :to="`/app/issues/${row.id}`" class="text-crystal-500 hover:text-crystal-700 font-medium">{{ row.id }}</NuxtLink>
          </template>
          <template #title-data="{ row }">
            <NuxtLink :to="`/app/issues/${row.id}`" class="text-gray-900 hover:text-crystal-600 line-clamp-1">{{ row.title }}</NuxtLink>
          </template>
          <template #priority-data="{ row }">
            <UBadge :color="row.priority === 'P0' ? 'red' : row.priority === 'P1' ? 'orange' : row.priority === 'P2' ? 'yellow' : 'gray'" variant="subtle" size="xs">{{ row.priority }}</UBadge>
          </template>
          <template #status-data="{ row }">
            <UBadge :color="row.status === '待处理' ? 'amber' : row.status === '进行中' ? 'blue' : 'green'" variant="subtle" size="xs">{{ row.status }}</UBadge>
          </template>
          <template #assignee-data="{ row }">
            {{ getUserName(row.assignee) }}
          </template>
          <template #created_at-data="{ row }">
            {{ row.created_at.slice(0, 10) }}
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

const tableColumns = [
  { key: 'id', label: 'ID', sortable: true },
  { key: 'title', label: '标题' },
  { key: 'priority', label: '优先级', sortable: true },
  { key: 'status', label: '状态' },
  { key: 'assignee', label: '负责人' },
  { key: 'created_at', label: '创建时间', sortable: true },
]
</script>
