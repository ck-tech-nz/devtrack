<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div
      v-for="col in columns"
      :key="col.status"
      class="bg-gray-50 rounded-xl p-4 transition-colors"
      :class="dragOverTarget === col.status ? 'ring-2 ring-crystal-300 bg-crystal-50' : ''"
      @dragover.prevent="onDragOver(col.status)"
      @dragleave="onDragLeave"
      @drop="onDrop(col.status)"
    >
      <div class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-semibold text-gray-700">{{ col.label }}</h4>
        <UBadge color="neutral" variant="subtle" size="xs">{{ col.items.length }}</UBadge>
      </div>
      <div class="space-y-2">
        <div
          v-for="issue in col.items"
          :key="issue.id"
          draggable="true"
          class="bg-white rounded-lg border border-gray-100 p-3 hover:shadow-sm transition-shadow cursor-grab active:cursor-grabbing"
          :class="draggingId === issue.id ? 'opacity-40' : ''"
          @dragstart="onDragStart(issue.id)"
          @dragend="onDragEnd"
        >
          <NuxtLink :to="`/app/issues/${issue.id}`" class="block">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs text-gray-400">#{{ issue.id }}</span>
              <UBadge
                :color="issue.priority === 'P0' ? 'error' : issue.priority === 'P1' ? 'warning' : issue.priority === 'P2' ? 'warning' : 'neutral'"
                variant="subtle"
                size="xs"
              >
                {{ issue.priority }}
              </UBadge>
            </div>
            <p class="text-sm text-gray-900 font-medium line-clamp-2">{{ issue.title }}</p>
            <div class="mt-2 flex items-center">
              <div class="w-5 h-5 rounded-full bg-crystal-100 flex items-center justify-center">
                <span class="text-crystal-600 text-[10px] font-medium">{{ (issue.assignee_name || '?').slice(0, 1) }}</span>
              </div>
              <span class="ml-1.5 text-xs text-gray-400">{{ issue.assignee_name || '-' }}</span>
            </div>
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  issues: any[]
}>()

const emit = defineEmits<{
  'update:status': [payload: { issueId: number, newStatus: string }]
}>()

const { draggingId, dragOverTarget, onDragStart, onDragEnd, onDragOver, onDragLeave } = useDragDrop<number>()

const columns = computed(() => [
  { status: '待处理', label: '待处理', items: props.issues.filter(i => i.status === '待处理') },
  { status: '进行中', label: '进行中', items: props.issues.filter(i => i.status === '进行中') },
  { status: '已解决', label: '已解决', items: props.issues.filter(i => i.status === '已解决') },
])

function onDrop(newStatus: string) {
  const issueId = draggingId.value
  if (issueId == null) return

  const issue = props.issues.find(i => i.id === issueId)
  if (issue && issue.status !== newStatus) {
    emit('update:status', { issueId, newStatus })
  }

  onDragEnd()
}
</script>
