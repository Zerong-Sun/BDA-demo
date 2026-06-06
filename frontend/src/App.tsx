import { HashRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Topbar } from './components/ui/Topbar'
import { Toast } from './components/ui/Toast'
import { ExperimentsPage } from './app/Experiments'
import { WorkflowPage } from './app/Workflow'
import { CandidatesPage } from './app/Candidates'
import { ResultsPage } from './app/Results'
import { LoginPage } from './app/Login'
import { setUnauthorizedHandler } from './lib/api/client'

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

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <AuthHandler />
        <div className="min-h-screen bg-bda-bg text-bda-text">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <>
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
                </>
              }
            />
          </Routes>
        </div>
      </HashRouter>
    </QueryClientProvider>
  )
}
