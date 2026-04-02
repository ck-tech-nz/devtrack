<template>
  <div class="max-w-4xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100">通知管理</h1>
      <UButton
        icon="i-heroicons-plus"
        size="sm"
        @click="navigateTo('/app/notifications/manage/create')"
      >
        新建广播
      </UButton>
    </div>

    <!-- Notification list -->
    <div class="space-y-2">
      <div v-if="loading" class="py-12 text-center text-sm text-gray-400">加载中...</div>
      <div v-else-if="data && data.results.length === 0" class="py-12 text-center text-sm text-gray-400">
        暂无通知
      </div>
      <div
        v-for="n in data?.results"
        :key="n.id"
        class="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl"
      >
        <!-- Type badge -->
        <span
          class="px-2 py-0.5 text-xs rounded-full flex-shrink-0"
          :class="typeBadge(n.notification_type)"
        >
          {{ typeLabel(n.notification_type) }}
        </span>

        <!-- Title -->
        <div class="flex-1 min-w-0">
          <span class="text-sm text-gray-900 dark:text-gray-100 truncate block">{{ n.title }}</span>
          <span v-if="n.source_user_name" class="text-xs text-gray-400">{{ n.source_user_name }}</span>
        </div>

        <!-- Time -->
        <span class="text-xs text-gray-400 flex-shrink-0">{{ formatTime(n.created_at) }}</span>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="data && data.count > 20" class="flex justify-center mt-6">
      <UPagination
        :model-value="page"
        :total="data.count"
        :items-per-page="20"
        @update:model-value="page = $event"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { NotificationItem } from '~/composables/useNotifications'

const { api } = useApi()

const page = ref(1)
const loading = ref(false)
const data = ref<{ count: number; results: NotificationItem[] } | null>(null)

async function load() {
  loading.value = true
  const params = page.value > 1 ? `?page=${page.value}` : ''
  data.value = await api(`/api/notifications/manage/${params}`)
  loading.value = false
}

function typeLabel(type: string) {
  return { mention: '提及', system: '系统', broadcast: '广播' }[type] || type
}

function typeBadge(type: string) {
  return {
    mention: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    system: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    broadcast: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  }[type] || 'bg-gray-100 text-gray-700'
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

watch(page, load)
onMounted(load)
</script>
