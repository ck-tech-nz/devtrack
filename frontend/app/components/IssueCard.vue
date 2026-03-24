<template>
  <NuxtLink
    :to="`/app/issues/${issue.id}`"
    class="block bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border border-white/85 dark:border-gray-700/50 rounded-xl p-3 active:scale-[0.98] transition-transform"
  >
    <div class="flex items-start justify-between gap-2">
      <p class="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2 flex-1">
        {{ issue.title }}
      </p>
      <UBadge
        :color="issue.priority === 'P0' ? 'error' : issue.priority === 'P1' ? 'warning' : issue.priority === 'P2' ? 'warning' : 'neutral'"
        variant="subtle"
        size="xs"
        class="flex-shrink-0"
      >
        {{ issue.priority }}
      </UBadge>
    </div>
    <div class="mt-2 flex items-center gap-2 text-[11px] text-gray-400 dark:text-gray-500">
      <UBadge
        :color="issue.status === '待处理' ? 'warning' : issue.status === '进行中' ? 'info' : issue.status === '已解决' ? 'success' : 'neutral'"
        variant="subtle"
        size="xs"
      >
        {{ issue.status }}
      </UBadge>
      <span>{{ issue.assignee_name || '-' }}</span>
      <span v-if="issue.created_at">{{ issue.created_at.slice(5, 10) }}</span>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
defineProps<{
  issue: {
    id: string | number
    title: string
    priority: string
    status: string
    assignee_name?: string
    created_at?: string
  }
}>()
</script>
