<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">项目管理</h1>
      <UButton icon="i-heroicons-plus" size="sm" @click="showCreateModal = true">新建项目</UButton>
    </div>

    <!-- Create Project Modal -->
    <UModal v-model:open="showCreateModal" title="新建项目" :close="true">
      <template #body>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">项目名 <span class="text-red-500">*</span></label>
            <UInput v-model="newProject.name" placeholder="输入项目名" size="sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <UTextarea v-model="newProject.description" placeholder="输入项目描述" size="sm" :rows="3" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
            <USelect v-model="newProject.status" :items="projectStatusOptions" size="sm" value-key="value" />
          </div>
          <p v-if="createError" class="text-sm text-red-500">{{ createError }}</p>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="ghost" @click="showCreateModal = false">取消</UButton>
          <UButton :loading="creating" @click="handleCreateProject">创建</UButton>
        </div>
      </template>
    </UModal>

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

// Create project modal state
const showCreateModal = ref(false)
const creating = ref(false)
const createError = ref('')
const newProject = ref({
  name: '',
  description: '',
  status: '进行中',
})

const projectStatusOptions = [
  { label: '进行中', value: '进行中' },
  { label: '已完成', value: '已完成' },
  { label: '已归档', value: '已归档' },
]

async function fetchProjects() {
  loading.value = true
  try {
    const data = await api<any>('/api/projects/')
    projects.value = data.results || data || []
  } catch (e) {
    console.error('Failed to load projects:', e)
  } finally {
    loading.value = false
  }
}

async function handleCreateProject() {
  if (!newProject.value.name.trim()) {
    createError.value = '项目名不能为空'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    await api('/api/projects/', {
      method: 'POST',
      body: {
        name: newProject.value.name,
        description: newProject.value.description,
        status: newProject.value.status,
      },
    })
    showCreateModal.value = false
    newProject.value = { name: '', description: '', status: '进行中' }
    await fetchProjects()
  } catch (e: any) {
    createError.value = e?.data?.detail || e?.message || '创建失败，请重试'
    console.error('Failed to create project:', e)
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  fetchProjects()
})
</script>
