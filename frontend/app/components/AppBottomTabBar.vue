<template>
  <div class="fixed bottom-0 left-0 right-0 z-40 md:hidden flex justify-center" style="padding-bottom: env(safe-area-inset-bottom)">
    <ClientOnly>
      <LiquidGlassBottomNavBar
        v-model="activeTabId"
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

// Map nav items to LiquidGlassBottomNavBar format
const tabItems = computed(() => [
  ...primaryTabs.value.map(tab => ({
    id: tab.to!,
    label: tab.label,
  })),
  { id: '_more', label: '更多' },
])

// Track active tab
const moreOpen = ref(false)

const activeTabId = computed({
  get: () => {
    if (moreOpen.value) return '_more'
    const match = primaryTabs.value.find(t => t.to && (currentPath.value === t.to || currentPath.value.startsWith(t.to + '/')))
    return match?.to || primaryRoutes[0]
  },
  set: (id: string) => {
    if (id === '_more') {
      moreOpen.value = true
    } else {
      moreOpen.value = false
      router.push(id)
    }
  },
})
</script>
