export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/' || to.path === '/login') return
  if (to.path === '/app/forbidden') return

  const { getToken } = useApi()
  if (!getToken()) {
    return navigateTo('/')
  }

  const { user, fetchMe, can } = useAuth()
  const { loaded, fetchRoutes, routePermissions, error } = usePagePerms()

  if (!user.value) {
    await fetchMe()
  }

  if (!user.value) {
    return navigateTo('/')
  }

  if (!loaded.value) {
    await fetchRoutes()
  }

  if (error.value && to.path.startsWith('/app/')) {
    return navigateTo('/app/forbidden')
  }

  const perms = routePermissions.value
  for (const [prefix, perm] of Object.entries(perms)) {
    if (to.path === prefix || to.path.startsWith(prefix + '/')) {
      if (!can(perm)) {
        return navigateTo('/app/forbidden')
      }
      break
    }
  }
})
