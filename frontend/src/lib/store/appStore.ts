import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'en' | 'zh'
export type ViewRoute = 'experiments' | 'workflow' | 'candidates' | 'results'

interface AppState {
  language: Language
  activeProjectId: string
  copilotOpen: boolean
  setLanguage: (language: Language) => void
  setActiveProjectId: (projectId: string) => void
  setCopilotOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      language: 'en',
      activeProjectId: 'proj_pd1_0423',
      copilotOpen: true,
      setLanguage: (language) => set({ language }),
      setActiveProjectId: (activeProjectId) => set({ activeProjectId }),
      setCopilotOpen: (copilotOpen) => set({ copilotOpen }),
    }),
    {
      name: 'bda-app-store',
      partialize: (state) => ({
        language: state.language,
        activeProjectId: state.activeProjectId,
      }),
    },
  ),
)
