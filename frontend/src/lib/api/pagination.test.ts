import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { paginatedListSchema, unwrapPaginatedList } from './pagination'

const ItemSchema = z.object({ id: z.string() })

describe('pagination helpers', () => {
  it('unwraps paginated object responses', () => {
    const parsed = paginatedListSchema(ItemSchema).parse({
      items: [{ id: 'a' }],
      total: 1,
      limit: 50,
      offset: 0,
    })
    expect(unwrapPaginatedList(parsed)).toEqual([{ id: 'a' }])
  })

  it('unwraps legacy array responses', () => {
    const parsed = paginatedListSchema(ItemSchema).parse([{ id: 'b' }])
    expect(unwrapPaginatedList(parsed)).toEqual([{ id: 'b' }])
  })
})
