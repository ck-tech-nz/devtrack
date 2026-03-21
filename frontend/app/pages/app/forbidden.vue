<template>
  <div class="flex items-center justify-center h-full">
    <div class="text-center space-y-4">
      <div class="w-16 h-16 mx-auto rounded-full bg-red-50 flex items-center justify-center">
        <UIcon name="i-heroicons-lock-closed" class="w-8 h-8 text-red-400" />
      </div>
      <h1 class="text-2xl font-semibold text-gray-900">无权访问</h1>
      <p class="text-gray-500 max-w-sm">你没有权限访问该页面，请联系管理员分配相应权限。</p>
      <UButton
        v-if="firstAccessible"
        :to="firstAccessible"
        color="primary"
        variant="soft"
        class="mt-4"
      >
        返回首页
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { filteredNavItems } = useNavigation()
const firstAccessible = computed(() => filteredNavItems.value[0]?.to)
</script>
