<template>
  <div v-if="tasks.length" class="mb-6">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-sm font-medium text-gray-500 dark:text-gray-400">
        我的待办
        <span class="ml-1.5 text-xs bg-crystal-50 dark:bg-crystal-950 text-crystal-600 dark:text-crystal-400 px-1.5 py-0.5 rounded-full">{{ tasks.length }}</span>
      </h2>
      <button
        class="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        @click="collapsed = !collapsed"
      >
        {{ collapsed ? '展开' : '收起' }}
      </button>
    </div>
    <transition name="slide">
      <div v-show="!collapsed" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        <NuxtLink
          v-for="task in tasks"
          :key="task.id"
          :to="`/app/issues/${task.id}`"
          class="group bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-lg p-3.5 hover:border-crystal-200 dark:hover:border-crystal-800 hover:shadow-sm transition-all"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-400 dark:text-gray-500 font-mono">#{{ task.id }}</span>
            <UBadge
              :color="task.priority === 'P0' ? 'error' : task.priority === 'P1' ? 'warning' : 'neutral'"
              variant="subtle"
              size="xs"
            >
              {{ task.priority }}
            </UBadge>
          </div>
          <p class="text-sm text-gray-900 dark:text-gray-100 font-medium line-clamp-2 group-hover:text-crystal-600 dark:group-hover:text-crystal-400 transition-colors">
            {{ task.title }}
          </p>
          <div class="flex items-center justify-between mt-2.5">
            <UBadge
              :color="task.status === '待处理' ? 'warning' : 'info'"
              variant="subtle"
              size="xs"
            >
              {{ task.status }}
            </UBadge>
            <span v-if="task.project_name" class="text-[11px] text-gray-400 dark:text-gray-500 truncate ml-2">{{ task.project_name }}</span>
          </div>
        </NuxtLink>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
const { api } = useApi()
const { user } = useAuth()

const tasks = ref<any[]>([])
const collapsed = ref(false)

onMounted(async () => {
  if (!user.value) return
  try {
    const uid = user.value.id
    const [ap, ai, hp, hi] = await Promise.all([
      api<any>(`/api/issues/?assignee=${uid}&status=待处理&page_size=8`),
      api<any>(`/api/issues/?assignee=${uid}&status=进行中&page_size=8`),
      api<any>(`/api/issues/?helpers=${uid}&status=待处理&page_size=8`),
      api<any>(`/api/issues/?helpers=${uid}&status=进行中&page_size=8`),
    ])
    const seen = new Set<number>()
    const merged: any[] = []
    for (const item of [
      ...(ap.results || ap || []),
      ...(ai.results || ai || []),
      ...(hp.results || hp || []),
      ...(hi.results || hi || []),
    ]) {
      if (!seen.has(item.id)) { seen.add(item.id); merged.push(item) }
    }
    tasks.value = merged.slice(0, 8)
  } catch (e) {
    console.error('Failed to load pending tasks:', e)
  }
})
</script>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}
.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
