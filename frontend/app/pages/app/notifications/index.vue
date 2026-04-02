<template>
  <div class="max-w-3xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100">通知中心</h1>
      <UButton
        v-if="unreadCount > 0"
        variant="soft"
        size="sm"
        @click="handleMarkAllRead"
      >
        全部已读
      </UButton>
    </div>

    <!-- Filter tabs -->
    <div class="flex gap-1 mb-4">
      <UButton
        v-for="tab in tabs"
        :key="tab.value"
        :variant="activeTab === tab.value ? 'solid' : 'ghost'"
        size="xs"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
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
        class="flex items-center gap-3 p-4 bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
        :class="{ 'border-l-2 border-l-primary-500': !n.is_read }"
        @click="goToDetail(n)"
      >
        <!-- Unread dot -->
        <span
          v-if="!n.is_read"
          class="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0"
        />
        <div v-else class="w-2 flex-shrink-0" />

        <!-- Title + time -->
        <div class="flex-1 min-w-0">
          <span class="text-sm text-gray-900 dark:text-gray-100 truncate block" :class="{ 'font-medium': !n.is_read }">{{ n.title }}</span>
        </div>
        <span class="text-xs text-gray-400 flex-shrink-0">{{ formatTime(n.created_at) }}</span>

        <!-- Actions -->
        <div class="flex items-center gap-1 flex-shrink-0" @click.stop>
          <UButton
            v-if="!n.is_read"
            icon="i-heroicons-check"
            variant="ghost"
            color="neutral"
            size="xs"
            title="标记已读"
            @click="handleMarkRead(n)"
          />
          <UButton
            icon="i-heroicons-trash"
            variant="ghost"
            color="neutral"
            size="xs"
            title="删除"
            @click="handleDelete(n)"
          />
        </div>
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
const { unreadCount, fetchNotifications, markRead, markAllRead, deleteNotification, fetchUnreadCount } = useNotifications()

const tabs = [
  { label: '全部', value: 'all' },
  { label: '未读', value: 'unread' },
  { label: '已读', value: 'read' },
]

const activeTab = ref('all')
const page = ref(1)
const loading = ref(false)
const data = ref<Awaited<ReturnType<typeof fetchNotifications>> | null>(null)

async function load() {
  loading.value = true
  const params: { is_read?: string; page?: number } = {}
  if (activeTab.value === 'unread') params.is_read = 'false'
  if (activeTab.value === 'read') params.is_read = 'true'
  if (page.value > 1) params.page = page.value
  data.value = await fetchNotifications(params)
  loading.value = false
}

function goToDetail(n: { id: string; is_read: boolean }) {
  if (!n.is_read) markRead(n.id)
  navigateTo(`/app/notifications/${n.id}`)
}

async function handleMarkRead(n: { id: string; is_read: boolean }) {
  await markRead(n.id)
  n.is_read = true
}

async function handleMarkAllRead() {
  await markAllRead()
  await load()
}

async function handleDelete(n: { id: string }) {
  await deleteNotification(n.id)
  await fetchUnreadCount()
  await load()
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`
  return date.toLocaleDateString('zh-CN')
}

watch(activeTab, () => {
  page.value = 1
  load()
})

watch(page, load)

onMounted(load)
</script>
