<template>
  <aside
    class="h-screen bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col transition-all duration-300 ease-in-out flex-shrink-0 relative z-30"
    :class="expanded ? 'w-60' : 'w-16'"
    @mouseenter="expanded = true"
    @mouseleave="autoCollapse && (expanded = false)"
  >
    <div class="h-16 flex items-center px-4 border-b border-gray-50 dark:border-gray-800">
      <img src="~/assets/images/logo-icon.svg" alt="DevTrakr" class="w-8 h-8 flex-shrink-0" />
      <transition name="fade">
        <span v-if="expanded" class="ml-3 font-semibold text-gray-900 dark:text-gray-100 whitespace-nowrap">DevTrakr</span>
      </transition>
    </div>

    <nav class="flex-1 overflow-y-auto py-4 space-y-1 px-2">
      <NuxtLink
        v-for="item in filteredNavItems"
        :key="item.label"
        :to="item.to!"
        class="flex items-center h-10 px-2 rounded-lg transition-colors group"
        :class="currentPath === item.to || (item.to && currentPath.startsWith(item.to + '/'))
          ? 'bg-crystal-50 dark:bg-crystal-950 text-crystal-600 dark:text-crystal-400'
          : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'"
      >
        <UIcon :name="item.icon" class="w-5 h-5 flex-shrink-0" />
        <transition name="fade">
          <span v-if="expanded" class="ml-3 text-sm font-medium whitespace-nowrap flex items-center gap-2">
            {{ item.label }}
            <ServiceStatusDot
              v-if="item.meta?.serviceKey"
              :online="isOnline(item.meta.serviceKey)"
            />
          </span>
        </transition>
      </NuxtLink>
    </nav>

    <div v-if="expanded" class="border-t border-gray-50 dark:border-gray-800 py-3 px-3 space-y-1">
      <p class="text-[10px] uppercase tracking-wider text-gray-300 dark:text-gray-600 mb-1">服务状态 (Demo)</p>
      <button
        v-for="key in ['github', 'ai']"
        :key="key"
        class="flex items-center justify-between w-full text-xs text-gray-400 hover:text-gray-600 py-1"
        @click="toggle(key)"
      >
        <span>{{ getLabel(key) }}</span>
        <ServiceStatusDot :online="isOnline(key)" />
      </button>
    </div>

    <div class="border-t border-gray-50 dark:border-gray-800 py-3 px-3">
      <button
        class="flex items-center w-full text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 py-1"
        :class="expanded ? 'justify-between' : 'justify-center'"
        @click="autoCollapse = !autoCollapse"
      >
        <transition name="fade">
          <span v-if="expanded" class="whitespace-nowrap">自动收起</span>
        </transition>
        <UIcon
          :name="autoCollapse ? 'i-heroicons-chevron-double-left' : 'i-heroicons-chevron-double-right'"
          class="w-4 h-4 flex-shrink-0"
        />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
const { filteredNavItems, currentPath } = useNavigation()
const { isOnline, toggle, getLabel } = useServiceStatus()
const { settings, update } = useUserSettings()
const expanded = ref(!settings.value.sidebar_auto_collapse)
const autoCollapse = computed({
  get: () => settings.value.sidebar_auto_collapse,
  set: (v: boolean) => update('sidebar_auto_collapse', v),
})
</script>

<style scoped>
.fade-enter-active { transition: opacity 0.2s ease 0.1s; }
.fade-leave-active { transition: opacity 0.1s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
