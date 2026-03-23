<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">用户管理</h1>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <div v-else class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
      <UTable :data="users" :columns="columns" :ui="{ th: 'text-xs', td: 'text-sm' }">
        <template #username-cell="{ row }">
          <NuxtLink :to="`/app/users/${row.original.id}`" class="text-crystal-500 dark:text-crystal-400 hover:text-crystal-700 dark:hover:text-crystal-300 font-medium flex items-center gap-2">
            <img v-if="row.original.avatar" :src="resolveAvatarUrl(row.original.avatar)" class="w-6 h-6 rounded-full" />
            {{ row.original.username }}
          </NuxtLink>
        </template>
        <template #is_active-cell="{ row }">
          <UBadge :color="row.original.is_active ? 'success' : 'warning'" variant="subtle" size="xs">
            {{ row.original.is_active ? '已激活' : '待审批' }}
          </UBadge>
        </template>
        <template #groups-cell="{ row }">
          <div class="flex gap-1 flex-wrap">
            <UBadge v-for="g in row.original.groups" :key="g" color="neutral" variant="subtle" size="xs">{{ g }}</UBadge>
            <span v-if="!row.original.groups?.length" class="text-gray-300 dark:text-gray-600">-</span>
          </div>
        </template>
        <template #date_joined-cell="{ row }">
          {{ row.original.date_joined?.slice(0, 10) || '-' }}
        </template>
      </UTable>
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50 dark:border-gray-800">
        <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ users.length }} 位用户</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { resolveAvatarUrl } = useAvatars()

const loading = ref(true)
const users = ref<any[]>([])

const columns = [
  { accessorKey: 'username', header: '用户名' },
  { accessorKey: 'name', header: '昵称' },
  { accessorKey: 'email', header: '邮箱' },
  { accessorKey: 'is_active', header: '状态' },
  { accessorKey: 'groups', header: '用户组' },
  { accessorKey: 'date_joined', header: '注册时间' },
]

onMounted(async () => {
  try {
    const data = await api<any>('/api/users/')
    // Handle paginated or non-paginated response
    users.value = Array.isArray(data) ? data : data.results || []
  } catch (e) {
    console.error('Failed to load users:', e)
  } finally {
    loading.value = false
  }
})
</script>
