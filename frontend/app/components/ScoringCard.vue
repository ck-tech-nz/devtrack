<template>
  <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
    <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">{{ title }}</h3>
    <p v-if="description" class="text-xs text-gray-400 dark:text-gray-500 mb-4">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>
