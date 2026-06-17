export type TranslationDict = {
  brand: string
  demoMode: string
  nav: {
    experiments: string
    workflow: string
    candidates: string
    results: string
  }
  loop: {
    experiments: string
    workflow: string
    candidates: string
    results: string
  }
  common: {
    loading: string
    retry: string
    openProject: string
    newExperiment: string
    project: string
    selectProject: string
    noWorkflowData: string
  }
  experiments: {
    eyebrow: string
    title: string
    copilotTitle: string
    copilotBody: string
    planRoute: string
    reviewCandidates: string
    interpretResults: string
    overview: {
      activeProject: string
      bindingPositives: string
      computeAccess: string
      nextAction: string
    }
    agent: {
      planRoute: string
      planRouteBody: string
      adjustWorkflow: string
      adjustWorkflowBody: string
      interpretLab: string
      interpretLabBody: string
    }
  }
  workflow: {
    addNode: string
    startWorkflow: string
    targetIntake: string
    toggleCopilot: string
    readOnly: string
  }
  pdbUpload: {
    dropzone: string
    hint: string
    uploading: string
    replace: string
    replaceHint: string
    invalidFile: string
    uploadSuccess: string
    uploadFallback: string
  }
  nodeBuilder: {
    title: string
    subtitle: string
    modelCards: string
    methodControls: string
    previewCard: string
    addButton: string
    cancel: string
    nodeNameLabel: string
    nodeNamePlaceholder: string
    noMethodsSelected: string
    adding: string
    methodOptions: Record<string, string>
  }
  candidates: {
    eyebrow: string
    title: string
    exportCsv: string
    viewLabResults: string
    explain: string
    predKd: string
  }
  results: {
    eyebrow: string
    title: string
    preparePackage: string
    disclaimer: string
    interpret: string
  }
}
