<template>
  <div class="max-w-3xl mx-auto">
    <div class="mb-4">
      <NuxtLink to="/app/notifications/manage" class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1">
        <UIcon name="i-heroicons-arrow-left" class="w-4 h-4" />
        返回通知管理
      </NuxtLink>
    </div>

    <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">新建通知</h1>

    <NotificationForm @saved="onSaved" />
  </div>
</template>

<script setup lang="ts">
function onSaved(data: { id: string }) {
  navigateTo(`/app/notifications/manage/${data.id}`)
}
</script>
