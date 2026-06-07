import { HashRouter, Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Topbar } from './components/ui/Topbar'
import { Toast } from './components/ui/Toast'
import { CopilotDrawer } from './components/ui/CopilotDrawer'
import { ExperimentsPage } from './app/Experiments'
import { WorkflowPage } from './app/Workflow'
import { CandidatesPage } from './app/Candidates'
import { ResultsPage } from './app/Results'
import { LoginPage } from './app/Login'
import { setUnauthorizedHandler } from './lib/api/client'
import { useAppStore } from './lib/store/appStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

function AuthHandler() {
  const navigate = useNavigate()
  useEffect(() => {
    setUnauthorizedHandler(() => {
      sessionStorage.removeItem('bda_token')
      navigate('/login')
    })
  }, [navigate])
  return null
}

function AppShell() {
  const copilotOpen = useAppStore((s) => s.copilotOpen)
  const setCopilotOpen = useAppStore((s) => s.setCopilotOpen)

  return (
    <>
      <Topbar />
      <main className="mx-auto max-w-[1440px] px-6 py-6">
        <Outlet />
      </main>
      <CopilotDrawer open={copilotOpen} onClose={() => setCopilotOpen(false)} />
      <Toast />
    </>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <AuthHandler />
        <div className="min-h-screen bg-bda-bg text-bda-text">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/experiments" replace />} />
              <Route path="/experiments" element={<ExperimentsPage />} />
              <Route path="/workflow" element={<WorkflowPage />} />
              <Route path="/candidates" element={<CandidatesPage />} />
              <Route path="/results" element={<ResultsPage />} />
            </Route>
          </Routes>
        </div>
      </HashRouter>
    </QueryClientProvider>
  )
}
