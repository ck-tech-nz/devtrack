// @vitest-environment nuxt
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { ref, computed } from 'vue'
import HeaderBulletinCarousel from '../app/components/HeaderBulletinCarousel.vue'

// 用可控盒子驱动 useBulletins 的两个分片;组件内部 watch(rotating) 会在挂载时
// 立即对 rotating 洗牌一次,所以断言用「集合成员」而非顺序。
const { annBox, rotBox } = vi.hoisted(() => ({
  annBox: { v: [] as any[] },
  rotBox: { v: [] as any[] },
}))

mockNuxtImport('useBulletins', () => () => ({
  announcements: computed(() => annBox.v),
  rotating: computed(() => rotBox.v),
  loading: ref(false),
  refresh: () => {},
}))

const stubs = { UIcon: { props: ['name'], template: '<i :data-icon="name"></i>' } }

function bulletin(over: Partial<{ id: number; category: string; content: string; link_url: string }>) {
  return { id: 1, category: 'quote', content: 'x', source: '', link_url: '', ...over }
}

beforeEach(() => {
  annBox.v = []
  rotBox.v = []
})

describe('HeaderBulletinCarousel', () => {
  it('renders nothing when there are no bulletins', async () => {
    const w = await mountSuspended(HeaderBulletinCarousel, { global: { stubs } })
    expect(w.text()).toBe('')
    w.unmount()
  })

  it('prioritises announcements over rotating content in the pool', async () => {
    annBox.v = [bulletin({ id: 1, category: 'announcement', content: '系统维护公告' })]
    rotBox.v = [bulletin({ id: 2, category: 'quote', content: '一条名言' })]
    const w = await mountSuspended(HeaderBulletinCarousel, { global: { stubs } })
    expect(w.text()).toContain('系统维护公告')
    expect(w.text()).not.toContain('一条名言')
    // announcement 用喇叭图标
    expect(w.find('[data-icon]').attributes('data-icon')).toBe('i-heroicons-megaphone')
    w.unmount()
  })

  it('falls back to rotating content when there are no announcements', async () => {
    rotBox.v = [bulletin({ id: 2, category: 'pitfall', content: '小心边界条件' })]
    const w = await mountSuspended(HeaderBulletinCarousel, { global: { stubs } })
    expect(w.text()).toContain('小心边界条件')
    expect(w.find('[data-icon]').attributes('data-icon')).toBe('i-heroicons-exclamation-triangle')
    w.unmount()
  })

  it('renders a link with safe rel/target when link_url is present', async () => {
    annBox.v = [bulletin({ id: 1, category: 'announcement', content: '点我', link_url: 'https://example.com' })]
    const w = await mountSuspended(HeaderBulletinCarousel, { global: { stubs } })
    const a = w.find('a')
    expect(a.exists()).toBe(true)
    expect(a.attributes('href')).toBe('https://example.com')
    expect(a.attributes('target')).toBe('_blank')
    expect(a.attributes('rel')).toBe('noopener noreferrer')
    w.unmount()
  })

  it('renders a non-link element when link_url is empty', async () => {
    annBox.v = [bulletin({ id: 1, category: 'announcement', content: '纯文本', link_url: '' })]
    const w = await mountSuspended(HeaderBulletinCarousel, { global: { stubs } })
    expect(w.find('a').exists()).toBe(false)
    expect(w.text()).toContain('纯文本')
    w.unmount()
  })
})
