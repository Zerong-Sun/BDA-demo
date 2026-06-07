import { HashRouter, Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Topbar } from './components/ui/Topbar'
import { Toast } from './components/ui/Toast'
import { CopilotDrawer } from './components/ui/CopilotDrawer'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { ExperimentsPage } from './app/Experiments'
import { WorkflowPage } from './app/Workflow'
import { CandidatesPage } from './app/Candidates'
import { ResultsPage } from './app/Results'
import { LoginPage } from './app/Login'
import { ApiError, setUnauthorizedHandler } from './lib/api/client'
import { useAppStore } from './lib/store/appStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Retry transient failures up to 3 times, but never retry client errors
      // (4xx) such as 401/404 where retrying cannot help.
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false
        }
        return failureCount < 3
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30_000),
    },
    mutations: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false
        }
        return failureCount < 2
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
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

function RequireAuth() {
  const token = sessionStorage.getItem('bda_token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

function AppShell() {
  const copilotOpen = useAppStore((s) => s.copilotOpen)
  const setCopilotOpen = useAppStore((s) => s.setCopilotOpen)

  return (
    <>
      <Topbar />
      <main className="mx-auto max-w-[1440px] px-6 py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
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
            <Route element={<RequireAuth />}>
              <Route element={<AppShell />}>
                <Route index element={<Navigate to="/experiments" replace />} />
                <Route path="/experiments" element={<ExperimentsPage />} />
                <Route path="/workflow" element={<WorkflowPage />} />
                <Route path="/candidates" element={<CandidatesPage />} />
                <Route path="/results" element={<ResultsPage />} />
              </Route>
            </Route>
          </Routes>
        </div>
      </HashRouter>
    </QueryClientProvider>
  )
}
