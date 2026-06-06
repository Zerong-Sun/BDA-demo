import type { ReactNode } from 'react'

interface PageHeadProps {
  eyebrow: string
  title: string
  actions?: ReactNode
}

export function PageHead({ eyebrow, title, actions }: PageHeadProps) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-xs uppercase tracking-wide text-bda-cyan">{eyebrow}</p>
        <h1 className="mt-1 text-2xl font-semibold text-bda-text">{title}</h1>
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  )
}
