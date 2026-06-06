import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'

interface LoginResponse {
  access_token: string
  token_type: string
  user: {
    user_id: string
    username: string
    role: string
    display_name?: string
  }
}

export function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      sessionStorage.setItem('bda_token', data.access_token)
      sessionStorage.setItem('bda_user', JSON.stringify(data.user))
      navigate('/experiments')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl border border-bda-border bg-bda-panel p-8"
      >
        <h1 className="mb-6 text-xl font-semibold text-bda-text">BDA Workbench</h1>
        {error && <p className="mb-4 text-sm text-bda-red">{error}</p>}
        <label className="mb-4 block">
          <span className="mb-1 block text-sm text-bda-muted">Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg border border-bda-border bg-bda-bg px-3 py-2 text-bda-text"
            autoComplete="username"
          />
        </label>
        <label className="mb-6 block">
          <span className="mb-1 block text-sm text-bda-muted">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-bda-border bg-bda-bg px-3 py-2 text-bda-text"
            autoComplete="current-password"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-bda-cyan px-4 py-2 font-medium text-bda-bg hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="mt-4 text-center text-xs text-bda-muted">Default: admin / admin123</p>
      </form>
    </div>
  )
}
