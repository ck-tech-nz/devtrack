<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
  </div>
  <div v-else-if="issue" class="space-y-6">
    <!-- Header -->
    <div>
      <div class="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500 mb-2">
        <NuxtLink :to="`/app/repos/${route.params.id}`" class="hover:text-crystal-500">{{ issue.repo_name }}</NuxtLink>
        <UIcon name="i-heroicons-chevron-right" class="w-3.5 h-3.5" />
        <span>#{{ issue.github_id }}</span>
      </div>
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">{{ issue.title }}</h1>
        <div class="flex items-center gap-2">
          <UBadge :color="issue.state === 'open' ? 'warning' : 'success'" variant="subtle">
            {{ issue.state === 'open' ? '开放' : '已关闭' }}
          </UBadge>
        </div>
      </div>
    </div>

    <!-- Main content + Sidebar -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Body -->
      <div class="lg:col-span-3">
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
          <div v-if="issue.body" class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words leading-relaxed">{{ issue.body }}</div>
          <p v-else class="text-sm text-gray-400 dark:text-gray-500 italic">无描述</p>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-4">
        <!-- Labels -->
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-2">标签</p>
          <div v-if="issue.labels?.length" class="flex flex-wrap gap-1.5">
            <UBadge v-for="label in issue.labels" :key="label" color="neutral" variant="subtle" size="xs">{{ label }}</UBadge>
          </div>
          <p v-else class="text-sm text-gray-400 dark:text-gray-500">-</p>
        </div>

        <!-- Assignees -->
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-2">负责人</p>
          <div v-if="issue.assignees?.length" class="space-y-2">
            <div v-for="assignee in issue.assignees" :key="assignee" class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center">
                <span class="text-crystal-600 dark:text-crystal-400 text-[10px] font-medium">{{ assignee.slice(0, 1).toUpperCase() }}</span>
              </div>
              <span class="text-sm text-gray-700 dark:text-gray-300">{{ assignee }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-gray-400 dark:text-gray-500">-</p>
        </div>

        <!-- Dates -->
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-2">时间</p>
          <div class="space-y-1.5 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-400 dark:text-gray-500">创建</span>
              <span class="text-gray-700 dark:text-gray-300">{{ issue.github_created_at?.slice(0, 10) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-400 dark:text-gray-500">更新</span>
              <span class="text-gray-700 dark:text-gray-300">{{ issue.github_updated_at?.slice(0, 10) }}</span>
            </div>
            <div v-if="issue.github_closed_at" class="flex justify-between">
              <span class="text-gray-400 dark:text-gray-500">关闭</span>
              <span class="text-gray-700 dark:text-gray-300">{{ issue.github_closed_at?.slice(0, 10) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { api } = useApi()

const loading = ref(true)
const issue = ref<any>(null)

onMounted(async () => {
  try {
    issue.value = await api<any>(`/api/repos/github-issues/${route.params.issueId}/`)
  } catch (e) {
    console.error('Failed to load GitHub issue:', e)
  } finally {
    loading.value = false
  }
})
</script>
