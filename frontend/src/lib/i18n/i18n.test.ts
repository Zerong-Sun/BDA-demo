import { describe, expect, it } from 'vitest'
import { en } from './en'
import { zh } from './zh'

function keys(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null) return [prefix]
  return Object.entries(value).flatMap(([key, nested]) => keys(nested, prefix ? `${prefix}.${key}` : key))
}

describe('i18n', () => {
  it('keeps en and zh key parity', () => {
    const enKeys = keys(en).sort()
    const zhKeys = keys(zh).sort()
    expect(zhKeys).toEqual(enKeys)
  })
})
