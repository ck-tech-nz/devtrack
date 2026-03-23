<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">GitHub 仓库</h1>
      <UButton icon="i-heroicons-plus" size="sm" @click="showCreateModal = true">添加仓库</UButton>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>
    <template v-else>
      <div v-if="repos.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <NuxtLink v-for="repo in repos" :key="repo.id" :to="`/app/repos/${repo.id}`" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 hover:shadow-sm transition-shadow block">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="font-semibold text-gray-900 dark:text-gray-100">{{ repo.name }}</h3>
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ repo.full_name }}</p>
            </div>
            <UBadge :color="repo.status === '在线' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ repo.status }}</UBadge>
          </div>
          <div class="flex items-center text-xs text-gray-400 dark:text-gray-500 space-x-4 mt-3">
            <span class="flex items-center">
              <UIcon name="i-heroicons-exclamation-circle" class="w-3.5 h-3.5 mr-1 text-amber-500" />
              Open {{ repo.open_issues_count ?? 0 }}
            </span>
            <span class="flex items-center">
              <UIcon name="i-heroicons-check-circle" class="w-3.5 h-3.5 mr-1 text-emerald-500" />
              Closed {{ repo.closed_issues_count ?? 0 }}
            </span>
          </div>
        </NuxtLink>
      </div>
      <div v-else class="text-center py-20 text-sm text-gray-400 dark:text-gray-500">暂无绑定仓库</div>
    </template>

    <!-- Create Modal -->
    <UModal v-model:open="showCreateModal" title="添加仓库" :ui="{ width: 'sm:max-w-lg' }">
      <template #content>
        <div class="modal-form">
          <div class="modal-header">
            <h3>添加仓库</h3>
            <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showCreateModal = false" />
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label>仓库全名 <span class="text-red-400">*</span></label>
              <UInput v-model="form.full_name" placeholder="如 org/repo-name" />
            </div>
            <div class="form-row">
              <label>GitHub URL</label>
              <UInput v-model="form.url" placeholder="https://github.com/org/repo-name" />
            </div>
            <div class="form-row">
              <label>描述</label>
              <UTextarea v-model="form.description" placeholder="仓库描述" :rows="3" />
            </div>
            <div class="form-grid-2">
              <div class="form-row">
                <label>主要语言</label>
                <UInput v-model="form.language" placeholder="如 Python" />
              </div>
              <div class="form-row">
                <label>默认分支</label>
                <UInput v-model="form.default_branch" placeholder="main" />
              </div>
            </div>
            <p v-if="createError" class="text-sm text-red-500">{{ createError }}</p>
          </div>
          <div class="modal-footer">
            <UButton variant="outline" color="neutral" @click="showCreateModal = false">取消</UButton>
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
    createError.value = formatApiError(e, '添加失败')
  } finally {
    creating.value = false
  }
}

function formatApiError(e: any, fallback: string): string {
  const data = e?.data || e?.response?._data
  if (data && typeof data === 'object') {
    const msgs = Object.entries(data)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
      .join('; ')
    if (msgs) return msgs
  }
  return e?.message || fallback
}

onMounted(fetchRepos)
</script>

<style scoped>
.modal-form { padding: 1.5rem 2rem; }
.modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
.modal-header h3 { font-size: 1.125rem; font-weight: 600; color: #111827; }
:root.dark .modal-header h3 { color: #f3f4f6; }
.modal-body { display: flex; flex-direction: column; gap: 1rem; }
.form-row { display: flex; flex-direction: column; gap: 0.375rem; }
.form-row label { font-size: 0.8125rem; font-weight: 500; color: #374151; }
:root.dark .form-row label { color: #9ca3af; }
.form-row :deep(input),
.form-row :deep(textarea),
.form-row :deep(select),
.form-row :deep(button[role="combobox"]),
.form-row :deep([data-part="trigger"]) { width: 100% !important; }
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #f3f4f6; }
:root.dark .modal-footer { border-top-color: #374151; }
</style>
