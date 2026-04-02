<template>
  <div class="max-w-3xl mx-auto">
    <div class="mb-4">
      <NuxtLink to="/app/notifications/manage" class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1">
        <UIcon name="i-heroicons-arrow-left" class="w-4 h-4" />
        返回通知管理
      </NuxtLink>
    </div>

    <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">发送广播通知</h1>

    <div class="space-y-4">
      <!-- Title -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">标题</label>
        <input
          v-model="form.title"
          type="text"
          placeholder="通知标题"
          class="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-gray-100 outline-none focus:border-primary-500"
        />
      </div>

      <!-- Target -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">目标</label>
        <div class="flex gap-2">
          <UButton
            :variant="form.target_type === 'all' ? 'solid' : 'outline'"
            size="xs"
            @click="form.target_type = 'all'"
          >
            全员
          </UButton>
        </div>
      </div>

      <!-- Content -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">内容（支持 Markdown）</label>
        <MarkdownEditor
          v-model="form.content"
          placeholder="通知内容，支持 Markdown 格式和图片上传..."
        />
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-3 pt-2">
        <UButton
          :loading="sending"
          :disabled="!form.title.trim()"
          @click="send"
        >
          发送通知
        </UButton>
        <span v-if="result" class="text-sm text-green-600">
          发送成功，{{ result.recipients }} 人收到通知
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { api } = useApi()
const toast = useToast()

const form = reactive({
  title: '',
  content: '',
  target_type: 'all' as string,
})

const sending = ref(false)
const result = ref<{ id: string; recipients: number } | null>(null)

async function send() {
  sending.value = true
  result.value = null
  try {
    const data = await api<{ id: string; recipients: number }>('/api/notifications/manage/create/', {
      method: 'POST',
      body: form,
    })
    result.value = data
    toast.add({ title: `通知已发送，${data.recipients} 人收到`, color: 'success' })
  } catch (e: any) {
    toast.add({ title: e?.data?.detail || '发送失败', color: 'error' })
  }
  sending.value = false
}
</script>
