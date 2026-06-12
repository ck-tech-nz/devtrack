import { describe, it, expect } from 'vitest'
import {
  DEFAULT_MIN_WIDTH,
  DEFAULT_MAX_WIDTH,
  clampWidth,
  parseStoredWidth,
} from '../app/utils/columnWidth'

describe('clampWidth', () => {
  it('keeps a value inside the range, rounded', () => {
    expect(clampWidth(300.6)).toBe(301)
  })
  it('clamps below min and above max', () => {
    expect(clampWidth(10)).toBe(DEFAULT_MIN_WIDTH)
    expect(clampWidth(9999)).toBe(DEFAULT_MAX_WIDTH)
  })
  it('honours custom bounds', () => {
    expect(clampWidth(50, 80, 200)).toBe(80)
    expect(clampWidth(500, 80, 200)).toBe(200)
    expect(clampWidth(150, 80, 200)).toBe(150)
  })
})

describe('parseStoredWidth', () => {
  it('returns null for a missing value', () => {
    expect(parseStoredWidth(null)).toBeNull()
  })
  it('returns null for non-numeric or non-positive input', () => {
    expect(parseStoredWidth('abc')).toBeNull()
    expect(parseStoredWidth('')).toBeNull()
    expect(parseStoredWidth('0')).toBeNull()
    expect(parseStoredWidth('-50')).toBeNull()
  })
  it('parses and clamps a stored pixel value', () => {
    expect(parseStoredWidth('300')).toBe(300)
    expect(parseStoredWidth('50')).toBe(DEFAULT_MIN_WIDTH)
    expect(parseStoredWidth('9999')).toBe(DEFAULT_MAX_WIDTH)
  })
  it('honours custom bounds', () => {
    expect(parseStoredWidth('500', 80, 200)).toBe(200)
  })
})
