import clsx from 'clsx'

const toneMap: Record<string, string> = {
  green: 'bg-bda-green/15 text-bda-green border-bda-green/30',
  amber: 'bg-bda-amber/15 text-bda-amber border-bda-amber/30',
  blue: 'bg-bda-blue/15 text-bda-blue border-bda-blue/30',
  red: 'bg-bda-red/15 text-bda-red border-bda-red/30',
  neutral: 'bg-bda-panel-hover text-bda-muted border-bda-border',
}

export function StatusPill({
  label,
  tone = 'neutral',
}: {
  label: string
  tone?: keyof typeof toneMap
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium',
        toneMap[tone] ?? toneMap.neutral,
      )}
    >
      {label}
    </span>
  )
}

export function statusTone(status: string): keyof typeof toneMap {
  const normalized = status.toLowerCase()
  if (['validated', 'completed', 'pass', 'running', 'anchor', 'order'].some((s) => normalized.includes(s))) {
    return 'green'
  }
  if (['retest', 'queued', 'review', 'qc risk', 'hold'].some((s) => normalized.includes(s))) {
    return 'amber'
  }
  if (['failed', 'fail', 'reject'].some((s) => normalized.includes(s))) {
    return 'red'
  }
  return 'neutral'
}
