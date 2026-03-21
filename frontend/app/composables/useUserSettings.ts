interface UserSettings {
  sidebar_auto_collapse: boolean
  issues_view_mode: 'kanban' | 'table'
  project_view_mode: 'kanban' | 'table'
  theme: 'light' | 'dark' | 'auto'
}

const defaults: UserSettings = {
  sidebar_auto_collapse: false,
  issues_view_mode: 'table',
  project_view_mode: 'kanban',
  theme: 'light',
}

export function useUserSettings() {
  const settings = useState<UserSettings>('user_settings', () => ({ ...defaults }))
  const { api } = useApi()

  function load(raw: Record<string, any> | null | undefined) {
    settings.value = { ...defaults, ...(raw || {}) }
  }

  let saveTimer: ReturnType<typeof setTimeout> | null = null

  async function save() {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(async () => {
      try {
        await api('/api/auth/me/', {
          method: 'PATCH',
          body: { settings: settings.value },
        })
      } catch (e) {
        console.error('Failed to save user settings:', e)
      }
    }, 500)
  }

  function update<K extends keyof UserSettings>(key: K, value: UserSettings[K]) {
    settings.value = { ...settings.value, [key]: value }
    save()
  }

  return { settings, load, update }
}
