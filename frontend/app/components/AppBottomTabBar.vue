<template>
  <div class="fixed bottom-0 left-0 right-0 z-40 md:hidden px-2" style="padding-bottom: env(safe-area-inset-bottom)">
    <ClientOnly>
      <LiquidGlass
        class="mb-1.5"
        :blur-amount="16"
        :corner-radius="20"
        :displacement-scale="30"
        :saturation="1.2"
        :elasticity="0.35"
        :aberration-intensity="0"
        :over-light="false"
        padding="0px"
      >
        <div class="tab-bar-inner relative">
          <!-- Liquid pill indicator -->
          <div class="liquid-pill absolute rounded-xl" :style="pillStyle" />
          <div class="flex items-center justify-around h-[52px] relative z-10">
            <NuxtLink
              v-for="(tab, index) in primaryTabs"
              :key="tab.to"
              :to="tab.to!"
              class="tab-item flex flex-col items-center justify-center min-w-[64px] h-[44px] gap-0.5 transition-colors duration-300"
              :class="isActive(tab.to!) ? 'text-crystal-600 dark:text-crystal-400' : 'text-gray-400 dark:text-gray-500'"
            >
              <UIcon :name="tab.icon" class="w-6 h-6 transition-transform duration-300" :class="isActive(tab.to!) ? 'scale-110' : ''" />
              <span class="text-[10px] leading-tight font-medium">{{ tab.label }}</span>
            </NuxtLink>
            <button
              class="tab-item flex flex-col items-center justify-center min-w-[64px] h-[44px] gap-0.5 transition-colors duration-300"
              :class="moreOpen ? 'text-crystal-600 dark:text-crystal-400' : 'text-gray-400 dark:text-gray-500'"
              @click="($event.currentTarget as HTMLElement)?.blur(); moreOpen = true"
            >
              <UIcon name="i-heroicons-ellipsis-horizontal" class="w-6 h-6 transition-transform duration-300" :class="moreOpen ? 'scale-110' : ''" />
              <span class="text-[10px] leading-tight font-medium">更多</span>
            </button>
          </div>
        </div>
      </LiquidGlass>
    </ClientOnly>
    <MobileMoreSheet v-model:open="moreOpen" :items="moreItems" />
  </div>
</template>

<script setup lang="ts">
import { LiquidGlass } from '@wxperia/liquid-glass-vue'
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

// Total tab count = primary tabs + more button
const tabCount = computed(() => primaryTabs.value.length + 1)

// Active tab index for pill positioning
const activeIndex = computed(() => {
  if (moreOpen.value) return primaryTabs.value.length
  const idx = primaryTabs.value.findIndex(t => t.to && isActive(t.to))
  return idx >= 0 ? idx : 0
})

// Sliding pill position
const pillStyle = computed(() => {
  const count = tabCount.value
  if (count === 0) return {}
  const widthPercent = 100 / count
  return {
    width: `calc(${widthPercent}% - 8px)`,
    height: '40px',
    top: '6px',
    left: `calc(${activeIndex.value * widthPercent}% + 4px)`,
    transition: 'left 0.4s cubic-bezier(0.4, 0, 0.2, 1), width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  }
})
</script>

<style scoped>
.tab-bar-inner {
  min-height: 52px;
}

.liquid-pill {
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 0.5px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    0 1px 4px rgba(0, 0, 0, 0.06),
    inset 0 0.5px 0 rgba(255, 255, 255, 0.6);
}
:root.dark .liquid-pill {
  background: rgba(255, 255, 255, 0.08);
  border: 0.5px solid rgba(255, 255, 255, 0.12);
  box-shadow:
    0 1px 4px rgba(0, 0, 0, 0.15),
    inset 0 0.5px 0 rgba(255, 255, 255, 0.08);
}

.tab-item {
  -webkit-tap-highlight-color: transparent;
}
</style>
