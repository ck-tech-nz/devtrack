interface AuthUser {
  id: string
  name: string
  email: string
  avatar: string
  groups: string[]
  permissions: string[]
}

export function useAuth() {
  const user = useState<AuthUser | null>('auth_user', () => null)
  const { api, clearTokens } = useApi()

  async function fetchMe() {
    try {
      user.value = await api<AuthUser>('/api/auth/me/')
    } catch {
      user.value = null
    }
  }

  function can(permission: string): boolean {
    return user.value?.permissions.includes(permission) ?? false
  }

  function hasGroup(groupName: string): boolean {
    return user.value?.groups.includes(groupName) ?? false
  }

  function logout() {
    clearTokens()
    user.value = null
    navigateTo('/')
  }

  return { user, fetchMe, can, hasGroup, logout }
}
