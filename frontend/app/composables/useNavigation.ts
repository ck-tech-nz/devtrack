export interface NavItem {
  label: string
  icon: string
  to?: string
  children?: NavItem[]
  serviceKey?: 'github' | 'ai'
  permission?: string
}

export const useNavigation = () => {
  const { can, user } = useAuth()

  const navItems: NavItem[] = [
    {
      label: '问题跟踪',
      icon: 'i-heroicons-bug-ant',
      to: '/app/issues',
      permission: 'issues.view_issue',
    },
    {
      label: '项目概览',
      icon: 'i-heroicons-squares-2x2',
      to: '/app/dashboard',
      permission: 'issues.view_dashboard',
    },
    {
      label: '项目管理',
      icon: 'i-heroicons-folder-open',
      to: '/app/projects',
      permission: 'projects.view_project',
    },
    {
      label: 'GitHub 仓库',
      icon: 'i-heroicons-code-bracket',
      to: '/app/repos',
      serviceKey: 'github',
      permission: 'repos.view_repo',
    },
    {
      label: 'AI 洞察',
      icon: 'i-heroicons-cpu-chip',
      to: '/app/ai-insights',
      serviceKey: 'ai',
    },
  ]

  const filteredNavItems = computed(() => {
    if (!user.value) return []
    return navItems.filter(item => !item.permission || can(item.permission))
  })

  const route = useRoute()
  const currentPath = computed(() => route.path)

  const breadcrumbs = computed(() => {
    const path = route.path
    const crumbs: { label: string; to?: string }[] = [{ label: '首页', to: '/app/dashboard' }]

    for (const item of navItems) {
      if (item.to === path) {
        crumbs.push({ label: item.label })
        return crumbs
      }
    }

    if (path.startsWith('/app/projects/')) {
      crumbs.push({ label: '项目管理', to: '/app/projects' })
      crumbs.push({ label: '项目详情' })
      return crumbs
    }
    if (path.startsWith('/app/issues/')) {
      crumbs.push({ label: '问题跟踪', to: '/app/issues' })
      crumbs.push({ label: 'Issue 详情' })
      return crumbs
    }
    if (path.startsWith('/app/repos/')) {
      crumbs.push({ label: 'GitHub 仓库', to: '/app/repos' })
      crumbs.push({ label: '仓库详情' })
      return crumbs
    }

    return crumbs
  })

  return { navItems, filteredNavItems, currentPath, breadcrumbs }
}
