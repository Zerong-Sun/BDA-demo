import { useQuery } from '@tanstack/react-query'
import { listModelPlugins } from '../../lib/api/registry'

export function PluginRegistryPanel() {
  const { data: plugins = [], isLoading } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
  })

  return (
    <section className="mb-4 rounded-lg border border-bda-border bg-bda-panel p-4">
      <p className="text-xs uppercase tracking-wide text-bda-cyan">Model plugin registry</p>
      <h2 className="text-lg font-semibold">Registered models</h2>
      {isLoading ? (
        <p className="mt-2 text-sm text-bda-muted">Loading plugins...</p>
      ) : (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {plugins.map((plugin) => (
            <article key={plugin.model_plugin_id} className="rounded-md border border-bda-border bg-bda-bg p-3">
              <div className="flex items-center justify-between gap-2">
                <strong className="text-sm">{plugin.model_name}</strong>
                <span className="text-xs text-bda-muted">{plugin.status}</span>
              </div>
              <p className="mt-1 text-xs text-bda-muted">
                {plugin.provider} · v{plugin.version} · {plugin.model_type}
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
