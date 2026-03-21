<script setup lang="ts">
const props = defineProps<{
  items: string[]
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const leftFilter = ref('')
const rightFilter = ref('')
const leftHighlighted = ref<Set<string>>(new Set())
const rightHighlighted = ref<Set<string>>(new Set())
const leftLastClicked = ref<number>(-1)
const rightLastClicked = ref<number>(-1)

const selectedSet = computed(() => new Set(props.modelValue))

const availableItems = computed(() =>
  props.items.filter(i => !selectedSet.value.has(i)).sort()
)

const selectedItems = computed(() =>
  [...props.modelValue].sort()
)

const filteredAvailable = computed(() => {
  if (!leftFilter.value) return availableItems.value
  const q = leftFilter.value.toLowerCase()
  return availableItems.value.filter(i => i.toLowerCase().includes(q))
})

const filteredSelected = computed(() => {
  if (!rightFilter.value) return selectedItems.value
  const q = rightFilter.value.toLowerCase()
  return selectedItems.value.filter(i => i.toLowerCase().includes(q))
})

watch(leftFilter, () => { leftHighlighted.value.clear(); leftLastClicked.value = -1 })
watch(rightFilter, () => { rightHighlighted.value.clear(); rightLastClicked.value = -1 })

function handleItemClick(side: 'left' | 'right', item: string, index: number, event: MouseEvent) {
  const highlighted = side === 'left' ? leftHighlighted : rightHighlighted
  const lastClicked = side === 'left' ? leftLastClicked : rightLastClicked
  const list = side === 'left' ? filteredAvailable.value : filteredSelected.value

  if (event.shiftKey && lastClicked.value >= 0) {
    const start = Math.min(lastClicked.value, index)
    const end = Math.max(lastClicked.value, index)
    const range = list.slice(start, end + 1)
    if (event.metaKey || event.ctrlKey) {
      range.forEach(i => highlighted.value.add(i))
    } else {
      highlighted.value = new Set(range)
    }
  } else if (event.metaKey || event.ctrlKey) {
    if (highlighted.value.has(item)) {
      highlighted.value.delete(item)
    } else {
      highlighted.value.add(item)
    }
  } else {
    highlighted.value = new Set([item])
  }
  lastClicked.value = index
}

function transferItems(direction: 'left' | 'right', items: string[]) {
  if (items.length === 0) return
  const current = new Set(props.modelValue)
  if (direction === 'right') {
    items.forEach(i => current.add(i))
    leftHighlighted.value.clear()
    leftLastClicked.value = -1
  } else {
    items.forEach(i => current.delete(i))
    rightHighlighted.value.clear()
    rightLastClicked.value = -1
  }
  emit('update:modelValue', [...current])
}
</script>

<template>
  <div class="flex items-start gap-2">
    <!-- Left Panel: Available -->
    <div class="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
      <div class="bg-gray-100 dark:bg-gray-800 px-3 py-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300">
        可用权限
      </div>
      <div class="p-2">
        <input
          v-model="leftFilter"
          type="text"
          placeholder="过滤..."
          class="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded
                 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100
                 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div class="h-[250px] overflow-y-auto border-t border-gray-200 dark:border-gray-700">
        <div
          v-for="(item, index) in filteredAvailable"
          :key="item"
          class="px-3 py-1 text-xs font-mono cursor-pointer select-none"
          :class="leftHighlighted.has(item)
            ? 'bg-blue-600 text-white'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
          @click="handleItemClick('left', item, index, $event)"
          @dblclick="transferItems('right', [item])"
        >
          {{ item }}
        </div>
        <div v-if="leftFilter && filteredAvailable.length === 0" class="px-3 py-4 text-xs text-gray-400 text-center">
          无匹配项
        </div>
      </div>
      <div class="border-t border-gray-200 dark:border-gray-700 px-3 py-1.5">
        <button
          class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          @click="transferItems('right', filteredAvailable)"
        >
          全部选择 {{ filteredAvailable.length }} ⇨
        </button>
      </div>
    </div>

    <!-- Center Arrows -->
    <div class="flex flex-col items-center justify-center gap-2 pt-20">
      <button
        class="p-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100
               dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
        title="添加选中项"
        @click="transferItems('right', [...leftHighlighted])"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
      <button
        class="p-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100
               dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
        title="移除选中项"
        @click="transferItems('left', [...rightHighlighted])"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    </div>

    <!-- Right Panel: Selected -->
    <div class="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
      <div class="bg-gray-100 dark:bg-gray-800 px-3 py-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300">
        选中的权限
      </div>
      <div class="p-2">
        <input
          v-model="rightFilter"
          type="text"
          placeholder="过滤..."
          class="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded
                 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100
                 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div class="h-[250px] overflow-y-auto border-t border-gray-200 dark:border-gray-700">
        <div
          v-for="(item, index) in filteredSelected"
          :key="item"
          class="px-3 py-1 text-xs font-mono cursor-pointer select-none"
          :class="rightHighlighted.has(item)
            ? 'bg-blue-600 text-white'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
          @click="handleItemClick('right', item, index, $event)"
          @dblclick="transferItems('left', [item])"
        >
          {{ item }}
        </div>
        <div v-if="rightFilter && filteredSelected.length === 0" class="px-3 py-4 text-xs text-gray-400 text-center">
          无匹配项
        </div>
      </div>
      <div class="border-t border-gray-200 dark:border-gray-700 px-3 py-1.5">
        <button
          class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          @click="transferItems('left', filteredSelected)"
        >
          ⇦ 全部移除 {{ filteredSelected.length }}
        </button>
      </div>
    </div>
  </div>
</template>
