import type { CopilotSkill } from './types'

/** Phase 2 skill registry — wired to DeepSeek / local LLM */
export const copilotSkills: CopilotSkill[] = [
  {
    name: 'programmable-biomaterials-expert',
    description: 'Answer only programmable biomaterials questions with model, method, protein, and assay context',
    trigger: [
      'programmable biomaterial',
      'biomaterial',
      'protein',
      'peptide',
      'binder',
      'scaffold',
      'hydrogel',
      'self-assembly',
      'RFdiffusion',
      'ProteinMPNN',
      'AlphaFold',
      'Rosetta',
      'Mask RGN',
      'PDB',
      'pLDDT',
      'PAE',
      'interface',
      'developability',
      'solubility',
      'aggregation',
      'BLI',
      'SEC',
      '蛋白',
      '多肽',
      '结合蛋白',
      '生物材料',
      '可编程生物材料',
      '方法学',
      '结构',
      '界面',
      '溶解性',
      '聚集',
      '论文',
      '文献',
      '通路',
      '信号通路',
      'PubMed',
      'Europe PMC',
      'sequence',
      '序列',
      '分子量',
    ],
    systemPrompt:
      'You only answer programmable biomaterials questions, including protein design, methods, models, data types, workflow parameters, structure prediction, material properties, and assay interpretation.',
    tools: [
      { name: 'query_candidates', description: 'Query candidate protein/material designs' },
      { name: 'interpret_results', description: 'Interpret BLI/SEC/developability results' },
      { name: 'adjust_workflow', description: 'Suggest biomaterials workflow parameter updates' },
      { name: 'search_literature', description: 'Search Europe PMC literature and abstracts' },
      { name: 'search_pdb', description: 'Search experimental structures in RCSB PDB' },
      { name: 'calculate_sequence_properties', description: 'Calculate sequence-only screening properties' },
      { name: 'search_uniprot', description: 'Search curated UniProt protein function annotations' },
      { name: 'analyze_reactome_pathways', description: 'Analyze related Reactome pathways' },
      { name: 'draft_cluster_job', description: 'Prepare a reviewable LSF job draft' },
    ],
  },
  {
    name: 'paper-reader',
    description: 'Search and summarize protein-design and biomaterials literature',
    trigger: ['paper', 'literature', 'citation', '论文', '文献', 'PubMed', 'Europe PMC'],
    systemPrompt:
      'You summarize protein design papers with methods, datasets, and actionable constraints for BDA workflows.',
    tools: [{ name: 'search_literature', description: 'Search Europe PMC publication metadata and abstracts' }],
  },
  {
    name: 'query-candidates',
    description: 'Query ranked candidates and explain selection rationale',
    trigger: ['candidate', 'rank', 'anchor', '候选'],
    systemPrompt:
      'You explain candidate rankings using interface score, pLDDT, Rosetta, developability, and experiment evidence.',
    tools: [{ name: 'list_candidates', description: 'List candidates for active project' }],
  },
  {
    name: 'workflow-adjust',
    description: 'Suggest workflow node and threshold adjustments',
    trigger: ['workflow', 'route', 'threshold', '工作流'],
    systemPrompt:
      'You adjust BDA workflow nodes and filtering thresholds based on project constraints and failures.',
    tools: [{ name: 'get_workflow_nodes', description: 'Fetch workflow node status' }],
  },
  {
    name: 'result-interpret',
    description: 'Interpret wet-lab results and propose redesign constraints',
    trigger: ['BLI', 'SEC', 'experiment', '实验'],
    systemPrompt:
      'You convert BLI/SEC/expression readouts into next-round design constraints without inventing data.',
    tools: [{ name: 'list_experiment_results', description: 'Fetch experiment results for project' }],
  },
  {
    name: 'structure-explain',
    description: 'Explain structural features using uploaded PDB context',
    trigger: ['structure', 'PDB', 'interface', '结构'],
    systemPrompt:
      'You explain protein structures, interface contacts, hydrophobic patches, and developability risks.',
    tools: [{ name: 'get_candidate_structure', description: 'Fetch candidate structure metadata' }],
  },
]

export function matchSkill(input: string): CopilotSkill | undefined {
  const lower = input.toLowerCase()
  return copilotSkills.find((skill) =>
    skill.trigger.some((token) => lower.includes(token.toLowerCase())),
  )
}
