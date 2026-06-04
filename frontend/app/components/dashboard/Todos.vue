<template>
  <div class="section-card">
    <button
      class="section-header section-toggle"
      :class="{ 'section-toggle--collapsed': !show }"
      type="button"
      @click="show = !show"
    >
      <h3 class="section-title">
        我的待办
        <span class="section-badge">{{ issues.length }}</span>
      </h3>
      <div class="section-toggle-right">
        <NuxtLink to="/app/issues?assignee=me" class="section-link" @click.stop>查看全部</NuxtLink>
        <UIcon :name="show ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'" class="w-4 h-4 text-gray-400" />
      </div>
    </button>
    <div v-if="show" class="todo-list">
      <NuxtLink
        v-for="issue in issues"
        :key="issue.id"
        :to="`/app/issues/${issue.id}`"
        class="todo-row"
      >
        <span class="dot" :class="priorityDotClass(issue.priority)" />
        <span class="todo-id">{{ formatIssueId(issue.id) }}</span>
        <span class="todo-title">{{ issue.title }}</span>
        <span
          v-if="isTester && issue.status === '已解决'"
          class="todo-priority todo-priority--verify"
        >待验证</span>
        <span class="todo-priority" :class="priorityPillClass(issue.priority)">{{ issue.priority }}</span>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ issues: any[]; isTester: boolean }>()
const show = ref(false)

function formatIssueId(id: number): string {
  return `ISS-${String(id).padStart(3, '0')}`
}
function priorityDotClass(priority: string): string {
  switch (priority) {
    case '紧急': return 'dot--urgent'
    case '高': return 'dot--high'
    case '中': return 'dot--mid'
    case '低': return 'dot--low'
    default: return 'dot--low'
  }
}
function priorityPillClass(priority: string): string {
  switch (priority) {
    case '紧急': return 'todo-priority--urgent'
    case '高': return 'todo-priority--high'
    case '中': return 'todo-priority--mid'
    case '低': return 'todo-priority--low'
    default: return 'todo-priority--low'
  }
}
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
.section-toggle { width: 100%; background: transparent; border: 0; cursor: pointer; padding: 0; font: inherit; color: inherit; text-align: left; }
.section-toggle--collapsed { margin-bottom: 0; }
.section-toggle:hover .section-title { color: #7c3aed; }
:root.dark .section-toggle:hover .section-title { color: #c4b5fd; }
.section-toggle-right { display: flex; align-items: center; gap: 0.625rem; }
.todo-list { display: flex; flex-direction: column; }
.todo-row { display: flex; align-items: center; gap: 0.625rem; padding: 0.5rem 0.5rem; margin: 0 -0.5rem; border-radius: 0.375rem; transition: background-color 0.15s; }
.todo-row:not(:last-child) { border-bottom: 1px solid #f3f4f6; border-radius: 0; margin-bottom: 0; }
:root.dark .todo-row:not(:last-child) { border-bottom-color: rgba(255, 255, 255, 0.04); }
.todo-row:hover { background-color: #f9fafb; }
:root.dark .todo-row:hover { background-color: rgba(255, 255, 255, 0.03); }
.todo-id { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.6875rem; color: #9ca3af; flex-shrink: 0; }
.todo-title { flex: 1; font-size: 0.8125rem; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:root.dark .todo-title { color: #d1d5db; }
.dot { width: 0.5rem; height: 0.5rem; border-radius: 9999px; flex-shrink: 0; }
.dot--urgent { background-color: #ef4444; }
.dot--high { background-color: #f59e0b; }
.dot--mid { background-color: #3b82f6; }
.dot--low { background-color: #9ca3af; }
.todo-priority { font-size: 0.6875rem; padding: 0.0625rem 0.4375rem; border-radius: 0.25rem; flex-shrink: 0; font-weight: 500; }
.todo-priority--urgent { background-color: #fef2f2; color: #dc2626; }
:root.dark .todo-priority--urgent { background-color: rgba(239, 68, 68, 0.15); color: #fca5a5; }
.todo-priority--high { background-color: #fffbeb; color: #d97706; }
:root.dark .todo-priority--high { background-color: rgba(245, 158, 11, 0.15); color: #fcd34d; }
.todo-priority--mid { background-color: #eff6ff; color: #2563eb; }
:root.dark .todo-priority--mid { background-color: rgba(59, 130, 246, 0.15); color: #93c5fd; }
.todo-priority--low { background-color: #f9fafb; color: #6b7280; }
:root.dark .todo-priority--low { background-color: rgba(255, 255, 255, 0.05); color: #9ca3af; }
.todo-priority--verify { background-color: #ecfdf5; color: #059669; }
:root.dark .todo-priority--verify { background-color: rgba(16, 185, 129, 0.15); color: #6ee7b7; }
</style>
