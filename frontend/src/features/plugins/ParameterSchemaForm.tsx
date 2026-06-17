import { useMemo } from 'react'
import { parseParameterSchema, type ParameterFieldDefinition } from '../../lib/forms/parameterSchema'

interface ParameterSchemaFormProps {
  schema: unknown
  values: Record<string, unknown>
  onChange: (values: Record<string, unknown>) => void
}

function optionValue(option: string | { label: string; value: string }) {
  return typeof option === 'string' ? option : option.value
}

function optionLabel(option: string | { label: string; value: string }) {
  return typeof option === 'string' ? option : option.label
}

export function ParameterSchemaForm({ schema, values, onChange }: ParameterSchemaFormProps) {
  const fields = useMemo(() => parseParameterSchema(schema), [schema])

  if (fields.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-bda-border bg-bda-bg p-3 text-xs text-bda-muted">
        No parameter schema is registered for this plugin yet.
      </div>
    )
  }

  const basicFields = fields.filter((field) => !field.advanced)
  const advancedFields = fields.filter((field) => field.advanced)

  const renderField = (field: ParameterFieldDefinition) => (
    <ParameterField
      key={field.key}
      field={field}
      value={values[field.key] ?? field.default ?? ''}
      changed={values[field.key] !== undefined && values[field.key] !== field.default}
      onChange={(value) => onChange({ ...values, [field.key]: value })}
    />
  )

  return (
    <div className="space-y-3">
      {basicFields.map(renderField)}
      {advancedFields.length > 0 ? (
        <details className="rounded-md border border-bda-border bg-bda-bg p-3">
          <summary className="cursor-pointer text-xs font-medium text-bda-muted">Advanced parameters</summary>
          <div className="mt-3 space-y-3">{advancedFields.map(renderField)}</div>
        </details>
      ) : null}
    </div>
  )
}

function ParameterField({
  field,
  value,
  changed,
  onChange,
}: {
  field: ParameterFieldDefinition
  value: unknown
  changed: boolean
  onChange: (value: unknown) => void
}) {
  const label = field.label ?? field.key
  const id = `param-${field.key}`

  return (
    <label className="block" htmlFor={id}>
      <span className="flex items-center justify-between gap-2 text-xs font-medium text-bda-text">
        <span>{label}</span>
        {changed ? <span className="text-[10px] uppercase text-bda-cyan">changed</span> : null}
      </span>
      <FieldControl id={id} field={field} value={value} onChange={onChange} />
      {field.help ? <span className="mt-1 block text-xs leading-relaxed text-bda-muted">{field.help}</span> : null}
    </label>
  )
}

function FieldControl({
  id,
  field,
  value,
  onChange,
}: {
  id: string
  field: ParameterFieldDefinition
  value: unknown
  onChange: (value: unknown) => void
}) {
  const baseClass =
    'mt-1 w-full rounded-md border border-bda-border bg-bda-bg px-2.5 py-1.5 text-sm text-bda-text outline-none focus:border-bda-cyan'

  if (field.type === 'boolean') {
    return (
      <input
        id={id}
        type="checkbox"
        className="mt-2 h-4 w-4 accent-bda-cyan"
        checked={Boolean(value)}
        onChange={(event) => onChange(event.target.checked)}
      />
    )
  }

  if (field.type === 'enum') {
    return (
      <select id={id} className={baseClass} value={String(value ?? '')} onChange={(event) => onChange(event.target.value)}>
        {(field.options ?? []).map((option) => (
          <option key={optionValue(option)} value={optionValue(option)}>
            {optionLabel(option)}
          </option>
        ))}
      </select>
    )
  }

  if (field.type === 'json') {
    return (
      <textarea
        id={id}
        className={`${baseClass} min-h-24 font-mono text-xs`}
        value={typeof value === 'string' ? value : JSON.stringify(value ?? {}, null, 2)}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  }

  if (field.type === 'integer' || field.type === 'number') {
    return (
      <input
        id={id}
        type="number"
        className={baseClass}
        min={field.min}
        max={field.max}
        step={field.type === 'integer' ? 1 : 'any'}
        value={Number(value)}
        onChange={(event) => onChange(field.type === 'integer' ? Number.parseInt(event.target.value, 10) : Number(event.target.value))}
      />
    )
  }

  return (
    <input
      id={id}
      type="text"
      className={baseClass}
      value={String(value ?? '')}
      onChange={(event) => onChange(event.target.value)}
    />
  )
}
