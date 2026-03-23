<template>
  <div class="space-y-6 max-w-2xl">
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400">加载中...</div>
    </div>

    <template v-else-if="user">
      <div class="flex items-center gap-4">
        <img v-if="user.avatar" :src="resolveAvatarUrl(user.avatar)" class="w-16 h-16 rounded-full" />
        <div v-else class="w-16 h-16 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center text-xl font-semibold text-crystal-600 dark:text-crystal-400">
          {{ (user.name || user.username || '?').slice(0, 1) }}
        </div>
        <div>
          <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">{{ user.username }}</h1>
          <UBadge :color="user.is_active ? 'success' : 'warning'" variant="subtle" size="sm" class="mt-1">
            {{ user.is_active ? '已激活' : '待审批' }}
          </UBadge>
        </div>
        <div class="ml-auto">
          <UButton
            :color="user.is_active ? 'warning' : 'success'"
            variant="soft"
            :loading="toggling"
            @click="toggleActive"
          >
            {{ user.is_active ? '停用用户' : '激活用户' }}
          </UButton>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <UFormField label="用户名">
            <UInput :model-value="user.username" disabled size="lg" class="w-full" />
          </UFormField>
          <UFormField label="昵称">
            <UInput v-model="form.name" size="lg" class="w-full" />
          </UFormField>
        </div>
        <UFormField label="邮箱">
          <UInput v-model="form.email" type="email" size="lg" class="w-full" />
        </UFormField>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">头像</label>
          <AvatarPicker v-model="form.avatar" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">用户组</label>
          <div class="flex gap-2 flex-wrap items-center">
            <UBadge v-for="g in form.groups" :key="g" color="primary" variant="subtle" class="gap-1">
              {{ g }}
              <button type="button" class="hover:text-red-500" @click="form.groups = form.groups.filter(x => x !== g)">&times;</button>
            </UBadge>
            <USelect
              :items="availableGroups"
              placeholder="+ 添加"
              size="sm"
              class="w-32"
              @update:model-value="addGroup"
            />
          </div>
        </div>
        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <div class="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
          <UButton variant="outline" color="neutral" @click="$router.back()">取消</UButton>
          <UButton :loading="saving" @click="handleSave">保存</UButton>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { api } = useApi()
const { resolveAvatarUrl } = useAvatars()

const loading = ref(true)
const saving = ref(false)
const toggling = ref(false)
const error = ref('')
const user = ref<any>(null)
const allGroups = ref<string[]>([])

const form = ref({ name: '', email: '', avatar: '', groups: [] as string[] })

const availableGroups = computed(() =>
  allGroups.value.filter(g => !form.value.groups.includes(g))
)

function addGroup(name: string) {
  if (name && !form.value.groups.includes(name)) {
    form.value.groups.push(name)
  }
}

async function toggleActive() {
  toggling.value = true
  try {
    const data = await api<any>(`/api/users/${route.params.id}/`, {
      method: 'PATCH',
      body: { is_active: !user.value.is_active },
    })
    user.value = { ...user.value, ...data }
  } catch (e) {
    console.error('Toggle failed:', e)
  } finally {
    toggling.value = false
  }
}

async function handleSave() {
  saving.value = true
  error.value = ''
  try {
    const data = await api<any>(`/api/users/${route.params.id}/`, {
      method: 'PATCH',
      body: { name: form.value.name, email: form.value.email, avatar: form.value.avatar, groups: form.value.groups },
    })
    user.value = { ...user.value, ...data }
    form.value = { name: data.name, email: data.email, avatar: data.avatar, groups: data.groups || [] }
  } catch (e: any) {
    error.value = '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [userData, groupsData] = await Promise.all([
      api<any>(`/api/users/${route.params.id}/`),
      api<any>('/api/page-perms/groups/').catch(() => []),
    ])
    user.value = userData
    form.value = { name: userData.name, email: userData.email, avatar: userData.avatar, groups: userData.groups || [] }
    allGroups.value = (Array.isArray(groupsData) ? groupsData : groupsData.results || []).map((g: any) => g.name)
  } catch (e) {
    console.error('Failed to load user:', e)
  } finally {
    loading.value = false
  }
})
</script>
