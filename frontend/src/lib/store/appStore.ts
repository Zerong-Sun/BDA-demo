import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'en' | 'zh'
export type AppMode = 'application' | 'demo'
export interface CopilotChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export const defaultCopilotMessages: CopilotChatMessage[] = [
  {
    role: 'assistant',
    content:
      'I am BDA Copilot for this project. Ask me to plan a route, inspect uploaded files, explain workflow state, draft an LSF job, or summarize biomaterials evidence. I will keep the same conversation as you move between pages.',
  },
]

interface AppState {
  language: Language
  appMode: AppMode
  activeProjectId: string
  workflowRunIdsByProject: Record<string, string>
  copilotMessages: CopilotChatMessage[]
  copilotOpen: boolean
  settingsOpen: boolean
  copilotWidth: number
  targetIntakeOpen: boolean
  setLanguage: (language: Language) => void
  setAppMode: (mode: AppMode) => void
  setActiveProjectId: (projectId: string) => void
  setProjectWorkflowRunId: (projectId: string, workflowRunId: string) => void
  clearProjectState: (projectId: string) => void
  setCopilotMessages: (
    messages:
      | CopilotChatMessage[]
      | ((messages: CopilotChatMessage[]) => CopilotChatMessage[]),
  ) => void
  resetCopilotMessages: () => void
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
      copilotMessages: defaultCopilotMessages,
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
      clearProjectState: (projectId) =>
        set((state) => {
          const workflowRunIdsByProject = { ...state.workflowRunIdsByProject }
          delete workflowRunIdsByProject[projectId]
          return {
            activeProjectId: state.activeProjectId === projectId ? '' : state.activeProjectId,
            workflowRunIdsByProject,
          }
        }),
      setCopilotMessages: (messages) =>
        set((state) => ({
          copilotMessages:
            typeof messages === 'function'
              ? messages(state.copilotMessages)
              : messages,
        })),
      resetCopilotMessages: () => set({ copilotMessages: defaultCopilotMessages }),
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
        copilotMessages: state.copilotMessages,
        copilotOpen: state.copilotOpen,
        settingsOpen: state.settingsOpen,
        copilotWidth: state.copilotWidth,
        targetIntakeOpen: state.targetIntakeOpen,
      }),
    },
  ),
)
