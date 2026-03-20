<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">GitHub 仓库</h1>
      <UButton icon="i-heroicons-plus" size="sm" @click="showCreateModal = true">添加仓库</UButton>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400">加载中...</div>
    </div>
    <template v-else>
      <div v-if="repos.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <NuxtLink v-for="repo in repos" :key="repo.id" :to="`/app/repos/${repo.id}`" class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-sm transition-shadow block">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-gray-900">{{ repo.full_name }}</h3>
            <UBadge :color="repo.status === '在线' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ repo.status }}</UBadge>
          </div>
          <p class="text-sm text-gray-500 mb-3">{{ repo.description }}</p>
          <div class="flex items-center text-xs text-gray-400 space-x-4">
            <span class="flex items-center"><UIcon name="i-heroicons-code-bracket" class="w-3.5 h-3.5 mr-1" />{{ repo.language }}</span>
            <span class="flex items-center"><UIcon name="i-heroicons-star" class="w-3.5 h-3.5 mr-1" />{{ repo.stars }}</span>
            <span>绑定于 {{ repo.connected_at?.slice(0, 10) }}</span>
          </div>
        </NuxtLink>
      </div>
      <div v-else class="text-center py-20 text-sm text-gray-400">暂无绑定仓库</div>
    </template>

    <!-- Create Modal -->
    <UModal v-model:open="showCreateModal">
      <template #default>
        <div class="p-6 space-y-4">
          <h3 class="text-lg font-semibold text-gray-900">添加仓库</h3>
          <UFormField label="仓库全名" required>
            <UInput v-model="form.full_name" placeholder="如 org/repo-name" />
          </UFormField>
          <UFormField label="GitHub URL">
            <UInput v-model="form.url" placeholder="https://github.com/org/repo-name" />
          </UFormField>
          <UFormField label="描述">
            <UTextarea v-model="form.description" placeholder="仓库描述" />
          </UFormField>
          <div class="grid grid-cols-2 gap-4">
            <UFormField label="主要语言">
              <UInput v-model="form.language" placeholder="如 Python" />
            </UFormField>
            <UFormField label="默认分支">
              <UInput v-model="form.default_branch" placeholder="main" />
            </UFormField>
          </div>
          <p v-if="createError" class="text-sm text-red-500">{{ createError }}</p>
          <div class="flex justify-end gap-2 pt-2">
            <UButton variant="ghost" color="neutral" @click="showCreateModal = false">取消</UButton>
            <UButton :loading="creating" @click="handleCreate">添加</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const loading = ref(true)
const repos = ref<any[]>([])

const showCreateModal = ref(false)
const creating = ref(false)
const createError = ref('')
const form = ref({ full_name: '', url: '', description: '', language: '', default_branch: 'main' })

async function fetchRepos() {
  loading.value = true
  try {
    repos.value = await api<any[]>('/api/repos/')
  } catch (e) {
    console.error('Failed to load repos:', e)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  createError.value = ''
  creating.value = true
  try {
    const name = form.value.full_name.split('/').pop() || form.value.full_name
    await api('/api/repos/', {
      method: 'POST',
      body: { ...form.value, name },
    })
    showCreateModal.value = false
    form.value = { full_name: '', url: '', description: '', language: '', default_branch: 'main' }
    await fetchRepos()
  } catch (e: any) {
    createError.value = '添加失败，请检查输入'
  } finally {
    creating.value = false
  }
}

onMounted(fetchRepos)
</script>
