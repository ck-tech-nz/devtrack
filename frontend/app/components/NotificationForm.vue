<template>
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

    <!-- Target Type -->
    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">目标</label>
      <div class="flex gap-2 mb-3">
        <UButton
          v-for="opt in targetOptions"
          :key="opt.value"
          :variant="form.target_type === opt.value ? 'solid' : 'outline'"
          size="xs"
          @click="form.target_type = opt.value"
        >
          {{ opt.label }}
        </UButton>
      </div>

      <!-- Group selector -->
      <div v-if="form.target_type === 'group'" class="mt-2">
        <select
          v-model="form.target_group"
          class="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-gray-100 outline-none focus:border-primary-500"
        >
          <option :value="null" disabled>请选择用户组</option>
          <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
      </div>

      <!-- User selector -->
      <div v-if="form.target_type === 'user'" class="mt-2">
        <div class="flex flex-wrap gap-2 mb-2">
          <span
            v-for="uid in form.target_user_ids"
            :key="uid"
            class="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300 text-xs rounded-full"
          >
            {{ userName(uid) }}
            <button class="hover:text-red-500" @click="removeUser(uid)">&times;</button>
          </span>
        </div>
        <select
          class="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-gray-100 outline-none focus:border-primary-500"
          @change="addUser($event)"
        >
          <option value="" disabled selected>选择用户...</option>
          <option
            v-for="u in availableUsers"
            :key="u.id"
            :value="u.id"
          >
            {{ u.name }}
          </option>
        </select>
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
        :loading="saving"
        :disabled="!form.title.trim() || !isTargetValid"
        @click="save(false)"
      >
        {{ isEdit ? '保存' : '发送通知' }}
      </UButton>
      <UButton
        variant="outline"
        :loading="saving"
        :disabled="!form.title.trim()"
        @click="save(true)"
      >
        {{ isEdit ? '保存为草稿' : '存为草稿' }}
      </UButton>
      <UButton
        v-if="isEdit"
        variant="ghost"
        @click="$emit('cancel')"
      >
        取消
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  initial?: any
}>()

const emit = defineEmits<{
  saved: [data: { id: string; recipients?: number }]
  cancel: []
}>()

const { api } = useApi()
const toast = useToast()

const isEdit = computed(() => !!props.initial)

const targetOptions = [
  { label: '全员', value: 'all' },
  { label: '用户组', value: 'group' },
  { label: '指定用户', value: 'user' },
]

const form = reactive({
  title: props.initial?.title || '',
  content: props.initial?.content || '',
  target_type: props.initial?.target_type || 'all',
  target_group: props.initial?.target_group_id || null,
  target_user_ids: [...(props.initial?.target_user_ids || [])] as number[],
})

const saving = ref(false)
const groups = ref<{ id: number; name: string }[]>([])
const users = ref<{ id: number; name: string }[]>([])

const availableUsers = computed(() =>
  users.value.filter(u => !form.target_user_ids.includes(u.id))
)

const isTargetValid = computed(() => {
  if (form.target_type === 'all') return true
  if (form.target_type === 'group') return !!form.target_group
  if (form.target_type === 'user') return form.target_user_ids.length > 0
  return false
})

function userName(id: number) {
  return users.value.find(u => u.id === id)?.name || `用户${id}`
}

function addUser(e: Event) {
  const select = e.target as HTMLSelectElement
  const id = Number(select.value)
  if (id && !form.target_user_ids.includes(id)) {
    form.target_user_ids.push(id)
  }
  select.value = ''
}

function removeUser(id: number) {
  form.target_user_ids = form.target_user_ids.filter(uid => uid !== id)
}

async function save(asDraft: boolean) {
  saving.value = true
  const body: any = {
    title: form.title,
    content: form.content,
    target_type: form.target_type,
    is_draft: asDraft,
    target_group: form.target_type === 'group' ? form.target_group : null,
    target_user_ids: form.target_type === 'user' ? form.target_user_ids : [],
  }

  try {
    let data: any
    if (isEdit.value) {
      data = await api(`/api/notifications/manage/${props.initial.id}/update/`, {
        method: 'PATCH',
        body,
      })
    } else {
      data = await api('/api/notifications/manage/create/', {
        method: 'POST',
        body,
      })
    }

    if (asDraft) {
      toast.add({ title: '已保存为草稿', color: 'success' })
    } else if (data.recipients !== undefined) {
      toast.add({ title: `已发送，${data.recipients} 人收到通知`, color: 'success' })
    } else {
      toast.add({ title: '已保存', color: 'success' })
    }
    emit('saved', data)
  } catch (e: any) {
    toast.add({ title: e?.data?.detail || '保存失败', color: 'error' })
  }
  saving.value = false
}

onMounted(async () => {
  const [groupData, userData] = await Promise.all([
    api<any[]>('/api/page-perms/groups/'),
    api<{ id: number; name: string }[]>('/api/users/choices/'),
  ])
  groups.value = groupData.map((g: any) => ({ id: g.id, name: g.name }))
  users.value = userData
})
</script>
