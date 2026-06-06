import {
  colorOptions,
  representationOptions,
  viewOptions,
  type ColorPreset,
  type RepresentationPreset,
  type ViewPreset,
} from './ColorPresets'

interface ViewerControlsProps {
  representation: RepresentationPreset
  color: ColorPreset
  onRepresentationChange: (value: RepresentationPreset) => void
  onColorChange: (value: ColorPreset) => void
  onViewChange: (value: ViewPreset) => void
}

export function ViewerControls({
  representation,
  color,
  onRepresentationChange,
  onColorChange,
  onViewChange,
}: ViewerControlsProps) {
  return (
    <div className="mb-2 flex flex-wrap gap-2 rounded-lg border border-bda-border bg-bda-panel p-2">
      <label className="flex items-center gap-1 text-xs text-bda-muted">
        Style
        <select
          className="rounded border border-bda-border bg-bda-bg px-2 py-1 text-bda-text"
          value={representation}
          onChange={(e) => onRepresentationChange(e.target.value as RepresentationPreset)}
        >
          {representationOptions.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-1 text-xs text-bda-muted">
        Color
        <select
          className="rounded border border-bda-border bg-bda-bg px-2 py-1 text-bda-text"
          value={color}
          onChange={(e) => onColorChange(e.target.value as ColorPreset)}
        >
          {colorOptions.map((opt) => (
            <option key={opt.id} value={opt.id} title={opt.description}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
      <div className="flex flex-wrap gap-1">
        {viewOptions.map((view) => (
          <button
            key={view.id}
            type="button"
            className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:bg-bda-panel-hover hover:text-bda-text"
            onClick={() => onViewChange(view.id)}
          >
            {view.label}
          </button>
        ))}
      </div>
    </div>
  )
}
