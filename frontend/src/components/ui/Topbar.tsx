import { NavLink } from 'react-router-dom'
import clsx from 'clsx'
import { useAppStore } from '../../lib/store/appStore'

const routes = [
  { to: '/experiments', label: 'Experiments' },
  { to: '/workflow', label: 'Workflow' },
  { to: '/candidates', label: 'Candidates' },
  { to: '/results', label: 'Results' },
]

export function Topbar() {
  const { language, setLanguage } = useAppStore()

  return (
    <header className="sticky top-0 z-40 flex items-center gap-4 border-b border-bda-border bg-bda-bg/95 px-6 py-3 backdrop-blur">
      <NavLink to="/experiments" className="text-sm font-semibold text-bda-cyan">
        BDA Workbench
      </NavLink>
      <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
        {routes.map((route) => (
          <NavLink
            key={route.to}
            to={route.to}
            className={({ isActive }) =>
              clsx(
                'rounded-md px-3 py-1.5 text-sm transition-colors',
                isActive
                  ? 'bg-bda-panel text-bda-cyan'
                  : 'text-bda-muted hover:bg-bda-panel hover:text-bda-text',
              )
            }
          >
            {route.label}
          </NavLink>
        ))}
      </nav>
      <div className="flex items-center gap-3 text-xs text-bda-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-bda-amber" />
          Demo mode
        </span>
        <button
          type="button"
          className="rounded-md border border-bda-border px-2 py-1 hover:bg-bda-panel"
          onClick={() => setLanguage(language === 'en' ? 'zh' : 'en')}
        >
          {language === 'en' ? '中文' : 'EN'}
        </button>
      </div>
    </header>
  )
}
