<template>
  <div class="grid gap-4" :style="{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }">
    <div
      v-for="col in columns"
      :key="col.key"
      class="rounded-xl p-4 transition-colors"
      :class="[
        draggable && dragOverTarget === col.key ? 'ring-2 ring-crystal-300 dark:ring-crystal-700' : '',
        col.color ? '' : 'bg-gray-50 dark:bg-gray-800',
      ]"
      :style="col.color ? { backgroundColor: col.color + '12' } : {}"
      @dragover.prevent="draggable && onDragOver(col.key)"
      @dragleave="draggable && onDragLeave()"
      @drop="draggable && onDrop(col.key)"
    >
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <div v-if="col.color" class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: col.color }" />
          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{{ col.label }}</h4>
        </div>
        <UBadge color="neutral" variant="subtle" size="xs">{{ col.items.length }}</UBadge>
      </div>
      <div class="space-y-2">
        <div
          v-for="item in col.items"
          :key="itemKey(item)"
          :draggable="draggable"
          class="bg-white dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-800 p-3 hover:shadow-sm transition-shadow"
          :class="[
            draggable ? 'cursor-grab active:cursor-grabbing' : '',
            draggable && draggingId === itemKey(item) ? 'opacity-40' : '',
          ]"
          @dragstart="draggable && onDragStart(itemKey(item))"
          @dragend="draggable && onDragEnd()"
        >
          <slot name="card" :item="item" :column="col.key" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  columns: Array<{ key: string; label: string; items: any[]; color?: string }>
  itemKey?: (item: any) => string | number
  draggable?: boolean
}>(), {
  itemKey: (item: any) => item.id,
  draggable: true,
})

const emit = defineEmits<{
  drop: [payload: { itemId: string | number; fromColumn: string; toColumn: string }]
}>()

const { draggingId, dragOverTarget, onDragStart, onDragEnd, onDragOver, onDragLeave } = useDragDrop<string | number>()

function onDrop(toColumn: string) {
  const itemId = draggingId.value
  if (itemId == null) return

  const fromCol = props.columns.find(c => c.items.some(i => props.itemKey(i) === itemId))
  if (fromCol && fromCol.key !== toColumn) {
    emit('drop', { itemId, fromColumn: fromCol.key, toColumn })
  }
  onDragEnd()
}
</script>
