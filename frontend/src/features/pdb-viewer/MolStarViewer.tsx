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

async function loadStructureFromAuthenticatedUrl(
  viewer: MolstarViewer,
  url: string,
): Promise<void> {
  const token = sessionStorage.getItem('bda_token')
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new Error(`Structure download failed (${response.status})`)
  }
  const disposition = response.headers.get('content-disposition') ?? ''
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? url
  const text = await response.text()
  await viewer.loadStructureFromData(text, structureFormatFromName(filename), {
    dataLabel: filename,
  })
}

interface PdbPreview {
  atomCount: number
  residueCount: number
  chains: string[]
  points: string
}

function parsePdbPreview(text: string): PdbPreview {
  const residues = new Set<string>()
  const chains = new Set<string>()
  const coords: Array<{ x: number; y: number }> = []
  let atomCount = 0

  for (const line of text.split('\n')) {
    if (!line.startsWith('ATOM') && !line.startsWith('HETATM')) continue
    atomCount += 1
    const chain = line.slice(21, 22).trim() || 'A'
    const residue = line.slice(22, 26).trim()
    const atomName = line.slice(12, 16).trim()
    chains.add(chain)
    residues.add(`${chain}:${residue}`)
    if (atomName === 'CA') {
      const x = Number.parseFloat(line.slice(30, 38))
      const y = Number.parseFloat(line.slice(38, 46))
      if (Number.isFinite(x) && Number.isFinite(y)) coords.push({ x, y })
    }
  }

  if (coords.length === 0) {
    return { atomCount, residueCount: residues.size, chains: [...chains], points: '' }
  }

  const minX = Math.min(...coords.map((coord) => coord.x))
  const maxX = Math.max(...coords.map((coord) => coord.x))
  const minY = Math.min(...coords.map((coord) => coord.y))
  const maxY = Math.max(...coords.map((coord) => coord.y))
  const width = Math.max(maxX - minX, 1)
  const height = Math.max(maxY - minY, 1)
  const points = coords
    .map((coord) => {
      const x = 24 + ((coord.x - minX) / width) * 272
      const y = 24 + ((coord.y - minY) / height) * 172
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return { atomCount, residueCount: residues.size, chains: [...chains], points }
}

function StructureFallbackPreview({
  sourceUrl,
  file,
}: Pick<MolStarViewerProps, 'sourceUrl' | 'file'>) {
  const [preview, setPreview] = useState<PdbPreview | null>(null)

  useEffect(() => {
    let disposed = false

    async function loadPreview() {
      try {
        let text: string | null = null
        if (file) {
          text = await file.text()
        } else if (sourceUrl) {
          const token = sessionStorage.getItem('bda_token')
          const response = await fetch(sourceUrl, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          })
          if (!response.ok) return
          text = await response.text()
        }
        if (!disposed && text) setPreview(parsePdbPreview(text))
      } catch {
        if (!disposed) setPreview(null)
      }
    }

    void loadPreview()
    return () => {
      disposed = true
    }
  }, [sourceUrl, file])

  return (
    <div className="absolute inset-0 flex flex-col justify-between bg-bda-bg p-4">
      <div className="grid grid-cols-3 gap-2 text-xs">
        <span className="rounded border border-bda-border bg-bda-panel px-2 py-1">
          Atoms {preview?.atomCount ?? '...'}
        </span>
        <span className="rounded border border-bda-border bg-bda-panel px-2 py-1">
          Residues {preview?.residueCount ?? '...'}
        </span>
        <span className="rounded border border-bda-border bg-bda-panel px-2 py-1">
          Chains {preview?.chains.join(', ') || '...'}
        </span>
      </div>
      <svg viewBox="0 0 320 220" className="min-h-0 flex-1">
        <rect x="1" y="1" width="318" height="218" rx="6" className="fill-bda-panel stroke-bda-border" />
        {preview?.points ? (
          <>
            <polyline
              points={preview.points}
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinejoin="round"
              strokeLinecap="round"
              className="text-bda-cyan"
            />
            <circle r="4" className="fill-bda-cyan">
              <animateMotion dur="8s" repeatCount="indefinite" path={`M${preview.points.replaceAll(' ', ' L')}`} />
            </circle>
          </>
        ) : (
          <text x="160" y="110" textAnchor="middle" className="fill-bda-muted text-xs">
            Loading PDB preview
          </text>
        )}
      </svg>
      <p className="text-xs text-bda-muted">PDB backbone preview</p>
    </div>
  )
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
          await loadStructureFromAuthenticatedUrl(activeViewer, sourceUrl)
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
        {error && (file || sourceUrl) ? (
          <StructureFallbackPreview sourceUrl={sourceUrl} file={file} />
        ) : null}
        {error && !file && !sourceUrl ? (
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
