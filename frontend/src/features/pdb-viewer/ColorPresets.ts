export type RepresentationPreset =
  | 'cartoon'
  | 'surface'
  | 'ball-and-stick'
  | 'backbone'

export type ColorPreset =
  | 'chain-id'
  | 'hydrophobicity'
  | 'electrostatics'
  | 'secondary-structure'
  | 'b-factor'

export type ViewPreset = 'front' | 'back' | 'top' | 'bottom' | 'side' | 'focus'

export const representationOptions: { id: RepresentationPreset; label: string }[] = [
  { id: 'cartoon', label: 'Cartoon' },
  { id: 'surface', label: 'Surface' },
  { id: 'ball-and-stick', label: 'Ball & Stick' },
  { id: 'backbone', label: 'Backbone' },
]

export const colorOptions: { id: ColorPreset; label: string; description: string }[] = [
  { id: 'chain-id', label: 'Chain', description: 'Color by chain ID' },
  { id: 'hydrophobicity', label: 'Hydrophobicity', description: 'Eisenberg hydrophobicity scale' },
  { id: 'electrostatics', label: 'Electrostatics', description: 'Residue charge coloring (red/blue)' },
  { id: 'secondary-structure', label: 'Secondary structure', description: 'Helix / sheet / loop' },
  { id: 'b-factor', label: 'B-factor', description: 'Temperature factor coloring' },
]

export const viewOptions: { id: ViewPreset; label: string }[] = [
  { id: 'front', label: 'Front' },
  { id: 'back', label: 'Back' },
  { id: 'top', label: 'Top' },
  { id: 'bottom', label: 'Bottom' },
  { id: 'side', label: 'Side' },
  { id: 'focus', label: 'Focus' },
]

export function molstarRepresentation(type: RepresentationPreset): string {
  switch (type) {
    case 'cartoon':
      return 'cartoon'
    case 'surface':
      return 'molecular-surface'
    case 'ball-and-stick':
      return 'ball-and-stick'
    case 'backbone':
      return 'backbone'
    default:
      return 'cartoon'
  }
}

export function molstarColorTheme(type: ColorPreset): string {
  switch (type) {
    case 'chain-id':
      return 'chain-id'
    case 'hydrophobicity':
      return 'hydrophobicity'
    case 'electrostatics':
      return 'residue-charge'
    case 'secondary-structure':
      return 'secondary-structure'
    case 'b-factor':
      return 'uncertainty'
    default:
      return 'chain-id'
  }
}
