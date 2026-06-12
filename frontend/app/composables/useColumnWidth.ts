import { clampWidth, parseStoredWidth, DEFAULT_MIN_WIDTH, DEFAULT_MAX_WIDTH } from '~/utils/columnWidth'

// 表格单列宽度:拖拽调整 + 按浏览器 localStorage 记忆(刷新保留)。
// width 为 null → 使用默认列宽(CSS auto);非 null → 像素值。

interface ColumnWidthOptions {
  min?: number
  max?: number
}

export function useColumnWidth(storageKey: string, options: ColumnWidthOptions = {}) {
  const min = options.min ?? DEFAULT_MIN_WIDTH
  const max = options.max ?? DEFAULT_MAX_WIDTH
  const width = ref<number | null>(null)

  // 从 localStorage 恢复(仅客户端)。
  function load() {
    if (typeof localStorage === 'undefined') return
    width.value = parseStoredWidth(localStorage.getItem(storageKey), min, max)
  }

  function persist() {
    if (typeof localStorage === 'undefined') return
    if (width.value === null) localStorage.removeItem(storageKey)
    else localStorage.setItem(storageKey, String(width.value))
  }

  // 在表头手柄上按下指针后开始拖拽;startPx = 当前列的实际像素宽。
  // 拖拽过程实时更新 width,松手时落盘一次。
  function startResize(event: PointerEvent, startPx: number) {
    event.preventDefault()
    event.stopPropagation()
    const startX = event.clientX

    const onMove = (e: PointerEvent) => {
      width.value = clampWidth(startPx + (e.clientX - startX), min, max)
    }
    const onUp = () => {
      document.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerup', onUp)
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
      persist()
    }
    document.addEventListener('pointermove', onMove)
    document.addEventListener('pointerup', onUp)
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
  }

  // 复原为默认列宽。
  function reset() {
    width.value = null
    persist()
  }

  return { width, load, startResize, reset }
}
