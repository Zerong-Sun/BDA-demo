import type { CopilotSkill } from './types'

/** Phase 2 skill registry — wired to DeepSeek / local LLM */
export const copilotSkills: CopilotSkill[] = [
  {
    name: 'paper-reader',
    description: 'Read and summarize papers from the BDA paper database',
    trigger: ['paper', 'literature', 'citation', '论文'],
    systemPrompt:
      'You summarize protein design papers with methods, datasets, and actionable constraints for BDA workflows.',
    tools: [{ name: 'search_paper_db', description: 'Search indexed paper database' }],
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
