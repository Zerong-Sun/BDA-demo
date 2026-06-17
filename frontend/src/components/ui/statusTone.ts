export type StatusTone = 'green' | 'amber' | 'blue' | 'red' | 'neutral'

export function statusTone(status: string): StatusTone {
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
