<template>
  <div class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-sm transition-shadow">
    <div class="flex items-center justify-between mb-3">
      <span class="text-sm text-gray-500">{{ label }}</span>
      <div class="w-9 h-9 rounded-lg flex items-center justify-center" :class="iconBg">
        <UIcon :name="icon" class="w-5 h-5" :class="iconColor" />
      </div>
    </div>
    <div class="text-2xl font-semibold text-gray-900 tracking-tight">{{ value }}</div>
    <div v-if="trend" class="mt-1.5 flex items-center text-xs" :class="trend > 0 ? 'text-emerald-500' : 'text-red-400'">
      <UIcon :name="trend > 0 ? 'i-heroicons-arrow-trending-up' : 'i-heroicons-arrow-trending-down'" class="w-3.5 h-3.5 mr-1" />
      {{ Math.abs(trend) }}% 较上月
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  icon: string
  iconBg?: string
  iconColor?: string
  trend?: number
}>()
</script>
