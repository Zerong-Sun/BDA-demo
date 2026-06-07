import { describe, expect, it } from 'vitest'
import { ApiError } from './client'

describe('ApiError', () => {
  it('stores status and payload', () => {
    const err = new ApiError('invalid_credentials', 401, { detail: 'invalid_credentials' })
    expect(err.name).toBe('ApiError')
    expect(err.status).toBe(401)
    expect(err.message).toBe('invalid_credentials')
    expect(err.payload).toEqual({ detail: 'invalid_credentials' })
  })
})
