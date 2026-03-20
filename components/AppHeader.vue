<template>
  <header class="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6 lg:px-8 flex-shrink-0">
    <nav class="flex items-center space-x-2 text-sm">
      <template v-for="(crumb, idx) in breadcrumbs" :key="idx">
        <UIcon v-if="idx > 0" name="i-heroicons-chevron-right-20-solid" class="w-4 h-4 text-gray-300" />
        <NuxtLink v-if="crumb.to" :to="crumb.to" class="text-gray-400 hover:text-gray-700 transition-colors">
          {{ crumb.label }}
        </NuxtLink>
        <span v-else class="text-gray-900 font-medium">{{ crumb.label }}</span>
      </template>
    </nav>

    <div class="flex items-center space-x-3">
      <UButton icon="i-heroicons-bell" variant="ghost" color="gray" size="sm" class="relative">
        <span class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-crystal-500 rounded-full" />
      </UButton>

      <UDropdown :items="userMenuItems" :popper="{ placement: 'bottom-end' }">
        <button class="flex items-center space-x-2 hover:bg-gray-50 rounded-lg px-2 py-1.5 transition-colors">
          <div class="w-8 h-8 rounded-full bg-crystal-100 flex items-center justify-center">
            <span class="text-crystal-600 text-sm font-medium">管</span>
          </div>
          <span class="text-sm text-gray-700 font-medium hidden sm:inline">管理员</span>
          <UIcon name="i-heroicons-chevron-down-20-solid" class="w-4 h-4 text-gray-400" />
        </button>
      </UDropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
const { breadcrumbs } = useNavigation()
const router = useRouter()

const userMenuItems = [
  [{
    label: '退出登录',
    icon: 'i-heroicons-arrow-right-on-rectangle',
    click: () => router.push('/'),
  }],
]
</script>
