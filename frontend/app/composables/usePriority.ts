export const PRIORITY_ITEMS = [
  { value: 'P0', label: '紧急', color: 'error',   activeClass: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' },
  { value: 'P1', label: '高',   color: 'warning', activeClass: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' },
  { value: 'P2', label: '中',   color: 'warning', activeClass: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' },
  { value: 'P3', label: '低',   color: 'neutral', activeClass: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
] as const

export function priorityLabel(p: string): string {
  return PRIORITY_ITEMS.find(i => i.value === p)?.label ?? p
}

export function priorityColor(p: string): string {
  return PRIORITY_ITEMS.find(i => i.value === p)?.color ?? 'neutral'
}
