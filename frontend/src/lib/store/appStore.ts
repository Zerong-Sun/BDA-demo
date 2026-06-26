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
  settingsOpen: boolean
  copilotWidth: number
  targetIntakeOpen: boolean
  setLanguage: (language: Language) => void
  setAppMode: (mode: AppMode) => void
  setActiveProjectId: (projectId: string) => void
  setProjectWorkflowRunId: (projectId: string, workflowRunId: string) => void
  setCopilotOpen: (open: boolean) => void
  setSettingsOpen: (open: boolean) => void
  setCopilotWidth: (width: number) => void
  setTargetIntakeOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      language: 'en',
      appMode: 'application',
      activeProjectId: '',
      workflowRunIdsByProject: {},
      copilotOpen: true,
      settingsOpen: false,
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
      setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
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
        settingsOpen: state.settingsOpen,
        copilotWidth: state.copilotWidth,
        targetIntakeOpen: state.targetIntakeOpen,
      }),
    },
  ),
)
