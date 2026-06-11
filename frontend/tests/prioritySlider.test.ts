// @vitest-environment nuxt
import { describe, it, expect } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import PrioritySlider from '../app/components/PrioritySlider.vue'

// STOPS 顺序:'' / P3 / P2 / P1 / P0 → range index 0..4
describe('PrioritySlider', () => {
  it('maps modelValue to the range index (P0 → 4)', async () => {
    const w = await mountSuspended(PrioritySlider, { props: { modelValue: 'P0' } })
    expect((w.find('input[type="range"]').element as HTMLInputElement).value).toBe('4')
  })

  it("'' (全部) maps to index 0", async () => {
    const w = await mountSuspended(PrioritySlider, { props: { modelValue: '' } })
    expect((w.find('input[type="range"]').element as HTMLInputElement).value).toBe('0')
  })

  it('unknown value falls back to index 0', async () => {
    const w = await mountSuspended(PrioritySlider, { props: { modelValue: 'P9' } })
    expect((w.find('input[type="range"]').element as HTMLInputElement).value).toBe('0')
  })

  it('emits the mapped priority value on input (index 4 → P0)', async () => {
    const w = await mountSuspended(PrioritySlider, { props: { modelValue: '' } })
    const input = w.find('input[type="range"]')
    ;(input.element as HTMLInputElement).value = '4'
    await input.trigger('input')
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual(['P0'])
  })

  it('emits empty string when sliding back to 全部 (index 0)', async () => {
    const w = await mountSuspended(PrioritySlider, { props: { modelValue: 'P0' } })
    const input = w.find('input[type="range"]')
    ;(input.element as HTMLInputElement).value = '0'
    await input.trigger('input')
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([''])
  })

  it('renders all five tick labels in low→urgent order', async () => {
    const w = await mountSuspended(PrioritySlider, { props: { modelValue: '' } })
    const labels = w.findAll('span').map(s => s.text())
    expect(labels).toEqual(['全部', '低', '中', '高', '紧急'])
  })
})
