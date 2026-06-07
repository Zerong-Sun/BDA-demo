import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

export const handlers = [
  http.get('/api/v1/health', () =>
    HttpResponse.json({ data: { status: 'ok' }, trace_id: 'test' }),
  ),
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = (await request.json()) as { username?: string; password?: string }
    if (body.username === 'admin' && body.password === 'admin123') {
      return HttpResponse.json({
        data: {
          access_token: 'test-token',
          token_type: 'bearer',
          user: { user_id: 'user_admin', username: 'admin', role: 'admin' },
        },
        trace_id: 'test',
      })
    }
    return HttpResponse.json({ message: 'invalid_credentials' }, { status: 401 })
  }),
]

export const server = setupServer(...handlers)
