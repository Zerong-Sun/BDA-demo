import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Plus, X } from 'lucide-react'
import { nodeTemplates, type NodeTemplate } from './workflowTypes'
import { createMethodPlugin, listMethodPlugins, listModelPlugins } from '../../lib/api/registry'
import { ParameterSchemaForm } from '../plugins'
import { defaultsFromFields, fieldsFromParameterSchema } from '../../lib/forms/parameterSchema'
import type { MethodPlugin } from '../../lib/schemas/registry'

const PLUGIN_ICON: Record<string, string> = {
  RFdiffusion: 'wand-sparkles',
  ProteinMPNN: 'dna',
  AlphaFold2: 'scan-search',
  Rosetta: 'activity',
}

interface NodeBuilderProps {
  open: boolean
  onClose: () => void
  onAdd: (
    template: NodeTemplate,
    nodeName: string,
    methods: string[],
    parameters: Record<string, unknown>,
  ) => Promise<void>
}

export function NodeBuilder({ open, onClose, onAdd }: NodeBuilderProps) {
  const [selected, setSelected] = useState('rf')
  const [methods, setMethods] = useState<string[]>(['Affinity score', 'Diversity cap', 'Auto report'])
  const [nodeName, setNodeName] = useState('')
  const [parameters, setParameters] = useState<Record<string, unknown>>({})
  const [adding, setAdding] = useState(false)
  const [nameError, setNameError] = useState('')
  const [newMethodName, setNewMethodName] = useState('')
  const [newMethodType, setNewMethodType] = useState('custom')
  const [newMethodDescription, setNewMethodDescription] = useState('')
  const methodDefaultsApplied = useRef(false)
  const queryClient = useQueryClient()

  const { data: plugins = [] } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
  })

  const { data: methodPlugins = [] } = useQuery<MethodPlugin[]>({
    queryKey: ['method-plugins'],
    queryFn: listMethodPlugins,
  })

  const methodOptions = useMemo(() => {
    if (methodPlugins.length > 0) {
      return methodPlugins.map((mp) => ({
        key: mp.method_plugin_id,
        label: mp.method_name,
        description: mp.description,
        method: mp,
      }))
    }
    const fallback = [
      'Affinity score',
      'Diversity cap',
      'Expression risk',
      'Aggregation penalty',
      'Hydrophobic patch penalty',
      'Auto report',
    ]
    return fallback.map((key) => ({
      key,
      label: key,
      description: undefined as string | undefined,
      method: undefined as MethodPlugin | undefined,
    }))
  }, [methodPlugins])

  useEffect(() => {
    if (!open) {
      methodDefaultsApplied.current = false
      return
    }
    if (methodDefaultsApplied.current || methodOptions.length === 0) return
    const optionKeys = new Set(methodOptions.map((method) => method.key))
    setMethods((current) => {
      methodDefaultsApplied.current = true
      const validCurrent = current.filter((method) => optionKeys.has(method))
      return validCurrent.length > 0 ? validCurrent : methodOptions.slice(0, 3).map((method) => method.key)
    })
  }, [methodOptions, open])

  const activeMethodKeys = useMemo(() => {
    const optionKeys = new Set(methodOptions.map((method) => method.key))
    return methods.filter((method) => optionKeys.has(method))
  }, [methodOptions, methods])

  const selectedMethodOptions = useMemo(
    () => methodOptions.filter((method) => activeMethodKeys.includes(method.key)),
    [activeMethodKeys, methodOptions],
  )

  const createMethod = useMutation({
    mutationFn: () =>
      createMethodPlugin({
        method_name: newMethodName.trim(),
        method_type: newMethodType.trim() || 'custom',
        description: newMethodDescription.trim() || null,
        compatible_model_types: template.modelName ? [template.modelName] : [],
        compatible_workflow_nodes: [template.nodeType],
        default_parameters_json: {},
        status: 'active',
      }),
    onSuccess: async (method) => {
      setNewMethodName('')
      setNewMethodType('custom')
      setNewMethodDescription('')
      setMethods((prev) => Array.from(new Set([...prev, method.method_plugin_id])))
      await queryClient.invalidateQueries({ queryKey: ['method-plugins'] })
    },
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
      parameterSchema: plugin.parameter_schema_json,
    }))
  }, [plugins])

  const template = templates.find((item) => item.id === selected) ?? templates[0] ?? nodeTemplates.rf
  const parameterFields = useMemo(
    () => fieldsFromParameterSchema(template.parameterSchema, template.modelName),
    [template.modelName, template.parameterSchema],
  )
  const parameterSchemaForForm = useMemo(() => ({ fields: parameterFields }), [parameterFields])

  const selectTemplate = (item: NodeTemplate) => {
    setSelected(item.id)
    setNodeName(item.title)
    setParameters(defaultsFromFields(fieldsFromParameterSchema(item.parameterSchema, item.modelName)))
    setNameError('')
  }

  const handleAdd = async () => {
    const trimmedName = nodeName.trim()
    if (!trimmedName) {
      setNameError('Enter node name')
      return
    }
    if (selectedMethodOptions.length === 0) return
    setNameError('')
    setAdding(true)
    try {
      const methodRefs = selectedMethodOptions.map((method) => {
        if (method.method) {
          return {
            method_plugin_id: method.method.method_plugin_id,
            method_name: method.method.method_name,
            method_type: method.method.method_type,
            default_parameters_json: method.method.default_parameters_json ?? {},
          }
        }
        return {
          method_plugin_id: null,
          method_name: method.label,
          method_type: 'built_in',
          default_parameters_json: {},
        }
      })
      await onAdd(template, trimmedName, selectedMethodOptions.map((method) => method.label), {
        ...defaultsFromFields(parameterFields),
        ...parameters,
        method_refs: methodRefs,
      })
    } finally {
      setAdding(false)
    }
  }

  const handleClose = () => {
    if (adding) return
    setNodeName('')
    setParameters({})
    setNameError('')
    onClose()
  }

  if (!open) return null

  return (
    <section className="mb-4 rounded-lg border border-bda-border bg-bda-panel">
      <div className="flex items-start justify-between border-b border-bda-border px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-bda-cyan">Add workflow card</p>
          <h2 className="text-lg font-semibold">Choose a model and configure settings</h2>
        </div>
        <button
          type="button"
          className="rounded border border-bda-border p-1 hover:bg-bda-panel-hover disabled:opacity-40"
          onClick={handleClose}
          disabled={adding}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[2fr_1.2fr_1fr]">
        {/* Model cards */}
        <div>
          <span className="text-xs text-bda-muted">Model cards</span>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {templates.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`rounded-lg border p-3 text-left transition-colors ${
                  selected === item.id
                    ? 'border-bda-cyan bg-bda-cyan/10'
                    : 'border-bda-border hover:border-bda-cyan/40'
                }`}
                onClick={() => {
                  selectTemplate(item)
                }}
                disabled={adding}
              >
                <strong className="block text-sm">{item.title}</strong>
                <small className="text-xs text-bda-muted">{item.body}</small>
              </button>
            ))}
          </div>
        </div>

        {/* Method controls + node name */}
        <div>
          <span className="text-xs text-bda-muted">Node name</span>
          <div className="mt-2">
            <input
              type="text"
              className={`w-full rounded-md border bg-bda-bg px-2.5 py-1.5 text-sm text-bda-text placeholder:text-bda-muted ${
                nameError ? 'border-bda-red' : 'border-bda-border'
              }`}
              placeholder="Enter node name"
              value={nodeName}
              onChange={(e) => {
                setNodeName(e.target.value)
                if (nameError) setNameError('')
              }}
              disabled={adding}
            />
            {nameError ? <p className="mt-1 text-xs text-bda-red">{nameError}</p> : null}
          </div>

          <span className="mt-4 block text-xs text-bda-muted">Method controls</span>
          <div className="mt-2 space-y-2">
            {methodOptions.map((method) => (
              <label key={method.key} className="flex items-start gap-2 text-sm text-bda-text">
                <input
                  type="checkbox"
                  className="mt-0.5 shrink-0"
                  checked={activeMethodKeys.includes(method.key)}
                  onChange={(e) => {
                    setMethods(
                      e.target.checked
                        ? Array.from(new Set([...activeMethodKeys, method.key]))
                        : activeMethodKeys.filter((m) => m !== method.key),
                    )
                  }}
                  disabled={adding}
                />
                <div className="min-w-0">
                  <span className="block leading-snug">{method.label}</span>
                  {method.description ? (
                    <span className="block text-xs text-bda-muted">{method.description}</span>
                  ) : null}
                </div>
              </label>
            ))}
          </div>
          <div className="mt-3 rounded-md border border-dashed border-bda-border p-2">
            <div className="grid gap-2 sm:grid-cols-[1fr_0.75fr]">
              <input
                type="text"
                className="min-w-0 rounded-md border border-bda-border bg-bda-bg px-2 py-1.5 text-sm text-bda-text placeholder:text-bda-muted"
                placeholder="New method name"
                value={newMethodName}
                onChange={(e) => setNewMethodName(e.target.value)}
                disabled={adding || createMethod.isPending}
              />
              <input
                type="text"
                className="min-w-0 rounded-md border border-bda-border bg-bda-bg px-2 py-1.5 text-sm text-bda-text placeholder:text-bda-muted"
                placeholder="Type"
                value={newMethodType}
                onChange={(e) => setNewMethodType(e.target.value)}
                disabled={adding || createMethod.isPending}
              />
            </div>
            <textarea
              className="mt-2 min-h-14 w-full resize-y rounded-md border border-bda-border bg-bda-bg px-2 py-1.5 text-sm text-bda-text placeholder:text-bda-muted"
              placeholder="Method note"
              value={newMethodDescription}
              onChange={(e) => setNewMethodDescription(e.target.value)}
              disabled={adding || createMethod.isPending}
            />
            <button
              type="button"
              className="mt-2 inline-flex items-center gap-1 rounded-md border border-bda-border px-2.5 py-1.5 text-xs text-bda-text hover:bg-bda-panel-hover disabled:opacity-40"
              onClick={() => createMethod.mutate()}
              disabled={adding || createMethod.isPending || !newMethodName.trim()}
            >
              {createMethod.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Create method
            </button>
            {createMethod.isError ? (
              <p className="mt-1 text-xs text-bda-red">Failed to create method</p>
            ) : null}
          </div>
          {selectedMethodOptions.length === 0 ? (
            <p className="mt-2 text-xs text-bda-red">Select at least one method</p>
          ) : null}
        </div>

        {/* Preview card + action */}
        <aside className="space-y-3 rounded-lg border border-bda-border bg-bda-bg p-3">
          <span className="text-xs text-bda-muted">Preview card</span>
          <article className="mt-2 rounded-lg border border-bda-border bg-bda-panel p-3 text-sm">
            <strong>{nodeName || template.title}</strong>
            <p className="mt-1 text-xs text-bda-muted">{template.body}</p>
            <p className="mt-2 text-xs text-bda-muted">
              {selectedMethodOptions.map((method) => method.label).join(' · ')}
            </p>
          </article>
          <div>
            <span className="mb-2 block text-xs text-bda-muted">Plugin parameters</span>
            <ParameterSchemaForm
              schema={parameterSchemaForForm}
              values={{ ...defaultsFromFields(parameterFields), ...parameters }}
              onChange={setParameters}
            />
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              className="flex-1 rounded-md border border-bda-border px-3 py-2 text-sm text-bda-text hover:bg-bda-panel-hover disabled:opacity-40"
              onClick={handleClose}
              disabled={adding}
            >
              Cancel
            </button>
            <button
              type="button"
              className="flex flex-1 items-center justify-center gap-1.5 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
              onClick={() => void handleAdd()}
              disabled={adding || selectedMethodOptions.length === 0}
            >
              {adding ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add card to workflow'
              )}
            </button>
          </div>
        </aside>
      </div>
    </section>
  )
}
