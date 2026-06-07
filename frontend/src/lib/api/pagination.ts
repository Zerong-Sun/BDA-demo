import { z } from 'zod'

import { apiRequest } from './client'

/** Accept paginated `{ items, total, ... }` or legacy bare array responses. */
export function paginatedListSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.union([
    z.object({
      items: z.array(itemSchema),
      total: z.number(),
      limit: z.number(),
      offset: z.number(),
    }),
    z.array(itemSchema),
  ])
}

export function unwrapPaginatedList<T>(data: T[] | { items: T[] }): T[] {
  return Array.isArray(data) ? data : data.items
}

export async function fetchPaginatedList<T>(
  path: string,
  itemSchema: z.ZodTypeAny,
  options: RequestInit = {},
): Promise<T[]> {
  const schema = paginatedListSchema(itemSchema)
  const data = await apiRequest(path, options, schema)
  return unwrapPaginatedList(data as T[] | { items: T[] })
}
