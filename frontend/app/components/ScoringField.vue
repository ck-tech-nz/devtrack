<template>
  <div>
    <label class="text-xs text-gray-500 dark:text-gray-400 mb-1 block">{{ label }}</label>
    <UInput
      type="number"
      size="sm"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', Number($event))"
      :step="step"
      :min="min"
      :max="max"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  modelValue: number
  step?: number
  min?: number
  max?: number
}>()
defineEmits<{
  'update:modelValue': [value: number]
}>()
</script>
