import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, KeyRound, LoaderCircle, PlugZap, XCircle } from 'lucide-react'
import { getCopilotConfig, testCopilotConfig, updateCopilotConfig } from '../../lib/api/copilot'

export function CopilotSettings() {
  const queryClient = useQueryClient()
  const { data: config, isLoading } = useQuery({
    queryKey: ['copilot-config'],
    queryFn: getCopilotConfig,
    retry: false,
  })
  const [baseUrlDraft, setBaseUrlDraft] = useState<string | null>(null)
  const [modelDraft, setModelDraft] = useState<string | null>(null)
  const [apiKey, setApiKey] = useState('')
  const baseUrl = baseUrlDraft ?? config?.llm_api_base ?? 'https://api.deepseek.com/v1'
  const model = modelDraft ?? config?.llm_model ?? 'deepseek-v4-pro'

  const save = useMutation({
    mutationFn: () =>
      updateCopilotConfig({
        llm_api_base: baseUrl.trim(),
        llm_model: model.trim(),
        ...(apiKey.trim() ? { llm_api_key: apiKey.trim() } : {}),
      }),
    onSuccess: () => {
      setApiKey('')
      setBaseUrlDraft(null)
      setModelDraft(null)
      queryClient.invalidateQueries({ queryKey: ['copilot-config'] })
    },
  })

  const test = useMutation({ mutationFn: testCopilotConfig })

  return (
    <section className="space-y-3 border-b border-bda-border bg-bda-bg p-4">
      <div>
        <div className="flex items-center gap-2 text-sm font-medium text-bda-text">
          <KeyRound className="h-4 w-4 text-bda-cyan" />
          DeepSeek / OpenAI-compatible API
        </div>
        <p className="mt-1 text-xs text-bda-muted">
          Key 只发送到当前 BDA 后端，不会显示完整值。当前是运行时配置，后端重启后需重新填写。
        </p>
      </div>

      {isLoading ? (
        <div className="text-xs text-bda-muted">Loading model configuration…</div>
      ) : (
        <div className="grid gap-2">
          <label className="grid gap-1 text-xs text-bda-muted">
            API base URL
            <input
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={baseUrl}
              onChange={(event) => setBaseUrlDraft(event.target.value)}
            />
          </label>
          <label className="grid gap-1 text-xs text-bda-muted">
            Model
            <input
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={model}
              onChange={(event) => setModelDraft(event.target.value)}
            />
          </label>
          <label className="grid gap-1 text-xs text-bda-muted">
            API key {config?.api_key_configured ? `(${config.api_key_preview})` : ''}
            <input
              type="password"
              autoComplete="off"
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              placeholder={config?.api_key_configured ? 'Leave blank to keep current key' : 'sk-…'}
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
            />
          </label>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-xs font-medium text-bda-bg disabled:opacity-50"
          disabled={save.isPending || !baseUrl.trim() || !model.trim()}
          onClick={() => save.mutate()}
        >
          {save.isPending ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <KeyRound className="h-3.5 w-3.5" />}
          Save configuration
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-xs text-bda-text disabled:opacity-50"
          disabled={test.isPending || !config?.api_key_configured}
          onClick={() => test.mutate()}
        >
          {test.isPending ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <PlugZap className="h-3.5 w-3.5" />}
          Test API
        </button>
      </div>

      {save.isSuccess ? (
        <p className="inline-flex items-center gap-1 text-xs text-bda-green">
          <CheckCircle2 className="h-3.5 w-3.5" /> Configuration saved.
        </p>
      ) : null}
      {save.isError ? (
        <p className="inline-flex items-center gap-1 text-xs text-bda-red">
          <XCircle className="h-3.5 w-3.5" /> Failed to save configuration.
        </p>
      ) : null}
      {test.data ? (
        <p className={`inline-flex items-center gap-1 text-xs ${test.data.connected ? 'text-bda-green' : 'text-bda-red'}`}>
          {test.data.connected ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
          {test.data.connected
            ? `Connected to ${test.data.model}: ${test.data.sample ?? 'OK'}`
            : `Connection failed: ${test.data.reason ?? 'unknown error'}`}
        </p>
      ) : null}
    </section>
  )
}
