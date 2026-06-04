// 相对时间格式化(中文),Mentions / Activity 共用。
export function timeAgo(isoDate: string): string {
  const then = new Date(isoDate)
  if (Number.isNaN(then.getTime())) return '' // 防御无效/缺失时间戳,避免 "NaN 天前"
  const diffMs = Date.now() - then.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay} 天前`
}
