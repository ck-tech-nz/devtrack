<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400">加载中...</div>
  </div>
  <div v-else-if="repo" class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">{{ repo.full_name }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ repo.description }}</p>
      </div>
      <div class="flex items-center space-x-3">
        <UBadge color="neutral" variant="subtle">{{ repo.language }}</UBadge>
        <UBadge color="neutral" variant="subtle"><UIcon name="i-heroicons-star" class="w-3 h-3 mr-1" />{{ repo.stars }}</UBadge>
      </div>
    </div>
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">仓库信息</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">默认分支</p>
          <p class="text-sm font-medium text-gray-900">{{ repo.default_branch }}</p>
        </div>
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">绑定时间</p>
          <p class="text-sm font-medium text-gray-900">{{ repo.connected_at?.slice(0, 10) }}</p>
        </div>
        <div class="bg-gray-50 rounded-lg px-4 py-3">
          <p class="text-xs text-gray-400 mb-1">状态</p>
          <p class="text-sm font-medium text-gray-900">{{ repo.status }}</p>
        </div>
      </div>
    </div>
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">最近提交</h3>
      <p class="text-sm text-gray-400">GitHub 集成尚未接入，暂无提交记录</p>
    </div>
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">Open Pull Requests</h3>
      <p class="text-sm text-gray-400">GitHub 集成尚未接入，暂无 PR 数据</p>
    </div>
    <div class="bg-white rounded-xl border border-gray-100 p-5">
      <h3 class="text-sm font-semibold text-gray-900 mb-3">Open Issues</h3>
      <p class="text-sm text-gray-400">GitHub 集成尚未接入，暂无 Issue 数据</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { api } = useApi()
const loading = ref(true)
const repo = ref<any>(null)

onMounted(async () => {
  try {
    repo.value = await api<any>(`/api/repos/${route.params.id}/`)
  } catch (e) {
    console.error('Failed to load repo:', e)
  } finally {
    loading.value = false
  }
})
</script>
