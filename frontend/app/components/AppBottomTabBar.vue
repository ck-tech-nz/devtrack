<template>
  <div class="fixed bottom-0 left-0 right-0 z-40 md:hidden flex justify-center items-end gap-2 px-2" style="padding-bottom: env(safe-area-inset-bottom)">
    <ClientOnly>
      <LiquidGlassBottomNavBar
        v-model="selectedTabId"
        :items="tabItems"
        size="medium"
        :always-show-glass="false"
        :specular-opacity="0.4"
        :specular-saturation="10"
        :base-refraction="-0.4"
        color="#7c3aed"
        class="mb-1.5"
      />
    </ClientOnly>
    <!-- Separate "更多" button outside liquid glass to avoid touch leaking -->
    <button
      class="mb-1.5 flex-shrink-0 flex flex-col items-center justify-center rounded-full
             w-[58px] h-[58px] transition-colors
             bg-gray-100/80 dark:bg-gray-800/80 backdrop-blur-md
             border border-gray-200/50 dark:border-gray-700/50
             text-gray-500 dark:text-gray-400
             active:bg-gray-200/80 dark:active:bg-gray-700/80"
      :class="moreOpen ? 'text-crystal-600 dark:text-crystal-400' : ''"
      @click="moreOpen = true"
    >
      <UIcon name="i-heroicons-ellipsis-horizontal" class="w-5 h-5" />
      <span class="text-[10px] leading-tight mt-0.5">更多</span>
    </button>
    <MobileMoreSheet v-model:open="moreOpen" :items="moreNavItems" />
  </div>
</template>

<script setup lang="ts">
import LiquidGlassBottomNavBar from '~/components/liquid-glass/LiquidGlassBottomNavBar.vue'
import type { NavItem } from '~/composables/useNavigation'

const router = useRouter()
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

const moreNavItems = computed(() =>
  filteredNavItems.value.filter(item => item.to && !primaryRoutes.includes(item.to))
)

// Only real navigation tabs — no "更多"
const tabItems = computed(() =>
  primaryTabs.value.map(tab => ({
    id: tab.to!,
    label: tab.label,
  }))
)

const moreOpen = ref(false)

const currentRealTab = computed(() => {
  const match = primaryTabs.value.find(t => t.to && (currentPath.value === t.to || currentPath.value.startsWith(t.to + '/')))
  return match?.to || primaryRoutes[0]
})

const selectedTabId = computed({
  get: () => currentRealTab.value,
  set: (id: string) => {
    router.push(id)
  },
})
</script>
