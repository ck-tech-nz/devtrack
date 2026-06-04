<template>
  <div class="section-card">
    <div class="section-header">
      <h3 class="section-title">
        提及我的
        <span class="section-badge">{{ mentions.length }}</span>
      </h3>
      <NuxtLink to="/app/notifications" class="section-link">查看全部</NuxtLink>
    </div>
    <div class="todo-list">
      <NuxtLink
        v-for="n in mentions"
        :key="n.id"
        :to="n.source_issue_id ? `/app/issues/${n.source_issue_id}` : `/app/notifications/${n.id}`"
        class="todo-row"
      >
        <span class="dot dot--info" />
        <span class="todo-title">{{ n.title }}</span>
        <span class="activity-time">{{ timeAgo(n.created_at) }}</span>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { timeAgo } from '~/utils/timeAgo'
defineProps<{ mentions: any[] }>()
</script>

<style scoped>
.section-card { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 0.75rem; padding: 1.25rem; }
:root.dark .section-card { background-color: #1f2937; border-color: #374151; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.section-title { font-size: 0.875rem; font-weight: 600; color: #111827; display: flex; align-items: center; gap: 0.5rem; }
:root.dark .section-title { color: #f3f4f6; }
.section-badge { font-size: 0.75rem; font-weight: 500; color: #9ca3af; }
.section-link { font-size: 0.75rem; color: #7c3aed; transition: color 0.15s; }
.section-link:hover { color: #6d28d9; }
.todo-list { display: flex; flex-direction: column; }
.todo-row { display: flex; align-items: center; gap: 0.625rem; padding: 0.5rem 0.5rem; margin: 0 -0.5rem; border-radius: 0.375rem; transition: background-color 0.15s; }
.todo-row:not(:last-child) { border-bottom: 1px solid #f3f4f6; border-radius: 0; margin-bottom: 0; }
:root.dark .todo-row:not(:last-child) { border-bottom-color: rgba(255, 255, 255, 0.04); }
.todo-row:hover { background-color: #f9fafb; }
:root.dark .todo-row:hover { background-color: rgba(255, 255, 255, 0.03); }
.todo-title { flex: 1; font-size: 0.8125rem; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:root.dark .todo-title { color: #d1d5db; }
.dot { width: 0.5rem; height: 0.5rem; border-radius: 9999px; flex-shrink: 0; }
.dot--info { background-color: #8b5cf6; }
.activity-time { font-size: 0.6875rem; color: #9ca3af; flex-shrink: 0; white-space: nowrap; }
</style>
