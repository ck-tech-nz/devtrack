<template>
  <div
    v-if="visible && items.length > 0"
    class="absolute z-50 w-64 max-h-48 overflow-y-auto bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg"
    :style="{ top: `${position.top}px`, left: `${position.left}px` }"
  >
    <button
      v-for="(item, idx) in items"
      :key="item.id"
      class="w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2"
      :class="idx === selectedIndex
        ? 'bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300'
        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
      @mousedown.prevent="selectItem(idx)"
    >
      <template v-if="type === 'user'">
        <UIcon name="i-heroicons-user-circle" class="w-4 h-4 text-gray-400 flex-shrink-0" />
        <span class="truncate">{{ item.label }}</span>
      </template>
      <template v-else>
        <span class="text-xs font-mono text-gray-400 flex-shrink-0">{{ item.prefix }}</span>
        <span class="truncate">{{ item.label }}</span>
      </template>
    </button>
  </div>
</template>

<script setup lang="ts">
export interface MentionItem {
  id: number
  label: string
  prefix?: string
}

const props = defineProps<{
  visible: boolean
  items: MentionItem[]
  position: { top: number; left: number }
  type: 'user' | 'issue'
}>()

const emit = defineEmits<{
  select: [item: MentionItem]
}>()

const selectedIndex = ref(0)

watch(() => props.items, () => {
  selectedIndex.value = 0
})

function selectItem(idx: number) {
  emit('select', props.items[idx])
}

function moveUp() {
  selectedIndex.value = Math.max(0, selectedIndex.value - 1)
}

function moveDown() {
  selectedIndex.value = Math.min(props.items.length - 1, selectedIndex.value + 1)
}

function confirmSelection() {
  if (props.items.length > 0) {
    emit('select', props.items[selectedIndex.value])
  }
}

defineExpose({ moveUp, moveDown, confirmSelection })
</script>
