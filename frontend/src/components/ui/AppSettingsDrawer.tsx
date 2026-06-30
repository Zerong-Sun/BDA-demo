import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { CheckCircle2, LogOut, RefreshCw, Server, Settings, UserPlus, X, XCircle } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CopilotSettings } from '../../features/copilot/CopilotSettings'
import { getClusterHealth } from '../../lib/api/registry'
import { getHealth } from '../../lib/api/client'
import { createUser, getCurrentUser, listUsers, type AuthUser } from '../../lib/api/auth'
import { useAppStore } from '../../lib/store/appStore'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

function storedUser(): AuthUser | null {
  try {
    const raw = sessionStorage.getItem('bda_user')
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

export function AppSettingsDrawer() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { settingsOpen, setSettingsOpen, appMode, setAppMode } = useAppStore()
  const { projects, setProjectId } = useProjectContext()
  const [newUser, setNewUser] = useState({
    username: '',
    display_name: '',
    role: 'researcher' as 'admin' | 'researcher' | 'viewer',
    password: '',
  })
  const backend = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    enabled: settingsOpen,
  })
  const me = useQuery({
    queryKey: ['auth-me'],
    queryFn: getCurrentUser,
    enabled: settingsOpen,
  })
  const currentUser = me.data ?? storedUser()
  const users = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
    enabled: settingsOpen && currentUser?.role === 'admin',
    retry: false,
  })
  const cluster = useQuery({
    queryKey: ['cluster-health'],
    queryFn: getClusterHealth,
    enabled: settingsOpen,
    retry: false,
  })
  const createAccount = useMutation({
    mutationFn: createUser,
    onSuccess: async () => {
      setNewUser({ username: '', display_name: '', role: 'researcher', password: '' })
      await queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  if (!settingsOpen) return null

  const refreshConnections = () => {
    void backend.refetch()
    void cluster.refetch()
  }
  const logout = () => {
    sessionStorage.removeItem('bda_token')
    sessionStorage.removeItem('bda_user')
    setSettingsOpen(false)
    navigate('/login', { replace: true })
  }

  return (
    <aside className="fixed inset-y-0 right-0 z-[60] w-full max-w-lg overflow-y-auto border-l border-bda-border bg-bda-panel shadow-2xl">
      <header className="sticky top-0 z-10 flex items-start justify-between border-b border-bda-border bg-bda-panel p-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-bda-cyan">Settings</p>
          <h2 className="text-lg font-semibold">Application settings and connection validation</h2>
        </div>
        <button
          type="button"
          aria-label="Close settings"
          className="rounded-md border border-bda-border p-1.5 hover:bg-bda-panel-hover"
          onClick={() => setSettingsOpen(false)}
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      <section className="space-y-3 border-b border-bda-border p-4">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Settings className="h-4 w-4 text-bda-cyan" />
          Operating mode
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            className={clsx(
              'rounded-md border p-3 text-left',
              appMode === 'application' ? 'border-bda-cyan bg-bda-cyan/10' : 'border-bda-border',
            )}
            onClick={() => setAppMode('application')}
          >
            <strong className="block text-sm">Application mode</strong>
            <span className="mt-1 block text-xs text-bda-muted">Create live projects, workflow runs, and cluster jobs.</span>
          </button>
          <button
            type="button"
            className={clsx(
              'rounded-md border p-3 text-left',
              appMode === 'demo' ? 'border-bda-amber bg-bda-amber/10' : 'border-bda-border',
            )}
            onClick={() => {
              setAppMode('demo')
              const demoProject = projects.find((project) => project.project_id === 'proj_pd1_0423')
              if (demoProject) setProjectId(demoProject.project_id)
            }}
          >
            <strong className="block text-sm">Demo mode</strong>
            <span className="mt-1 block text-xs text-bda-muted">Review curated reference projects and seeded data in read-only mode.</span>
          </button>
        </div>
      </section>

      <section className="space-y-3 border-b border-bda-border p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium">
              <UserPlus className="h-4 w-4 text-bda-cyan" />
              Login and access
            </div>
            <p className="mt-1 text-xs text-bda-muted">
              {currentUser ? `${currentUser.display_name ?? currentUser.username} · ${currentUser.role}` : 'Session pending validation'}
            </p>
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text"
            onClick={logout}
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
        {currentUser?.role === 'admin' ? (
          <form
            className="rounded border border-bda-border bg-bda-bg p-3"
            onSubmit={(event) => {
              event.preventDefault()
              createAccount.mutate({
                username: newUser.username,
                password: newUser.password,
                role: newUser.role,
                display_name: newUser.display_name || null,
              })
            }}
          >
            <div className="grid gap-2 sm:grid-cols-2">
              <AccountInput label="Username" value={newUser.username} onChange={(value) => setNewUser((current) => ({ ...current, username: value }))} required />
              <AccountInput label="Display name" value={newUser.display_name} onChange={(value) => setNewUser((current) => ({ ...current, display_name: value }))} />
              <label className="block">
                <span className="mb-1 block text-[10px] uppercase tracking-wide text-bda-muted">Role</span>
                <select
                  className="w-full rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs"
                  value={newUser.role}
                  onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value as typeof newUser.role }))}
                >
                  <option value="researcher">researcher</option>
                  <option value="viewer">viewer</option>
                  <option value="admin">admin</option>
                </select>
              </label>
              <AccountInput label="Password" type="password" value={newUser.password} onChange={(value) => setNewUser((current) => ({ ...current, password: value }))} required />
            </div>
            {createAccount.error instanceof Error ? (
              <p className="mt-2 text-xs text-bda-red">{createAccount.error.message}</p>
            ) : null}
            <div className="mt-3 flex items-center justify-between gap-2">
              <span className="text-xs text-bda-muted">{users.data?.length ?? 0} users provisioned</span>
              <button
                type="submit"
                className="rounded bg-bda-cyan px-3 py-1.5 text-xs font-medium text-bda-bg disabled:opacity-50"
                disabled={createAccount.isPending || !newUser.username.trim() || !newUser.password.trim()}
              >
                {createAccount.isPending ? 'Creating...' : 'Create user'}
              </button>
            </div>
          </form>
        ) : null}
      </section>

      <section className="space-y-3 border-b border-bda-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Server className="h-4 w-4 text-bda-cyan" />
            Service connections
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs"
            onClick={refreshConnections}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${backend.isFetching || cluster.isFetching ? 'animate-spin' : ''}`} />
            Revalidate
          </button>
        </div>
        <ConnectionRow
          label="BDA backend"
          connected={backend.isSuccess}
          detail={backend.data ? `${backend.data.database} · ${backend.data.compute}` : backend.error instanceof Error ? backend.error.message : 'Awaiting validation'}
        />
        <ConnectionRow
          label="SUSTech LSF cluster"
          connected={cluster.data?.connected === true}
          detail={
            cluster.data?.connected
              ? `${cluster.data.host ?? 'qm'} · ${cluster.data.queues.length} queues`
              : cluster.data?.reason ?? 'Awaiting validation'
          }
        />
      </section>

      <CopilotSettings />
    </aside>
  )
}

function AccountInput({
  label,
  value,
  onChange,
  type = 'text',
  required,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  required?: boolean
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-wide text-bda-muted">{label}</span>
      <input
        className="w-full rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
      />
    </label>
  )
}

function ConnectionRow({ label, connected, detail }: { label: string; connected: boolean; detail: string }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-md border border-bda-border bg-bda-bg p-3">
      <div>
        <strong className="text-sm">{label}</strong>
        <p className="mt-1 text-xs text-bda-muted">{detail}</p>
      </div>
      <span className={`inline-flex items-center gap-1 text-xs ${connected ? 'text-bda-green' : 'text-bda-red'}`}>
        {connected ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
        {connected ? 'Connected' : 'Disconnected'}
      </span>
    </div>
  )
}
