import { z } from 'zod'
import { apiRequest } from './client'

export const UserSchema = z.object({
  user_id: z.string(),
  username: z.string(),
  role: z.string(),
  display_name: z.string().nullable().optional(),
  enabled: z.boolean().optional(),
  created_at: z.string().optional(),
})

export type AuthUser = z.infer<typeof UserSchema>

const UsersSchema = z.array(UserSchema)

export function getCurrentUser(): Promise<AuthUser> {
  return apiRequest<AuthUser>('/auth/me', {}, UserSchema)
}

export function listUsers(): Promise<AuthUser[]> {
  return apiRequest<AuthUser[]>('/users', {}, UsersSchema)
}

export interface CreateUserPayload {
  username: string
  password: string
  role?: 'admin' | 'researcher' | 'viewer'
  display_name?: string | null
}

export function createUser(payload: CreateUserPayload): Promise<AuthUser> {
  return apiRequest<AuthUser>(
    '/users',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    UserSchema,
  )
}
