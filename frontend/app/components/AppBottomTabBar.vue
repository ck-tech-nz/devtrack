<template>
  <div class="fixed bottom-0 left-0 right-0 z-40 md:hidden px-2" style="padding-bottom: env(safe-area-inset-bottom)">
    <nav class="glass-tab-bar mb-1.5 rounded-2xl">
      <div class="flex items-center justify-around h-[52px]">
      <NuxtLink
        v-for="tab in primaryTabs"
        :key="tab.to"
        :to="tab.to"
        class="flex flex-col items-center justify-center min-w-[64px] h-[44px] gap-0.5"
        :class="isActive(tab.to) ? 'text-crystal-600 dark:text-crystal-400' : 'text-gray-400 dark:text-gray-500'"
      >
        <div
          class="w-7 h-7 flex items-center justify-center rounded-lg transition-colors"
          :class="isActive(tab.to) ? 'bg-crystal-600/12' : ''"
        >
          <UIcon :name="tab.icon" class="w-6 h-6" />
        </div>
        <span class="text-[10px] leading-tight">{{ tab.label }}</span>
      </NuxtLink>

      <button
        class="flex flex-col items-center justify-center min-w-[64px] h-[44px] gap-0.5"
        :class="moreOpen ? 'text-crystal-600 dark:text-crystal-400' : 'text-gray-400 dark:text-gray-500'"
        @click="($event.currentTarget as HTMLElement)?.blur(); moreOpen = true"
      >
        <div
          class="w-7 h-7 flex items-center justify-center rounded-lg transition-colors"
          :class="moreOpen ? 'bg-crystal-600/12' : ''"
        >
          <UIcon name="i-heroicons-ellipsis-horizontal" class="w-6 h-6" />
        </div>
        <span class="text-[10px] leading-tight">更多</span>
      </button>
      </div>
    </nav>
    <MobileMoreSheet v-model:open="moreOpen" :items="moreItems" />
  </div>
</template>

<script setup lang="ts">
import type { NavItem } from '~/composables/useNavigation'

const { filteredNavItems, currentPath } = useNavigation()

const primaryRoutes = ['/app/issues', '/app/dashboard', '/app/repos']

const primaryTabs = computed(() => {
  const tabs: NavItem[] = []
  for (const route of primaryRoutes) {
    const item = filteredNavItems.value.find(i => i.to === route)
    if (item) tabs.push(item)
  }
  return tabs
})

const moreItems = computed(() =>
  filteredNavItems.value.filter(item => item.to && !primaryRoutes.includes(item.to))
)

const moreOpen = ref(false)

function isActive(to: string) {
  return currentPath.value === to || currentPath.value.startsWith(to + '/')
}
</script>

<style scoped>
.glass-tab-bar {
  background: rgba(245, 245, 247, 0.72);
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  border: 0.5px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    0 0 0 0.5px rgba(0, 0, 0, 0.06),
    0 2px 12px rgba(0, 0, 0, 0.08),
    inset 0 0.5px 0 rgba(255, 255, 255, 0.6);
}
:root.dark .glass-tab-bar {
  background: rgba(30, 30, 35, 0.65);
  border: 0.5px solid rgba(255, 255, 255, 0.1);
  box-shadow:
    0 0 0 0.5px rgba(0, 0, 0, 0.3),
    0 2px 12px rgba(0, 0, 0, 0.25),
    inset 0 0.5px 0 rgba(255, 255, 255, 0.08);
}
</style>
