<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-semibold text-gray-900">项目管理</h1>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400">加载中...</div>
    </div>

    <template v-else>
      <div v-if="projects.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <NuxtLink
          v-for="project in projects"
          :key="project.id"
          :to="`/app/projects/${project.id}`"
          class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-sm transition-shadow block"
        >
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-gray-900">{{ project.name }}</h3>
            <UBadge
              :color="project.status === '进行中' ? 'primary' : project.status === '已完成' ? 'success' : 'neutral'"
              variant="subtle"
              size="xs"
            >
              {{ project.status }}
            </UBadge>
          </div>
          <p class="text-sm text-gray-500 mb-4 line-clamp-2">{{ project.description }}</p>
          <div class="flex items-center flex-wrap gap-y-1 text-xs text-gray-400 space-x-4">
            <span class="flex items-center">
              <UIcon name="i-heroicons-users" class="w-3.5 h-3.5 mr-1" />
              {{ project.member_count }} 成员
            </span>
            <span class="flex items-center">
              <UIcon name="i-heroicons-bug-ant" class="w-3.5 h-3.5 mr-1" />
              {{ project.issue_count }} Issues
            </span>
            <span v-if="project.linked_repos != null" class="flex items-center">
              <UIcon name="i-heroicons-code-bracket" class="w-3.5 h-3.5 mr-1" />
              {{ Array.isArray(project.linked_repos) ? project.linked_repos.length : project.linked_repos }} 仓库
            </span>
            <span v-if="project.estimated_completion" class="flex items-center">
              <UIcon name="i-heroicons-calendar" class="w-3.5 h-3.5 mr-1" />
              预计 {{ project.estimated_completion.slice(0, 10) }}
            </span>
          </div>
        </NuxtLink>
      </div>
      <div v-else class="text-center py-20 text-sm text-gray-400">暂无项目</div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()

const loading = ref(true)
const projects = ref<any[]>([])

onMounted(async () => {
  try {
    const data = await api<any>('/api/projects/')
    projects.value = data.results || data || []
  } catch (e) {
    console.error('Failed to load projects:', e)
  } finally {
    loading.value = false
  }
})
</script>
