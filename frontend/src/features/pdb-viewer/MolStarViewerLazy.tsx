import { lazy, Suspense } from 'react'
import type { MolStarViewerProps } from './MolStarViewer'

const LazyMolStarViewer = lazy(() =>
  import('./MolStarViewer').then((module) => ({ default: module.MolStarViewer })),
)

export function MolStarViewerLazy(props: MolStarViewerProps) {
  return (
    <Suspense
      fallback={
        <div
          className="flex items-center justify-center border border-bda-border bg-bda-bg text-sm text-bda-muted"
          style={{ height: props.height ?? 360 }}
        >
          Loading 3D viewer...
        </div>
      }
    >
      <LazyMolStarViewer {...props} />
    </Suspense>
  )
}
