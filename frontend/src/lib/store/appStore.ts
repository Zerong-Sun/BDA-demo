import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'en' | 'zh'
export type AppMode = 'application' | 'demo'

interface AppState {
  language: Language
  appMode: AppMode
  activeProjectId: string
  workflowRunIdsByProject: Record<string, string>
  copilotOpen: boolean
  copilotWidth: number
  targetIntakeOpen: boolean
  setLanguage: (language: Language) => void
  setAppMode: (mode: AppMode) => void
  setActiveProjectId: (projectId: string) => void
  setProjectWorkflowRunId: (projectId: string, workflowRunId: string) => void
  setCopilotOpen: (open: boolean) => void
  setCopilotWidth: (width: number) => void
  setTargetIntakeOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      language: 'en',
      appMode: 'application',
      activeProjectId: 'proj_pd1_0423',
      workflowRunIdsByProject: {},
      copilotOpen: true,
      copilotWidth: 380,
      targetIntakeOpen: false,
      setLanguage: (language) => set({ language }),
      setAppMode: (appMode) => set({ appMode }),
      setActiveProjectId: (activeProjectId) => set({ activeProjectId }),
      setProjectWorkflowRunId: (projectId, workflowRunId) =>
        set((state) => ({
          workflowRunIdsByProject: {
            ...state.workflowRunIdsByProject,
            [projectId]: workflowRunId,
          },
        })),
      setCopilotOpen: (copilotOpen) => set({ copilotOpen }),
      setCopilotWidth: (copilotWidth) => set({ copilotWidth }),
      setTargetIntakeOpen: (targetIntakeOpen) => set({ targetIntakeOpen }),
    }),
    {
      name: 'bda-app-store',
      partialize: (state) => ({
        language: state.language,
        appMode: state.appMode,
        activeProjectId: state.activeProjectId,
        workflowRunIdsByProject: state.workflowRunIdsByProject,
        copilotOpen: state.copilotOpen,
        copilotWidth: state.copilotWidth,
        targetIntakeOpen: state.targetIntakeOpen,
      }),
    },
  ),
)
