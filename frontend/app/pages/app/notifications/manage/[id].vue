<template>
  <div class="max-w-3xl mx-auto">
    <div class="mb-4">
      <NuxtLink to="/app/notifications/manage" class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1">
        <UIcon name="i-heroicons-arrow-left" class="w-4 h-4" />
        返回通知管理
      </NuxtLink>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-gray-400">加载中...</div>
    <div v-else-if="!notification" class="py-12 text-center text-sm text-gray-400">通知不存在</div>
    <template v-else>
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100">通知详情</h1>
          <span
            v-if="notification.is_draft"
            class="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
          >
            草稿
          </span>
          <span v-else class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
            已发布 · {{ notification.recipient_count }} 人
          </span>
        </div>
        <div class="flex items-center gap-2">
          <UButton
            v-if="notification.is_draft"
            icon="i-heroicons-paper-airplane"
            size="sm"
            @click="publish"
            :loading="publishing"
          >
            发布
          </UButton>
          <UButton
            v-if="!editing"
            icon="i-heroicons-pencil-square"
            variant="soft"
            size="sm"
            @click="editing = true"
          >
            编辑
          </UButton>
          <UButton
            icon="i-heroicons-trash"
            variant="soft"
            color="error"
            size="sm"
            @click="handleDelete"
          >
            删除
          </UButton>
        </div>
      </div>

      <!-- View mode -->
      <div v-if="!editing" class="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ notification.title }}</h2>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span>{{ typeLabel(notification.notification_type) }}</span>
            <span>目标: {{ targetLabel }}</span>
            <span>{{ new Date(notification.created_at).toLocaleString('zh-CN') }}</span>
          </div>
        </div>
        <div class="px-6 py-5 markdown-body text-sm" v-html="renderedContent" />
      </div>

      <!-- Edit mode -->
      <NotificationForm
        v-if="editing"
        :initial="notification"
        @saved="onSaved"
        @cancel="editing = false"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { api } = useApi()
const { md } = useMentionMarkdown()
const toast = useToast()

const loading = ref(true)
const editing = ref(false)
const publishing = ref(false)
const notification = ref<any>(null)

const renderedContent = computed(() => {
  if (!notification.value?.content) return '<p class="text-gray-400">无内容</p>'
  return md.render(notification.value.content)
})

const targetLabel = computed(() => {
  if (!notification.value) return ''
  const n = notification.value
  if (n.target_type === 'all') return '全员'
  if (n.target_type === 'group') return `组: ${n.target_group_name || '未知'}`
  if (n.target_type === 'user') return `${(n.target_user_ids || []).length} 个用户`
  return n.target_type
})

function typeLabel(type: string) {
  return { mention: '提及', system: '系统', broadcast: '广播' }[type] || type
}

async function loadNotification() {
  try {
    notification.value = await api(`/api/notifications/manage/${route.params.id}/`)
  } catch {
    notification.value = null
  }
  loading.value = false
}

async function publish() {
  publishing.value = true
  try {
    const data = await api<{ recipients: number }>(`/api/notifications/manage/${route.params.id}/publish/`, { method: 'POST' })
    toast.add({ title: `已发布，${data.recipients} 人收到通知`, color: 'success' })
    await loadNotification()
  } catch (e: any) {
    toast.add({ title: e?.data?.detail || '发布失败', color: 'error' })
  }
  publishing.value = false
}

async function handleDelete() {
  if (!confirm('确定删除此通知？')) return
  await api(`/api/notifications/manage/${route.params.id}/`, { method: 'DELETE' })
  toast.add({ title: '已删除', color: 'success' })
  navigateTo('/app/notifications/manage')
}

function onSaved() {
  editing.value = false
  loadNotification()
}

onMounted(loadNotification)
</script>
