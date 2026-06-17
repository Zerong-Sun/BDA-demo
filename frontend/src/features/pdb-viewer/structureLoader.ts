import type { PluginContext } from 'molstar/lib/mol-plugin/context'

export type StructureFormat = 'pdb' | 'mmcif'

export function structureFormatFromName(name: string): StructureFormat {
  const lower = name.toLowerCase()
  return lower.endsWith('.cif') || lower.endsWith('.mmcif') ? 'mmcif' : 'pdb'
}

export async function clearStructures(plugin: PluginContext): Promise<void> {
  const { trajectories } = plugin.managers.structure.hierarchy.current
  if (trajectories.length > 0) {
    await plugin.managers.structure.hierarchy.remove(trajectories)
  }
}
