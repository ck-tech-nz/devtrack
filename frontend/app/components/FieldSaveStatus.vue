<template>
  <Transition name="save-status" mode="out-in">
    <span v-if="saving" key="saving" class="inline-flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
      <UIcon name="i-heroicons-arrow-path" class="w-3 h-3 animate-spin" />保存中
    </span>
    <span v-else-if="saved" key="saved" class="inline-flex items-center gap-1 text-xs text-emerald-500 dark:text-emerald-400">
      <UIcon name="i-heroicons-check-circle" class="w-3.5 h-3.5" />已保存
    </span>
  </Transition>
</template>

<script setup lang="ts">
defineProps<{ saving?: boolean; saved?: boolean }>()
</script>

<style scoped>
.save-status-enter-active,
.save-status-leave-active {
  transition: opacity 0.2s ease;
}
.save-status-enter-from,
.save-status-leave-to {
  opacity: 0;
}
</style>
