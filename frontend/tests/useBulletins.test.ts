// @vitest-environment nuxt
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useBulletins } from '../app/composables/useBulletins'

// useApi/useAuth 是 useBulletins 内部的自动导入,这里替换成可控 mock。
// userBox 是一个 { value } 盒子,模拟 useAuth 返回的 user Ref;composable
// 只读 authUser.value,共享引用即可。
const { apiMock, userBox } = vi.hoisted(() => ({
  apiMock: vi.fn(),
  userBox: { value: { id: 'u1' } as { id: string } | null },
}))

mockNuxtImport('useApi', () => () => ({ api: apiMock }))
mockNuxtImport('useAuth', () => () => ({ user: userBox }))

// 挂载一个最小宿主组件来驱动 useBulletins 的 onMounted/onUnmounted 生命周期。
const Harness = defineComponent({
  setup() {
    return useBulletins()
  },
  render: () => h('div'),
})

function bulletin(over: Partial<{ id: number; category: string; content: string }>) {
  return { id: 1, category: 'quote', content: 'x', source: '', link_url: '', ...over }
}

beforeEach(() => {
  apiMock.mockReset()
  userBox.value = { id: 'u1' }
})

describe('useBulletins', () => {
  it('fetches on mount and splits announcements vs rotating by category', async () => {
    apiMock.mockResolvedValue([
      bulletin({ id: 1, category: 'announcement', content: 'A' }),
      bulletin({ id: 2, category: 'quote', content: 'Q' }),
      bulletin({ id: 3, category: 'pitfall', content: 'P' }),
    ])
    const w = await mountSuspended(Harness)
    await flushPromises()
    expect((w.vm.announcements as any[]).map(b => b.content)).toEqual(['A'])
    expect((w.vm.rotating as any[]).map(b => b.content)).toEqual(['Q', 'P'])
    w.unmount()
  })

  it('coerces a non-array response to an empty list', async () => {
    apiMock.mockResolvedValue({ results: [] } as any)
    const w = await mountSuspended(Harness)
    await flushPromises()
    expect(w.vm.announcements as any[]).toEqual([])
    expect(w.vm.rotating as any[]).toEqual([])
    w.unmount()
  })

  it('keeps the last data when a refresh fails (silent failure)', async () => {
    apiMock.mockResolvedValueOnce([bulletin({ id: 1, category: 'quote', content: 'keep' })])
    const w = await mountSuspended(Harness)
    await flushPromises()
    expect((w.vm.rotating as any[]).map(b => b.content)).toEqual(['keep'])

    apiMock.mockRejectedValueOnce(new Error('boom'))
    await (w.vm.refresh as () => Promise<void>)()
    await flushPromises()
    expect((w.vm.rotating as any[]).map(b => b.content)).toEqual(['keep'])
    w.unmount()
  })

  it('does not call the API when there is no authenticated user', async () => {
    userBox.value = null
    const w = await mountSuspended(Harness)
    await flushPromises()
    expect(apiMock).not.toHaveBeenCalled()
    w.unmount()
  })
})
