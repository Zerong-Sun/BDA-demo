import { useEffect, useRef, useState } from 'react'
import {
  type ColorPreset,
  type RepresentationPreset,
  type ViewPreset,
  molstarColorTheme,
  molstarRepresentation,
} from './ColorPresets'
import type { MolPlugin } from './molstar-types'
import { ViewerControls } from './ViewerControls'
import { applyViewPreset } from './viewPresets'

export interface MolStarViewerProps {
  sourceUrl?: string | null
  file?: File | null
  height?: number | string
  className?: string
  onReady?: () => void
  onError?: (message: string) => void
}

async function createMolPlugin(container: HTMLDivElement): Promise<MolPlugin> {
  const [{ createPluginUI }, { renderReact18 }, { DefaultPluginUISpec }, { PluginConfig }] =
    await Promise.all([
      import('molstar/lib/mol-plugin-ui'),
      import('molstar/lib/mol-plugin-ui/react18'),
      import('molstar/lib/mol-plugin-ui/spec'),
      import('molstar/lib/mol-plugin/config'),
    ])

  await import('molstar/lib/mol-plugin-ui/skin/dark.scss')

  const spec = DefaultPluginUISpec()
  spec.layout = {
    initial: {
      isExpanded: false,
      showControls: false,
      controlsDisplay: 'reactive',
    },
  }
  spec.config = [
    [PluginConfig.Viewport.ShowExpand, false],
    [PluginConfig.Viewport.ShowControls, false],
    [PluginConfig.Viewport.ShowSelectionMode, false],
    [PluginConfig.Viewport.ShowAnimation, false],
  ]

  const plugin = await createPluginUI({
    target: container,
    render: renderReact18,
    spec,
  })
  return plugin as unknown as MolPlugin
}

async function applyVisualPreset(
  plugin: MolPlugin,
  representation: RepresentationPreset,
  color: ColorPreset,
) {
  const structures = plugin.managers.structure.hierarchy.current.structures
  if (!structures.length) return

  await plugin.managers.structure.component.clear(structures)

  for (const structure of structures) {
    await plugin.builders.structure.representation.addRepresentation(structure, {
      type: molstarRepresentation(representation),
      colorTheme: { name: molstarColorTheme(color) },
    })
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
  const pluginRef = useRef<MolPlugin | null>(null)
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
        const plugin = await createMolPlugin(hostRef.current)
        if (disposed) {
          plugin.destroy()
          return
        }
        pluginRef.current = plugin
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
      pluginRef.current?.destroy()
      pluginRef.current = null
    }
  }, [])

  useEffect(() => {
    const plugin = pluginRef.current
    if (!plugin || loading) return

    async function loadStructure(activePlugin: MolPlugin) {
      if (!file && !sourceUrl) {
        setStructureLoaded(false)
        return
      }
      try {
        setError(null)
        await activePlugin.clear()
        if (file) {
          const text = await file.text()
          await activePlugin.loadStructureFromData(text, file.name.endsWith('.cif') ? 'mmcif' : 'pdb')
        } else if (sourceUrl) {
          const format = sourceUrl.endsWith('.cif') ? 'mmcif' : 'pdb'
          await activePlugin.loadStructureFromUrl(sourceUrl, format)
        }
        await applyVisualPreset(activePlugin, representation, color)
        setStructureLoaded(true)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load structure'
        setError(message)
        onErrorRef.current?.(message)
        setStructureLoaded(false)
      }
    }

    loadStructure(plugin)
  }, [sourceUrl, file, loading, representation, color])

  useEffect(() => {
    const plugin = pluginRef.current
    if (!plugin || loading || !structureLoaded) return
    applyVisualPreset(plugin, representation, color).catch((err) => {
      const message = err instanceof Error ? err.message : 'Failed to update visualization'
      setError(message)
    })
  }, [representation, color, structureLoaded, loading])

  const handleView = (view: ViewPreset) => {
    const plugin = pluginRef.current
    if (!plugin) return
    applyViewPreset(plugin, view).catch((err) => {
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
