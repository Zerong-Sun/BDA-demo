import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'en' | 'zh'

interface AppState {
  language: Language
  activeProjectId: string
  copilotOpen: boolean
  targetIntakeOpen: boolean
  setLanguage: (language: Language) => void
  setActiveProjectId: (projectId: string) => void
  setCopilotOpen: (open: boolean) => void
  setTargetIntakeOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      language: 'en',
      activeProjectId: 'proj_pd1_0423',
      copilotOpen: true,
      targetIntakeOpen: false,
      setLanguage: (language) => set({ language }),
      setActiveProjectId: (activeProjectId) => set({ activeProjectId }),
      setCopilotOpen: (copilotOpen) => set({ copilotOpen }),
      setTargetIntakeOpen: (targetIntakeOpen) => set({ targetIntakeOpen }),
    }),
    {
      name: 'bda-app-store',
      partialize: (state) => ({
        language: state.language,
        activeProjectId: state.activeProjectId,
        copilotOpen: state.copilotOpen,
        targetIntakeOpen: state.targetIntakeOpen,
      }),
    },
  ),
)
