/**
 * Composable for native HTML drag-and-drop between columns.
 * Tracks which item is being dragged and which column is the current drop target.
 */
export function useDragDrop<T = number>() {
  const draggingId = ref<T | null>(null)
  const dragOverTarget = ref<string | null>(null)

  function onDragStart(id: T) {
    draggingId.value = id as any
  }

  function onDragEnd() {
    draggingId.value = null
    dragOverTarget.value = null
  }

  function onDragOver(target: string) {
    dragOverTarget.value = target
  }

  function onDragLeave() {
    dragOverTarget.value = null
  }

  return {
    draggingId: readonly(draggingId),
    dragOverTarget: readonly(dragOverTarget),
    onDragStart,
    onDragEnd,
    onDragOver,
    onDragLeave,
  }
}
