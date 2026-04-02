<template>
  <div class="max-w-4xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100">通知管理</h1>
      <UButton
        icon="i-heroicons-plus"
        size="sm"
        @click="navigateTo('/app/notifications/manage/create')"
      >
        新建通知
      </UButton>
    </div>

    <div class="space-y-2">
      <div v-if="loading" class="py-12 text-center text-sm text-gray-400">加载中...</div>
      <div v-else-if="data && data.results.length === 0" class="py-12 text-center text-sm text-gray-400">
        暂无通知
      </div>
      <div
        v-for="n in data?.results"
        :key="n.id"
        class="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
        @click="navigateTo(`/app/notifications/manage/${n.id}`)"
      >
        <!-- Status -->
        <span
          class="px-2 py-0.5 text-xs rounded-full flex-shrink-0"
          :class="n.is_draft
            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
            : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'"
        >
          {{ n.is_draft ? '草稿' : '已发布' }}
        </span>

        <!-- Type -->
        <span class="px-2 py-0.5 text-xs rounded-full flex-shrink-0" :class="typeBadge(n.notification_type)">
          {{ typeLabel(n.notification_type) }}
        </span>

        <!-- Title + target -->
        <div class="flex-1 min-w-0">
          <span class="text-sm text-gray-900 dark:text-gray-100 truncate block">{{ n.title }}</span>
          <span class="text-xs text-gray-400">{{ targetLabel(n) }}</span>
        </div>

        <!-- Recipient count -->
        <span v-if="!n.is_draft" class="text-xs text-gray-400 flex-shrink-0">
          {{ n.recipient_count }} 人
        </span>

        <!-- Time -->
        <span class="text-xs text-gray-400 flex-shrink-0">{{ formatTime(n.created_at) }}</span>
      </div>
    </div>

    <div v-if="data && data.count > 20" class="flex justify-center mt-6">
      <UPagination :model-value="page" :total="data.count" :items-per-page="20" @update:model-value="page = $event" />
    </div>
  </div>
</template>

<script setup lang="ts">
const { api } = useApi()

const page = ref(1)
const loading = ref(false)
const data = ref<any>(null)

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
    broadcast: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  }[type] || 'bg-gray-100 text-gray-700'
}

function targetLabel(n: any) {
  if (n.target_type === 'all') return '全员'
  if (n.target_type === 'group') return `组: ${n.target_group_name || '未知'}`
  if (n.target_type === 'user') return `${(n.target_user_ids || []).length} 个用户`
  return ''
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

watch(page, load)
onMounted(load)
</script>
