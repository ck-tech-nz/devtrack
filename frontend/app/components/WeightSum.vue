<template>
  <div class="mt-3 text-xs" :class="isValid ? 'text-emerald-500' : 'text-red-500'">
    权重合计: {{ total.toFixed(2) }}
    <span v-if="!isValid">（应为 1.0）</span>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ weights: Record<string, number> }>()

const total = computed(() =>
  Object.values(props.weights).reduce((sum, v) => sum + (Number(v) || 0), 0)
)
const isValid = computed(() => Math.abs(total.value - 1.0) < 0.01)
</script>
