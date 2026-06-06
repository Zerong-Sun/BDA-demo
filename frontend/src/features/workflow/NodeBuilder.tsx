import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { nodeTemplates, type NodeTemplate } from './workflowTypes'
import { listModelPlugins } from '../../lib/api/registry'

const methodOptions = [
  'Affinity score',
  'Diversity cap',
  'Expression risk',
  'Aggregation penalty',
  'Hydrophobic patch penalty',
  'Auto report',
]

const PLUGIN_ICON: Record<string, string> = {
  RFdiffusion: 'wand-sparkles',
  ProteinMPNN: 'dna',
  AlphaFold2: 'scan-search',
  Rosetta: 'activity',
}

interface NodeBuilderProps {
  open: boolean
  onClose: () => void
  onAdd: (template: NodeTemplate, methods: string[]) => void | Promise<void>
}

export function NodeBuilder({ open, onClose, onAdd }: NodeBuilderProps) {
  const [selected, setSelected] = useState('rf')
  const [methods, setMethods] = useState<string[]>(['Affinity score', 'Diversity cap', 'Auto report'])
  const { data: plugins = [] } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
  })

  const templates = useMemo(() => {
    if (!plugins.length) return Object.values(nodeTemplates)
    return plugins.map((plugin) => ({
      id: plugin.model_plugin_id,
      icon: PLUGIN_ICON[plugin.model_name] ?? 'activity',
      title: plugin.model_name,
      body: plugin.description ?? `${plugin.model_type} model plugin`,
      resource: plugin.model_type.includes('gpu') ? ('gpu' as const) : ('cpu' as const),
      nodeType:
        plugin.model_name === 'RFdiffusion'
          ? 'backbone_generation'
          : plugin.model_name === 'ProteinMPNN'
            ? 'sequence_generation'
            : plugin.model_name === 'AlphaFold2'
              ? 'fold_prediction'
              : 'scoring',
      modelName: plugin.model_name,
      modelVersion: plugin.version,
      pluginId: plugin.model_plugin_id,
    }))
  }, [plugins])

  const template = templates.find((item) => item.id === selected) ?? templates[0] ?? nodeTemplates.rf

  if (!open) return null

  return (
    <section className="mb-4 rounded-lg border border-bda-border bg-bda-panel">
      <div className="flex items-start justify-between border-b border-bda-border px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-bda-cyan">Add workflow card</p>
          <h2 className="text-lg font-semibold">Choose a model or method</h2>
        </div>
        <button type="button" className="rounded border border-bda-border p-1 hover:bg-bda-panel-hover" onClick={onClose}>
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-[2fr_1.2fr_1fr]">
        <div>
          <span className="text-xs text-bda-muted">Model cards</span>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {templates.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`rounded-lg border p-3 text-left ${
                  selected === item.id
                    ? 'border-bda-cyan bg-bda-cyan/10'
                    : 'border-bda-border hover:border-bda-cyan/40'
                }`}
                onClick={() => setSelected(item.id)}
              >
                <strong className="block text-sm">{item.title}</strong>
                <small className="text-xs text-bda-muted">{item.body}</small>
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="text-xs text-bda-muted">Method controls</span>
          <div className="mt-2 space-y-2">
            {methodOptions.map((method) => (
              <label key={method} className="flex items-center gap-2 text-sm text-bda-text">
                <input
                  type="checkbox"
                  checked={methods.includes(method)}
                  onChange={(e) => {
                    setMethods((prev) =>
                      e.target.checked ? [...prev, method] : prev.filter((m) => m !== method),
                    )
                  }}
                />
                {method}
              </label>
            ))}
          </div>
        </div>
        <aside className="rounded-lg border border-bda-border bg-bda-bg p-3">
          <span className="text-xs text-bda-muted">Preview card</span>
          <article className="mt-2 rounded-lg border border-bda-border bg-bda-panel p-3 text-sm">
            <strong>{template.title}</strong>
            <p className="mt-1 text-xs text-bda-muted">{template.body}</p>
            <p className="mt-2 text-xs text-bda-muted">{methods.join(', ')}</p>
          </article>
          <button
            type="button"
            className="mt-3 w-full rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg"
            onClick={() => void onAdd(template, methods)}
          >
            Add card to workflow
          </button>
        </aside>
      </div>
    </section>
  )
}
