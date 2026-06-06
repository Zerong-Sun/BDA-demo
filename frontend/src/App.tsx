import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Topbar } from './components/ui/Topbar'
import { Toast } from './components/ui/Toast'
import { ExperimentsPage } from './app/Experiments'
import { WorkflowPage } from './app/Workflow'
import { CandidatesPage } from './app/Candidates'
import { ResultsPage } from './app/Results'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <div className="min-h-screen bg-bda-bg text-bda-text">
          <Topbar />
          <main className="mx-auto max-w-[1440px] px-6 py-6">
            <Routes>
              <Route path="/" element={<Navigate to="/experiments" replace />} />
              <Route path="/experiments" element={<ExperimentsPage />} />
              <Route path="/workflow" element={<WorkflowPage />} />
              <Route path="/candidates" element={<CandidatesPage />} />
              <Route path="/results" element={<ResultsPage />} />
            </Routes>
          </main>
          <Toast />
        </div>
      </HashRouter>
    </QueryClientProvider>
  )
}
