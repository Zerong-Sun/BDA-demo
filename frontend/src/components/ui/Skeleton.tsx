import clsx from 'clsx'

interface SkeletonProps {
  className?: string
}

/** A single shimmering placeholder block. */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={clsx('animate-pulse rounded-md bg-bda-panel-hover/60', className)}
    />
  )
}

interface SkeletonTableProps {
  rows?: number
  columns?: number
  className?: string
}

/** Table-shaped skeleton for list/table loading states. */
export function SkeletonTable({ rows = 5, columns = 4, className }: SkeletonTableProps) {
  return (
    <div className={clsx('space-y-2', className)} role="status" aria-label="Loading content">
      <div className="flex gap-3">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`h-${i}`} className="h-4 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={`r-${r}`} className="flex gap-3">
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton key={`c-${r}-${c}`} className="h-8 flex-1" />
          ))}
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  )
}

/** Card-shaped skeleton for metric/summary loading states. */
export function SkeletonCards({ count = 3, className }: { count?: number; className?: string }) {
  return (
    <div className={clsx('grid gap-4 sm:grid-cols-2 lg:grid-cols-3', className)} role="status" aria-label="Loading content">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-bda-border p-4">
          <Skeleton className="mb-3 h-4 w-1/2" />
          <Skeleton className="h-8 w-3/4" />
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  )
}
