export interface ParameterFieldDefinition {
  key: string
  label?: string
  type?: 'integer' | 'number' | 'boolean' | 'enum' | 'string' | 'json' | 'artifact_ref' | 'residue_selector'
  default?: unknown
  min?: number
  max?: number
  options?: Array<string | { label: string; value: string }>
  help?: string
  advanced?: boolean
  required?: boolean
}

function safeJson(value: string): unknown {
  try {
    return JSON.parse(value)
  } catch {
    return undefined
  }
}

export function parseParameterSchema(schema: unknown): ParameterFieldDefinition[] {
  const parsed = typeof schema === 'string' ? safeJson(schema) : schema
  if (!parsed || typeof parsed !== 'object') return []
  const fields = (parsed as { fields?: unknown }).fields
  if (!Array.isArray(fields)) return []
  return fields
    .filter((field): field is ParameterFieldDefinition => {
      return Boolean(field && typeof field === 'object' && typeof (field as { key?: unknown }).key === 'string')
    })
    .map((field) => ({
      type: 'string',
      ...field,
    }))
}

function fallbackFields(modelName?: string): ParameterFieldDefinition[] {
  if (modelName === 'RFdiffusion') {
    return [
      { key: 'num_designs', label: 'Number of designs', type: 'integer', default: 100, min: 1, max: 10000 },
      { key: 'contig_map', label: 'Contig map', type: 'string', default: '', help: 'RFdiffusion residue contig constraint.' },
      { key: 'hotspot_residues', label: 'Hotspot residues', type: 'string', default: '', advanced: true },
    ]
  }
  if (modelName === 'ProteinMPNN') {
    return [
      { key: 'num_seq_per_target', label: 'Sequences per target', type: 'integer', default: 8, min: 1, max: 512 },
      { key: 'sampling_temperature', label: 'Sampling temperature', type: 'number', default: 0.1, min: 0, max: 2 },
      { key: 'omit_aas', label: 'Omit amino acids', type: 'string', default: 'CX', advanced: true },
    ]
  }
  if (modelName === 'AlphaFold2') {
    return [
      { key: 'num_recycles', label: 'Recycles', type: 'integer', default: 3, min: 1, max: 48 },
      {
        key: 'model_preset',
        label: 'Model preset',
        type: 'enum',
        default: 'multimer',
        options: ['monomer', 'multimer'],
      },
    ]
  }
  if (modelName === 'Rosetta') {
    return [
      {
        key: 'protocol',
        label: 'Protocol',
        type: 'enum',
        default: 'interface_analyzer',
        options: ['interface_analyzer', 'relax', 'ddg'],
      },
      { key: 'nstruct', label: 'N structures', type: 'integer', default: 1, min: 1, max: 1000 },
    ]
  }
  return [
    { key: 'random_seed', label: 'Random seed', type: 'integer', default: 42, advanced: true },
  ]
}

export function fieldsFromParameterSchema(schema: unknown, modelName?: string): ParameterFieldDefinition[] {
  const fields = parseParameterSchema(schema)
  return fields.length > 0 ? fields : fallbackFields(modelName)
}

export function defaultsFromFields(fields: ParameterFieldDefinition[]): Record<string, unknown> {
  return fields.reduce<Record<string, unknown>>((acc, field) => {
    if (field.default !== undefined) acc[field.key] = field.default
    return acc
  }, {})
}
