import type { TranslationDict } from './types'

export const en: TranslationDict = {
  brand: 'BDA Workbench',
  demoMode: 'Demo mode',
  nav: {
    experiments: 'Experiments',
    workflow: 'Workflow',
    candidates: 'Candidates',
    results: 'Results',
  },
  loop: {
    experiments: 'Experiments',
    workflow: 'Workflow',
    candidates: 'Candidates',
    results: 'Results',
  },
  common: {
    loading: 'Loading...',
    retry: 'Retry',
    openProject: 'Open project',
    newExperiment: 'New experiment',
    project: 'Project',
    selectProject: 'Select project',
    noWorkflowData: 'No workflow data for this project yet. Open the PD-1 demo project to explore the full loop.',
  },
  experiments: {
    eyebrow: 'Project experiment list',
    title: 'BDA Experiments',
    copilotTitle: 'From design brief to traceable loop',
    copilotBody:
      'Plan routes, adjust workflow thresholds, interpret BLI/SEC evidence, and push constraints into the next design round.',
    planRoute: 'Plan route',
    reviewCandidates: 'Review top candidates',
    interpretResults: 'Interpret lab results',
    overview: {
      activeProject: 'Active project',
      bindingPositives: 'BLI positives',
      computeAccess: 'Compute access',
      nextAction: 'Next action',
    },
    agent: {
      planRoute: 'Plan route',
      planRouteBody: 'Propose a PD-1 binder workflow with RFdiffusion, MPNN, AF2, Rosetta, and wet-lab gates.',
      adjustWorkflow: 'Adjust workflow',
      adjustWorkflowBody: 'Tune solubility thresholds, family caps, and hydrophobic patch penalties.',
      interpretLab: 'Interpret lab results',
      interpretLabBody: 'Convert BLI/SEC readouts into round-two redesign constraints.',
    },
  },
  workflow: {
    addNode: 'Add node',
    startWorkflow: 'Start workflow',
    targetIntake: 'Target intake',
    toggleCopilot: 'Toggle Copilot panel',
    readOnly: 'Completed workflow run is read-only.',
  },
  candidates: {
    eyebrow: 'BDA selection layer',
    title: 'Candidate table',
    exportCsv: 'Export CSV',
    viewLabResults: 'View lab results',
    explain: 'Explain selection',
    predKd: 'Pred Kd',
  },
  results: {
    eyebrow: 'Closed-loop evidence',
    title: 'Results and delivery',
    preparePackage: 'Prepare package',
    disclaimer:
      'Precomputed PD-1 binder demo. Metrics and structures are seeded for storytelling, not live model execution.',
    interpret: 'Interpret results',
  },
} as const satisfies TranslationDict
