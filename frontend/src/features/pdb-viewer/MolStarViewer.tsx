import { useEffect, useRef, useState } from 'react'
import {
  type ColorPreset,
  type RepresentationPreset,
  type ViewPreset,
  molstarColorTheme,
  molstarRepresentation,
} from './ColorPresets'
import type { PluginContext } from 'molstar/lib/mol-plugin/context'
import type { StructureRepresentationBuiltInProps } from 'molstar/lib/mol-plugin-state/helpers/structure-representation-params'
import { ViewerControls } from './ViewerControls'
import { clearStructures, structureFormatFromName } from './structureLoader'
import { applyViewPreset } from './viewPresets'

export interface MolStarViewerProps {
  sourceUrl?: string | null
  file?: File | null
  height?: number | string
  className?: string
  onReady?: () => void
  onError?: (message: string) => void
}

/** Minimal Viewer surface used by this component (loaded dynamically to avoid Vite pre-bundle issues). */
interface MolstarViewer {
  plugin: PluginContext
  dispose(): void
  loadStructureFromData(
    data: string,
    format: 'pdb' | 'mmcif',
    options?: { dataLabel?: string },
  ): Promise<void>
  loadStructureFromUrl(url: string, format: 'pdb' | 'mmcif'): Promise<void>
}

const VIEWER_OPTIONS = {
  layoutIsExpanded: false,
  layoutShowControls: false,
  layoutShowSequence: false,
  layoutShowLog: false,
  layoutShowLeftPanel: false,
  collapseRightPanel: true,
  viewportShowExpand: false,
  viewportShowControls: false,
  viewportShowSelectionMode: false,
  viewportShowAnimation: false,
  viewportShowScreenshotControls: false,
  viewportShowSettings: false,
  viewportShowReset: false,
} as const

async function createViewer(container: HTMLDivElement): Promise<MolstarViewer> {
  const [{ Viewer }] = await Promise.all([
    import('molstar/lib/apps/viewer/app'),
    import('molstar/lib/mol-plugin-ui/skin/dark.scss'),
  ])
  const viewer = await Viewer.create(container, VIEWER_OPTIONS)
  await viewer.plugin.initialized
  return viewer
}

async function applyVisualPreset(
  plugin: PluginContext,
  representation: RepresentationPreset,
  color: ColorPreset,
) {
  const structures = plugin.managers.structure.hierarchy.current.structures
  if (!structures.length) return

  await plugin.managers.structure.component.clear(structures)

  for (const structure of structures) {
    const props: StructureRepresentationBuiltInProps = {
      type: molstarRepresentation(representation) as StructureRepresentationBuiltInProps['type'],
      color: molstarColorTheme(color) as StructureRepresentationBuiltInProps['color'],
    }
    await plugin.builders.structure.representation.addRepresentation(structure.cell, props)
  }
}

export function MolStarViewer({
  sourceUrl,
  file,
  height = 360,
  className,
  onReady,
  onError,
}: MolStarViewerProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<MolstarViewer | null>(null)
  const [representation, setRepresentation] = useState<RepresentationPreset>('cartoon')
  const [color, setColor] = useState<ColorPreset>('chain-id')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [structureLoaded, setStructureLoaded] = useState(false)

  // Keep the latest callbacks in refs so the (expensive) init effect can run
  // exactly once on mount instead of tearing down and rebuilding the Mol*
  // plugin every time the parent passes new inline onReady/onError handlers.
  const onReadyRef = useRef(onReady)
  const onErrorRef = useRef(onError)
  useEffect(() => {
    onReadyRef.current = onReady
    onErrorRef.current = onError
  }, [onReady, onError])

  useEffect(() => {
    let disposed = false

    async function init() {
      if (!hostRef.current) return
      try {
        setLoading(true)
        setError(null)
        const viewer = await createViewer(hostRef.current)
        if (disposed) {
          viewer.dispose()
          return
        }
        viewerRef.current = viewer
        onReadyRef.current?.()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to initialize Mol* viewer'
        setError(message)
        onErrorRef.current?.(message)
      } finally {
        if (!disposed) setLoading(false)
      }
    }

    init()

    return () => {
      disposed = true
      viewerRef.current?.dispose()
      viewerRef.current = null
    }
  }, [])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || loading) return

    async function loadStructure(activeViewer: MolstarViewer) {
      if (!file && !sourceUrl) {
        setStructureLoaded(false)
        return
      }
      try {
        setError(null)
        await clearStructures(activeViewer.plugin)
        if (file) {
          const text = await file.text()
          await activeViewer.loadStructureFromData(
            text,
            structureFormatFromName(file.name),
            { dataLabel: file.name },
          )
        } else if (sourceUrl) {
          await activeViewer.loadStructureFromUrl(
            sourceUrl,
            structureFormatFromName(sourceUrl),
          )
        }
        await applyVisualPreset(activeViewer.plugin, representation, color)
        activeViewer.plugin.managers.camera.focusObject({ durationMs: 250 })
        setStructureLoaded(true)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load structure'
        setError(message)
        onErrorRef.current?.(message)
        setStructureLoaded(false)
      }
    }

    void loadStructure(viewer)
  }, [sourceUrl, file, loading, representation, color])

  useEffect(() => {
    const host = hostRef.current
    const viewer = viewerRef.current
    if (!host || !viewer || loading) return

    const resize = () => viewer.plugin.handleResize()
    const observer = new ResizeObserver(resize)
    observer.observe(host)
    resize()

    return () => observer.disconnect()
  }, [loading])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || loading || !structureLoaded) return
    applyVisualPreset(viewer.plugin, representation, color).catch((err) => {
      const message = err instanceof Error ? err.message : 'Failed to update visualization'
      setError(message)
    })
  }, [representation, color, structureLoaded, loading])

  const handleView = (view: ViewPreset) => {
    const viewer = viewerRef.current
    if (!viewer) return
    applyViewPreset(viewer.plugin, view).catch((err) => {
      const message = err instanceof Error ? err.message : 'Failed to update camera view'
      setError(message)
    })
  }

  return (
    <div className={className}>
      <ViewerControls
        representation={representation}
        color={color}
        onRepresentationChange={setRepresentation}
        onColorChange={setColor}
        onViewChange={handleView}
      />
      <div
        className="molstar-viewer-host relative border border-bda-border"
        style={{ height }}
      >
        <div ref={hostRef} className="absolute inset-0" />
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-bda-bg/80 text-sm text-bda-muted">
            Initializing 3D viewer...
          </div>
        ) : null}
        {error ? (
          <div className="absolute bottom-2 left-2 right-2 rounded-md border border-bda-red/40 bg-bda-panel px-3 py-2 text-xs text-bda-red">
            {error}
          </div>
        ) : null}
        {!loading && !file && !sourceUrl ? (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-bda-muted">
            Upload a PDB file or select a candidate with structure data
          </div>
        ) : null}
      </div>
    </div>
  )
}
