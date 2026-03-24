<template>
  <UDrawer
    :open="open"
    title="更多"
    description="导航菜单"
    :ui="{
      content: 'bg-white/80 dark:bg-slate-900/80 backdrop-blur-[20px] backdrop-saturate-[180%]',
      overlay: 'bg-black/30',
      title: 'sr-only',
      description: 'sr-only',
    }"
    @update:open="$emit('update:open', $event)"
  >
    <template #content>
      <div class="px-4 pb-2">
        <nav class="space-y-1">
          <NuxtLink
            v-for="item in items"
            :key="item.to"
            :to="item.to!"
            class="flex items-center h-12 px-3 rounded-xl transition-colors"
            :class="currentPath === item.to || (item.to && currentPath.startsWith(item.to + '/'))
              ? 'bg-crystal-50 dark:bg-crystal-950 text-crystal-600 dark:text-crystal-400'
              : 'text-gray-600 dark:text-gray-300 active:bg-gray-100 dark:active:bg-gray-800'"
            @click="$emit('update:open', false)"
          >
            <UIcon :name="item.icon" class="w-5 h-5 mr-3" />
            <span class="text-sm font-medium">{{ item.label }}</span>
          </NuxtLink>
        </nav>
      </div>
      <div style="height: env(safe-area-inset-bottom)" />
    </template>
  </UDrawer>
</template>

<script setup lang="ts">
import type { NavItem } from '~/composables/useNavigation'

defineProps<{
  open: boolean
  items: NavItem[]
}>()
defineEmits<{
  'update:open': [value: boolean]
}>()

const { currentPath } = useNavigation()
</script>
