import { NavLink, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { ChevronDown, Settings } from 'lucide-react'
import { useI18n } from '../../lib/i18n'
import { useProjectContext } from '../../lib/hooks/useProjectContext'
import { useAppStore } from '../../lib/store/appStore'
import { BackendHealthBanner } from './BackendHealthBanner'
import { CopilotToggleButton } from './CopilotDrawer'

const routes = [
  { to: '/experiments', key: 'experiments' as const },
  { to: '/workflow', key: 'workflow' as const },
  { to: '/candidates', key: 'candidates' as const },
  { to: '/results', key: 'results' as const },
  { to: '/research', label: 'Research' },
]

function currentUserLabel(): string | null {
  try {
    const raw = sessionStorage.getItem('bda_user')
    if (!raw) return null
    const user = JSON.parse(raw) as { display_name?: string; username?: string }
    return user.display_name || user.username || null
  } catch {
    return null
  }
}

export function Topbar() {
  const navigate = useNavigate()
  const { language, setLanguage, appMode, copilotOpen, setCopilotOpen, setSettingsOpen } = useAppStore()
  const { t } = useI18n()
  const { projects, activeProject, projectId, setProjectId } = useProjectContext()
  const userLabel = currentUserLabel()
  const projectQuery = projectId ? `?project=${encodeURIComponent(projectId)}` : ''

  const logout = () => {
    sessionStorage.removeItem('bda_token')
    sessionStorage.removeItem('bda_user')
    navigate('/login')
  }

  return (
    <>
    <header className="sticky top-0 z-40 flex items-center gap-4 border-b border-bda-border bg-bda-bg/95 px-6 py-3 backdrop-blur">
      <NavLink to={`/experiments${projectQuery}`} className="text-sm font-semibold text-bda-cyan">
        {t.brand}
      </NavLink>
      <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
        {routes.map((route) => (
          <NavLink
            key={route.to}
            to={`${route.to}${projectQuery}`}
            className={({ isActive }) =>
              clsx(
                'rounded-md px-3 py-1.5 text-sm transition-colors',
                isActive
                  ? 'bg-bda-panel text-bda-cyan'
                  : 'text-bda-muted hover:bg-bda-panel hover:text-bda-text',
              )
            }
          >
            {'label' in route ? route.label : t.nav[route.key]}
          </NavLink>
        ))}
      </nav>
      <label className="relative hidden items-center gap-2 text-xs text-bda-muted lg:flex">
        <span>{t.common.project}</span>
        <select
          className="appearance-none rounded-md border border-bda-border bg-bda-panel py-1 pl-2 pr-7 text-sm text-bda-text"
          value={activeProject?.project_id ?? ''}
          onChange={(e) => setProjectId(e.target.value)}
          aria-label={t.common.selectProject}
        >
          <option value="">未选择项目</option>
          {projects.map((project) => (
            <option key={project.project_id} value={project.project_id}>
              {project.project_name}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-1 h-4 w-4" />
      </label>
      <div className="flex items-center gap-3 text-xs text-bda-muted">
        <span
          className={clsx(
            'hidden rounded border px-2 py-1 sm:inline',
            appMode === 'application'
              ? 'border-bda-cyan/40 text-bda-cyan'
              : 'border-bda-amber/40 text-bda-amber',
          )}
        >
          {appMode === 'application' ? '应用模式' : '演示模式'}
        </span>
        <CopilotToggleButton active={copilotOpen} onClick={() => setCopilotOpen(!copilotOpen)} />
        <button
          type="button"
          aria-label="应用设置"
          title="应用设置"
          className="rounded-md border border-bda-border p-1.5 hover:bg-bda-panel"
          onClick={() => setSettingsOpen(true)}
        >
          <Settings className="h-4 w-4" />
        </button>
        {userLabel ? (
          <>
            <span className="hidden text-bda-text sm:inline">{userLabel}</span>
            <button
              type="button"
              className="rounded-md border border-bda-border px-2 py-1 hover:bg-bda-panel"
              onClick={logout}
            >
              Logout
            </button>
          </>
        ) : (
          <button
            type="button"
            className="rounded-md border border-bda-border px-2 py-1 hover:bg-bda-panel"
            onClick={() => navigate('/login')}
          >
            Login
          </button>
        )}
        <button
          type="button"
          className="rounded-md border border-bda-border px-2 py-1 hover:bg-bda-panel"
          onClick={() => setLanguage(language === 'en' ? 'zh' : 'en')}
        >
          {language === 'en' ? '中文' : 'EN'}
        </button>
      </div>
    </header>
    <BackendHealthBanner />
    </>
  )
}
