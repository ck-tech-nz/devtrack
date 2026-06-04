<template>
  <div class="section-card">
    <div class="section-header">
      <h3 class="section-title">
        我的任务
        <span class="section-badge">{{ tasks.length }}</span>
      </h3>
      <NuxtLink to="/app/ai/my-plan" class="section-link">查看全部</NuxtLink>
    </div>
    <div class="todo-list">
      <NuxtLink
        v-for="t in tasks"
        :key="t.id"
        to="/app/ai/my-plan"
        class="todo-row"
      >
        <span class="dot" :class="taskDotClass(t.priority)" />
        <span class="todo-title">{{ t.title }}</span>
        <span
          v-if="t.due_date"
          class="todo-priority"
          :class="taskOverdue(t) ? 'todo-priority--urgent' : 'todo-priority--low'"
        >截止 {{ t.due_date }}</span>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ tasks: any[] }>()

function taskDotClass(priority: string): string {
  if (priority === 'high') return 'dot--high'
  if (priority === 'medium') return 'dot--mid'
  return 'dot--low'
}
function taskOverdue(t: any): boolean {
  if (!t.due_date) return false
  const d = new Date()
  const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return t.due_date < today
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
.todo-list { display: flex; flex-direction: column; }
.todo-row { display: flex; align-items: center; gap: 0.625rem; padding: 0.5rem 0.5rem; margin: 0 -0.5rem; border-radius: 0.375rem; transition: background-color 0.15s; }
.todo-row:not(:last-child) { border-bottom: 1px solid #f3f4f6; border-radius: 0; margin-bottom: 0; }
:root.dark .todo-row:not(:last-child) { border-bottom-color: rgba(255, 255, 255, 0.04); }
.todo-row:hover { background-color: #f9fafb; }
:root.dark .todo-row:hover { background-color: rgba(255, 255, 255, 0.03); }
.todo-title { flex: 1; font-size: 0.8125rem; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:root.dark .todo-title { color: #d1d5db; }
.dot { width: 0.5rem; height: 0.5rem; border-radius: 9999px; flex-shrink: 0; }
.dot--high { background-color: #f59e0b; }
.dot--mid { background-color: #3b82f6; }
.dot--low { background-color: #9ca3af; }
.todo-priority { font-size: 0.6875rem; padding: 0.0625rem 0.4375rem; border-radius: 0.25rem; flex-shrink: 0; font-weight: 500; }
.todo-priority--urgent { background-color: #fef2f2; color: #dc2626; }
:root.dark .todo-priority--urgent { background-color: rgba(239, 68, 68, 0.15); color: #fca5a5; }
.todo-priority--low { background-color: #f9fafb; color: #6b7280; }
:root.dark .todo-priority--low { background-color: rgba(255, 255, 255, 0.05); color: #9ca3af; }
</style>
