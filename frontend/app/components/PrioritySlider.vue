<template>
  <div class="flex flex-col gap-0.5 w-32 select-none" title="按优先级筛选">
    <input
      type="range"
      min="0"
      max="4"
      step="1"
      :value="index"
      class="priority-range"
      aria-label="优先级筛选"
      @input="onInput"
    >
    <div class="flex justify-between text-[10px] leading-none text-gray-400">
      <span
        v-for="(s, i) in STOPS"
        :key="s.value || 'all'"
        :class="i === index ? 'text-crystal-600 dark:text-crystal-300 font-medium' : ''"
      >{{ s.short }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

// 低→紧急排列;'' 表示「全部」(不筛选)
const STOPS = [
  { value: '',   short: '全部' },
  { value: 'P3', short: '低' },
  { value: 'P2', short: '中' },
  { value: 'P1', short: '高' },
  { value: 'P0', short: '紧急' },
]

const index = computed(() => {
  const i = STOPS.findIndex(s => s.value === props.modelValue)
  return i === -1 ? 0 : i
})

function onInput(e: Event) {
  const i = Number((e.target as HTMLInputElement).value)
  emit('update:modelValue', STOPS[i]?.value ?? '')
}
</script>

<style scoped>
.priority-range {
  width: 100%;
  accent-color: var(--color-crystal-500);
  cursor: pointer;
}
</style>
