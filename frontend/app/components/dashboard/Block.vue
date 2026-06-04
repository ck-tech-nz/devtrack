<template>
  <!-- 普通模式:仅当可见且有内容时渲染插槽内容(根级条件,不加包裹 div,避免隐藏区块在 gap 列中留空位) -->
  <slot v-if="!editing && visible && available" />

  <!-- 编辑模式:渲染所有区块(含占位),叠加控件条 -->
  <div v-else-if="editing" class="db-edit" :class="{ 'db-edit--hidden': !visible }">
    <div class="db-edit-bar">
      <span class="db-edit-title">{{ title }}</span>
      <span v-if="!visible" class="db-edit-flag">已隐藏</span>
      <div class="db-edit-actions">
        <button type="button" class="db-btn" :disabled="isFirst" title="上移" @click="moveUp(id)">
          <UIcon name="i-heroicons-arrow-up" class="db-icon" />
        </button>
        <button type="button" class="db-btn" :disabled="isLast" title="下移" @click="moveDown(id)">
          <UIcon name="i-heroicons-arrow-down" class="db-icon" />
        </button>
        <button type="button" class="db-btn" :title="visible ? '隐藏' : '显示'" @click="toggleVisible(id)">
          <UIcon :name="visible ? 'i-heroicons-eye' : 'i-heroicons-eye-slash'" class="db-icon" />
        </button>
      </div>
    </div>
    <div v-if="available" class="db-edit-body">
      <slot />
    </div>
    <div v-else class="db-edit-placeholder">{{ emptyText }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  id: string
  title: string
  available: boolean
  visible: boolean
  isFirst: boolean
  isLast: boolean
  emptyText: string
}>()
const { editing, moveUp, moveDown, toggleVisible } = useDashboardLayout()
</script>

<style scoped>
.db-edit { border: 1px dashed #c4b5fd; border-radius: 0.75rem; padding: 0.5rem; }
:root.dark .db-edit { border-color: #6d28d9; }
.db-edit--hidden { opacity: 0.55; }
.db-edit-bar { display: flex; align-items: center; gap: 0.5rem; padding: 0.25rem 0.5rem 0.5rem; }
.db-edit-title { font-size: 0.8125rem; font-weight: 600; color: #6d28d9; }
:root.dark .db-edit-title { color: #c4b5fd; }
.db-edit-flag { font-size: 0.6875rem; color: #9ca3af; }
.db-edit-actions { margin-left: auto; display: flex; align-items: center; gap: 0.25rem; }
.db-btn { display: inline-flex; align-items: center; justify-content: center; width: 1.75rem; height: 1.75rem; border-radius: 0.375rem; border: 1px solid #e5e7eb; background: #fff; cursor: pointer; transition: background-color 0.15s; }
:root.dark .db-btn { background: #1f2937; border-color: #374151; }
.db-btn:hover:not(:disabled) { background: #f5f3ff; }
:root.dark .db-btn:hover:not(:disabled) { background: rgba(124, 58, 237, 0.15); }
.db-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.db-icon { width: 1rem; height: 1rem; color: #6b7280; }
:root.dark .db-icon { color: #9ca3af; }
/* 编辑模式下内容仅供预览,屏蔽交互,避免误点跳转 */
.db-edit-body { pointer-events: none; }
.db-edit-placeholder { padding: 1.25rem; text-align: center; font-size: 0.8125rem; color: #9ca3af; background: #f9fafb; border-radius: 0.5rem; }
:root.dark .db-edit-placeholder { background: rgba(255, 255, 255, 0.03); }
</style>
