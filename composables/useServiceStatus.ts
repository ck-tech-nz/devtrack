interface ServiceState {
  online: boolean
  label: string
}

const state = reactive<Record<string, ServiceState>>({
  github: { online: true, label: 'GitHub' },
  ai: { online: true, label: 'AI 服务' },
})

export const useServiceStatus = () => {
  const isOnline = (key: string) => state[key]?.online ?? false
  const getLabel = (key: string) => state[key]?.label ?? key
  const toggle = (key: string) => {
    if (state[key]) state[key].online = !state[key].online
  }

  return { state, isOnline, getLabel, toggle }
}
