export const useMobile = () => {
  const isMobile = ref(false)

  if (import.meta.client) {
    const mql = window.matchMedia('(max-width: 767px)')
    isMobile.value = mql.matches
    const handler = (e: MediaQueryListEvent) => { isMobile.value = e.matches }
    mql.addEventListener('change', handler)
    onScopeDispose(() => mql.removeEventListener('change', handler))
  }

  return { isMobile }
}
