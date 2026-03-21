<template>
  <div class="editable-cell" @dblclick="startEdit">
    <template v-if="editing">
      <input
        ref="inputRef"
        v-model="editValue"
        class="editable-input"
        @keydown.enter="save"
        @keydown.escape="cancel"
        @blur="save"
      />
    </template>
    <template v-else>
      <span class="cell-text" :class="{ 'text-gray-300': !value }" :title="value || ''">
        {{ value || '-' }}
      </span>
    </template>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ value?: string | null }>()
const emit = defineEmits<{ save: [value: string] }>()

const editing = ref(false)
const editValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

function startEdit() {
  editing.value = true
  editValue.value = props.value || ''
  nextTick(() => inputRef.value?.focus())
}

function save() {
  if (!editing.value) return
  editing.value = false
  if (editValue.value !== (props.value || '')) {
    emit('save', editValue.value)
  }
}

function cancel() {
  editing.value = false
}
</script>

<style scoped>
.editable-cell {
  cursor: default;
  min-height: 1.5rem;
}
.cell-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 10rem;
}
.editable-input {
  width: 100%;
  padding: 0.125rem 0.375rem;
  font-size: 0.8125rem;
  border: 1px solid #8b5cf6;
  border-radius: 0.25rem;
  outline: none;
  background: white;
}
:root.dark .editable-input {
  background: #1f2937;
  color: #e5e7eb;
  border-color: #7c3aed;
}
</style>
