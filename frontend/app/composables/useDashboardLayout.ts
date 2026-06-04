import {
  DASHBOARD_BLOCKS,
  defaultLayout,
  mergeLayout,
  moveBlock,
  toggleBlock,
  type LayoutEntry,
} from '~/utils/dashboardLayout'

export function useDashboardLayout() {
  const { settings, update } = useUserSettings()
  // 编辑模式开关:仅运行时,不持久化;useState 保证 home 与各 Block 共享同一实例
  const editing = useState<boolean>('dashboard_editing', () => false)

  // 合并后的有序区块(含 title),随 settings 变化
  const orderedBlocks = computed(() =>
    mergeLayout(settings.value.dashboard_layout).map((entry) => {
      const meta = DASHBOARD_BLOCKS.find(b => b.id === entry.id)!
      return { id: entry.id, visible: entry.visible, title: meta.title }
    }),
  )

  function current(): LayoutEntry[] {
    return mergeLayout(settings.value.dashboard_layout)
  }
  function persist(next: LayoutEntry[]) {
    update('dashboard_layout', next)
  }

  function moveUp(id: string) {
    persist(moveBlock(current(), id, -1))
  }
  function moveDown(id: string) {
    persist(moveBlock(current(), id, 1))
  }
  function toggleVisible(id: string) {
    persist(toggleBlock(current(), id))
  }
  function reset() {
    persist(defaultLayout())
  }

  return { orderedBlocks, editing, moveUp, moveDown, toggleVisible, reset }
}
