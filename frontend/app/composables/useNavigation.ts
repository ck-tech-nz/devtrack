export interface NavItem {
  label: string
  icon: string
  to?: string
  permission?: string
  meta?: Record<string, any>
}

export const useNavigation = () => {
  const { can, user } = useAuth()
  const { routes, loaded } = usePagePerms()

  const navItems = computed<NavItem[]>(() => {
    if (!loaded.value) return []
    return routes.value
      .filter(r => r.show_in_nav && r.is_active)
      .map(r => ({
        label: r.label,
        icon: r.icon,
        to: r.path,
        permission: r.permission ?? undefined,
        meta: r.meta,
      }))
  })

  const filteredNavItems = computed(() => {
    if (!user.value) return []
    return navItems.value.filter(item => {
      if (item.meta?.superuserOnly && !user.value?.is_superuser) return false
      if (item.permission && !can(item.permission)) return false
      return true
    })
  })

  const route = useRoute()
  const currentPath = computed(() => route.path)

  // 不在 navItems 中的独立页面
  const standalonePages: Record<string, string> = {
    '/app/profile': '个人资料',
    '/app/about': '关于系统',
  }

  const breadcrumbs = computed(() => {
    const path = route.path
    const crumbs: { label: string; to?: string }[] = [{ label: '首页', to: '/app/issues' }]

    // 独立页面直接返回页面标题，不显示"首页"面包屑
    const standaloneName = standalonePages[path]
    if (standaloneName) {
      return [{ label: standaloneName }]
    }

    for (const item of navItems.value) {
      if (item.to === path) {
        crumbs.push({ label: item.label })
        return crumbs
      }
    }

    for (const item of navItems.value) {
      if (item.to && path.startsWith(item.to + '/')) {
        crumbs.push({ label: item.label, to: item.to })
        crumbs.push({ label: '详情' })
        return crumbs
      }
    }

    return crumbs
  })

  return { navItems, filteredNavItems, currentPath, breadcrumbs }
}
