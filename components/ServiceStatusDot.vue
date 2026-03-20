<template>
  <span
    class="inline-block w-2 h-2 rounded-full flex-shrink-0"
    :class="online ? 'bg-emerald-400' : 'bg-gray-300'"
    :title="online ? '在线' : '离线'"
  />
</template>

<script setup lang="ts">
defineProps<{ online: boolean }>()
</script>
