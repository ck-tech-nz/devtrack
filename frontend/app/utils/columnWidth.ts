// 列宽调整的纯逻辑(无 Vue / DOM 依赖),便于在 node 环境快速单测。

export const DEFAULT_MIN_WIDTH = 120
export const DEFAULT_MAX_WIDTH = 700

// 把像素值夹到 [min, max] 区间并取整。
export function clampWidth(px: number, min = DEFAULT_MIN_WIDTH, max = DEFAULT_MAX_WIDTH): number {
  return Math.max(min, Math.min(max, Math.round(px)))
}

// 解析 localStorage 里存的列宽:缺失 / 非法 → null(表示用默认列宽);
// 合法则夹到 [min, max]。
export function parseStoredWidth(
  raw: string | null,
  min = DEFAULT_MIN_WIDTH,
  max = DEFAULT_MAX_WIDTH,
): number | null {
  if (raw === null) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0) return null
  return clampWidth(n, min, max)
}
