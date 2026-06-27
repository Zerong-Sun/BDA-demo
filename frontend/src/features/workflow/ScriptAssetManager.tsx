import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileUp, LoaderCircle, RefreshCw, ScrollText } from 'lucide-react'
import { listModelPlugins, listScriptAssets, uploadScriptAsset } from '../../lib/api/registry'
import type { ScriptAsset } from '../../lib/schemas/registry'
import { useToastStore } from '../../components/ui/toastStore'

function warningCount(asset: ScriptAsset): number {
  const raw = asset.parse_warnings_json
  if (Array.isArray(raw)) return raw.length
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw) as unknown
      return Array.isArray(parsed) ? parsed.length : 0
    } catch {
      return 0
    }
  }
  return 0
}

export function ScriptAssetManager() {
  const [modelPluginId, setModelPluginId] = useState('')
  const [relativePath, setRelativePath] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [lastResult, setLastResult] = useState<string>('')
  const queryClient = useQueryClient()
  const showToast = useToastStore((s) => s.show)

  const { data: plugins = [] } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
  })

  const {
    data: scripts = [],
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['script-assets', modelPluginId],
    queryFn: () => listScriptAssets(modelPluginId || undefined),
  })

  const selectedModel = useMemo(
    () => plugins.find((plugin) => plugin.model_plugin_id === modelPluginId),
    [modelPluginId, plugins],
  )

  const upload = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('Select a script file before import.')
      return uploadScriptAsset(file, {
        modelPluginId: modelPluginId || undefined,
        relativePath: relativePath.trim() || undefined,
      })
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['script-assets'] })
      await queryClient.invalidateQueries({ queryKey: ['model-parameter-catalog'] })
      setFile(null)
      setLastResult(
        `Success: ${result.item.relative_path} · parameters ${result.item.parameter_observations} · warnings ${result.item.parse_warnings}`,
      )
      showToast(
        `Script imported: ${result.item.parameter_observations} parameters, ${result.item.parse_warnings} warnings`,
        'success',
      )
    },
    onError: (error) => {
      setLastResult(error instanceof Error ? `Failed: ${error.message}` : 'Failed: script import failed')
      showToast(error instanceof Error ? error.message : 'Script import failed', 'error')
    },
  })

  return (
    <section className="rounded-lg border border-bda-border bg-bda-panel p-3">
      <div className="mb-3 flex items-center gap-2">
        <ScrollText className="h-4 w-4 text-bda-cyan" />
        <div>
          <p className="text-xs uppercase tracking-wide text-bda-cyan">Scripts</p>
          <h2 className="text-sm font-semibold">Model script imports</h2>
        </div>
      </div>

      <div className="grid gap-2">
        <p className="rounded border border-bda-border bg-bda-bg px-2 py-2 text-[11px] leading-relaxed text-bda-muted">
          Imported scripts are archived and parsed for parameter observations. They are not submitted automatically; jobs are created when a node or workflow run is submitted.
        </p>
        <label className="grid gap-1 text-xs text-bda-muted">
          Model plugin
          <select
            className="rounded-md border border-bda-border bg-bda-bg px-2 py-2 text-xs text-bda-text"
            value={modelPluginId}
            onChange={(event) => setModelPluginId(event.target.value)}
          >
            <option value="">Auto-detect or show all scripts</option>
            {plugins.map((plugin) => (
              <option key={plugin.model_plugin_id} value={plugin.model_plugin_id}>
                {plugin.model_name}
              </option>
            ))}
          </select>
        </label>

          <label className="grid gap-1 text-xs text-bda-muted">
          Archive path
          <input
            className="rounded-md border border-bda-border bg-bda-bg px-2 py-2 text-xs text-bda-text"
            value={relativePath}
            onChange={(event) => setRelativePath(event.target.value)}
            placeholder={selectedModel ? `${selectedModel.model_name}/submit.lsf` : 'Example: af3/submit.lsf'}
          />
        </label>

        <label className="grid gap-1 text-xs text-bda-muted">
          Script file
          <input
            className="rounded-md border border-bda-border bg-bda-bg px-2 py-2 text-xs text-bda-text file:mr-2 file:rounded file:border-0 file:bg-bda-cyan file:px-2 file:py-1 file:text-xs file:font-medium file:text-bda-bg"
            type="file"
            accept=".lsf,.sh,.py,.xml"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>

        <div className="flex gap-2">
          <button
            type="button"
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-xs font-medium text-bda-bg disabled:opacity-50"
            disabled={!file || upload.isPending}
            onClick={() => upload.mutate()}
          >
            {upload.isPending ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <FileUp className="h-3.5 w-3.5" />}
          {upload.isPending ? 'Importing...' : 'Upload and import'}
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md border border-bda-border px-2 py-2 text-bda-text disabled:opacity-50"
            title="Refresh script registry"
            disabled={isFetching}
            onClick={() => void refetch()}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {lastResult ? (
        <p className={`mt-3 rounded border px-2 py-2 text-xs ${lastResult.startsWith('Failed') ? 'border-bda-red/40 text-bda-red' : 'border-bda-green/40 text-bda-green'}`}>
          {lastResult}
        </p>
      ) : null}

      <div className="mt-3 space-y-2">
        {isLoading ? <p className="text-xs text-bda-muted">Loading script registry...</p> : null}
        {!isLoading && scripts.length === 0 ? (
          <p className="rounded border border-dashed border-bda-border px-3 py-4 text-center text-xs text-bda-muted">
            No scripts have been imported yet. Upload a script to register it and review the import status.
          </p>
        ) : null}
        {scripts.slice(0, 6).map((script) => (
          <article key={script.script_asset_id} className="rounded-md border border-bda-border bg-bda-bg p-2">
            <div className="flex items-center justify-between gap-2">
              <strong className="truncate text-xs">{script.relative_path}</strong>
              <span className="shrink-0 rounded border border-bda-border px-1.5 py-0.5 text-[10px] text-bda-muted">
                {script.language}
              </span>
            </div>
            <p className="mt-1 truncate text-[11px] text-bda-muted">
              {script.model_plugin_id ?? 'auto'} · {script.scheduler ?? 'no scheduler'} · warnings {warningCount(script)}
            </p>
            <p className="mt-1 truncate font-mono text-[10px] text-bda-muted">{script.content_hash}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
