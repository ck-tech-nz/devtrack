export default defineNuxtRouteMiddleware((to) => {
  if (to.path === '/' || to.path === '/login') return

  const { getToken } = useApi()
  if (!getToken()) {
    return navigateTo('/')
  }
})
