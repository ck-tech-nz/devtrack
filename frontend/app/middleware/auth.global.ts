/**
 * Route-to-permission mapping.
 * Keys are route prefixes; the first match wins.
 * Routes without a mapping are accessible to all authenticated users.
 */
const routePermissions: Record<string, string> = {
  '/app/dashboard': 'issues.view_dashboard',
  '/app/issues': 'issues.view_issue',
  '/app/projects': 'projects.view_project',
  '/app/repos': 'repos.view_repo',
}

function getRequiredPermission(path: string): string | undefined {
  for (const [prefix, perm] of Object.entries(routePermissions)) {
    if (path === prefix || path.startsWith(prefix + '/')) {
      return perm
    }
  }
  return undefined
}

export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/' || to.path === '/login') return
  if (to.path === '/app/forbidden') return

  const { getToken } = useApi()
  if (!getToken()) {
    return navigateTo('/')
  }

  const { user, fetchMe, can } = useAuth()

  // Ensure user data (including permissions) is loaded
  if (!user.value) {
    await fetchMe()
  }

  // If fetchMe failed (e.g. token expired), redirect to login
  if (!user.value) {
    return navigateTo('/')
  }

  const required = getRequiredPermission(to.path)
  if (required && !can(required)) {
    return navigateTo('/app/forbidden')
  }
})
