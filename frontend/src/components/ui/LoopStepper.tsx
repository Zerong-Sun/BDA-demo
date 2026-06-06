import { NavLink, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { useI18n } from '../../lib/i18n'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

const steps = [
  { to: '/experiments', key: 'experiments' as const },
  { to: '/workflow', key: 'workflow' as const },
  { to: '/candidates', key: 'candidates' as const },
  { to: '/results', key: 'results' as const },
]

export function LoopStepper() {
  const location = useLocation()
  const { t } = useI18n()
  const { projectId } = useProjectContext()

  const query = `?project=${encodeURIComponent(projectId)}`

  return (
    <nav
      aria-label="Closed-loop navigation"
      className="mb-5 flex flex-wrap items-center gap-2 rounded-lg border border-bda-border bg-bda-panel px-3 py-2"
    >
      {steps.map((step, index) => {
        const active = location.pathname.startsWith(step.to)
        return (
          <div key={step.to} className="flex items-center gap-2">
            {index > 0 ? <span className="text-bda-muted">→</span> : null}
            <NavLink
              to={`${step.to}${query}`}
              className={clsx(
                'rounded-md px-2.5 py-1 text-xs font-medium',
                active ? 'bg-bda-cyan/15 text-bda-cyan' : 'text-bda-muted hover:text-bda-text',
              )}
            >
              {t.loop[step.key]}
            </NavLink>
          </div>
        )
      })}
    </nav>
  )
}
