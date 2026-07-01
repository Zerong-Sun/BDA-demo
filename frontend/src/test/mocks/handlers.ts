import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

export const handlers = [
  http.get('/api/v1/health', () =>
    HttpResponse.json({ data: { status: 'ok' }, trace_id: 'test' }),
  ),
  http.get('/api/v1/projects', () =>
    HttpResponse.json({
      data: {
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      },
      trace_id: 'test',
    }),
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
  http.delete('/api/v1/projects/proj_delete_test', () =>
    HttpResponse.json({
      data: {
        project_id: 'proj_delete_test',
        deleted: true,
        workspace: {
          status: 'trashed',
          backend: 'local',
          root: 'projects/proj_delete_test',
          trash_root: 'project_trash/20260701T000000Z_proj_delete_test',
          deleted_at: '2026-07-01T00:00:00Z',
        },
      },
      trace_id: 'test',
    }),
  ),
]

export const server = setupServer(...handlers)
