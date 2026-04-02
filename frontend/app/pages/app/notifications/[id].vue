<template>
  <div class="max-w-3xl mx-auto">
    <!-- Back link -->
    <div class="mb-4">
      <NuxtLink to="/app/notifications" class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1">
        <UIcon name="i-heroicons-arrow-left" class="w-4 h-4" />
        返回通知列表
      </NuxtLink>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-gray-400">加载中...</div>
    <div v-else-if="!notification" class="py-12 text-center text-sm text-gray-400">通知不存在</div>
    <div v-else class="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl overflow-hidden">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
        <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ notification.title }}</h1>
        <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
          <span v-if="notification.source_user_name">来自 {{ notification.source_user_name }}</span>
          <span>{{ formatTime(notification.created_at) }}</span>
          <NuxtLink
            v-if="notification.source_issue_id"
            :to="`/app/issues/${notification.source_issue_id}`"
            class="text-primary-600 dark:text-primary-400 hover:underline"
          >
            查看关联问题 #{{ notification.source_issue_id }}
          </NuxtLink>
        </div>
      </div>

      <!-- Content -->
      <div
        class="px-6 py-5 markdown-body text-sm"
        v-html="renderedContent"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { NotificationItem } from '~/composables/useNotifications'

const route = useRoute()
const { api } = useApi()
const { md } = useMentionMarkdown()

const loading = ref(true)
const notification = ref<NotificationItem | null>(null)

const renderedContent = computed(() => {
  if (!notification.value?.content) return '<p class="text-gray-400">无内容</p>'
  return md.render(notification.value.content)
})

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(async () => {
  try {
    notification.value = await api<NotificationItem>(`/api/notifications/${route.params.id}/`)
  } catch {
    notification.value = null
  }
  loading.value = false
})
</script>

<style>
/* Reuse markdown-body styles from MarkdownEditor */
</style>
