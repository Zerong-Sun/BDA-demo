import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { PackageCheck } from 'lucide-react'
import { listExperimentResults } from '../lib/api/experiments'
import { getDeliveryPackageOrNull, getResultsSummary } from '../lib/api/projects'
import { interpretResults } from '../lib/api/copilot'
import { deliveryPackageDownloadUrl } from '../lib/api/client'
import { PageHead } from '../components/ui/PageHead'
import { ResultsMetrics } from '../features/results/ResultsMetrics'
import { ValidationTable } from '../features/results/ValidationTable'
import { ExperimentUpload } from '../features/results/ExperimentUpload'
import { DeliveryPackage } from '../features/results/DeliveryPackage'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useToastStore } from '../components/ui/toastStore'
import { useI18n } from '../lib/i18n'
import { ProjectContextBar } from '../features/projects/ProjectContextBar'

const DEMO_PROJECT_ID = 'proj_pd1_0423'

function InlineError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="mb-4 rounded-lg border border-bda-red/40 bg-bda-panel p-3 text-sm text-bda-red">
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          className="mt-2 rounded-md border border-bda-border px-3 py-1 text-bda-text hover:bg-bda-panel-hover"
          onClick={onRetry}
        >
          Retry
        </button>
      ) : null}
    </div>
  )
}

export function ResultsPage() {
  const { t } = useI18n()
  const { projectId, setProjectId } = useProjectContext()
  const queryClient = useQueryClient()
  const showToast = useToastStore((s) => s.show)

  const {
    data: results = [],
    isLoading: resultsLoading,
    isError: resultsError,
    error: resultsQueryError,
    refetch: refetchResults,
  } = useQuery({
    queryKey: ['experiment-results', projectId],
    queryFn: () => listExperimentResults(projectId),
    enabled: Boolean(projectId),
  })

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    error: summaryQueryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['results-summary', projectId],
    queryFn: () => getResultsSummary(projectId),
    enabled: Boolean(projectId),
  })

  const {
    data: deliveryPackage,
    isLoading: packageLoading,
    isError: packageError,
    error: packageQueryError,
    refetch: refetchPackage,
  } = useQuery({
    queryKey: ['delivery-package', projectId],
    queryFn: () => getDeliveryPackageOrNull(projectId),
    enabled: Boolean(projectId),
  })

  const invalidateResults = () => {
    queryClient.invalidateQueries({ queryKey: ['experiment-results', projectId] })
    queryClient.invalidateQueries({ queryKey: ['results-summary', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project-overview', projectId] })
  }

  const preparePackage = () => {
    window.open(deliveryPackageDownloadUrl(projectId), '_blank')
    showToast('Delivery package download started', 'success')
  }

  const handleInterpret = async () => {
    try {
      const response = await interpretResults(projectId)
      showToast(String(response.summary ?? 'Results interpreted'), 'success')
    } catch {
      showToast('Failed to interpret results', 'error')
    }
  }

  const showDemoPrompt =
    !resultsLoading && !resultsError && results.length === 0 && projectId !== DEMO_PROJECT_ID

  const resultsErrorMessage =
    resultsQueryError instanceof Error ? resultsQueryError.message : 'Failed to load validation readouts.'

  const summaryErrorMessage =
    summaryQueryError instanceof Error ? summaryQueryError.message : 'Failed to load results summary.'

  const packageErrorMessage =
    packageQueryError instanceof Error ? packageQueryError.message : 'Failed to load delivery package.'

  return (
    <section>
      <ProjectContextBar />
      <PageHead
        eyebrow={t.results.eyebrow}
        title={t.results.title}
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-md border border-bda-border px-3 py-2 text-sm hover:bg-bda-panel"
              onClick={() => void handleInterpret()}
            >
              {t.results.interpret}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg"
              onClick={preparePackage}
            >
              <PackageCheck className="h-4 w-4" />
              {t.results.preparePackage}
            </button>
          </div>
        }
      />

      <div className="mb-5 rounded-lg border border-bda-amber/30 bg-bda-panel p-4 text-sm text-bda-muted">
        {t.results.disclaimer}
      </div>

      {summaryError ? (
        <InlineError message={summaryErrorMessage} onRetry={() => void refetchSummary()} />
      ) : (
        <ResultsMetrics summary={summary ?? null} loading={summaryLoading} />
      )}

      <div className="mb-5 rounded-lg border border-bda-border bg-bda-panel p-4 text-sm text-bda-muted break-words">
        {summary?.experiment_summary ?? t.results.disclaimer}
      </div>

      {showDemoPrompt ? (
        <div className="mb-5 rounded-lg border border-bda-cyan/30 bg-bda-panel p-4 text-sm">
          <p className="text-bda-text">
            This project has no wet-lab readouts yet. Switch to the PD-1 demo project to explore BLI/SEC
            evidence and the delivery package.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg"
              onClick={() => setProjectId(DEMO_PROJECT_ID)}
            >
              Open PD-1 demo results
            </button>
            <Link
              to={`/results?project=${encodeURIComponent(DEMO_PROJECT_ID)}`}
              className="rounded-md border border-bda-border px-3 py-2 text-sm hover:bg-bda-panel-hover"
              onClick={() => setProjectId(DEMO_PROJECT_ID)}
            >
              View demo delivery package
            </Link>
          </div>
        </div>
      ) : null}

      <div className="mb-5">
        <ExperimentUpload projectId={projectId} onUploaded={invalidateResults} />
      </div>

      <div className="grid min-h-0 gap-4 xl:h-[calc(100vh-28rem)] xl:min-h-[28rem] xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.9fr)]">
        <div className="min-h-0">
          {resultsError ? (
            <InlineError message={resultsErrorMessage} onRetry={() => void refetchResults()} />
          ) : null}
          <ValidationTable results={results} loading={resultsLoading} isError={resultsError} />
        </div>
        <div className="min-h-0">
          {packageError ? (
            <InlineError message={packageErrorMessage} onRetry={() => void refetchPackage()} />
          ) : null}
          <DeliveryPackage
            packageData={deliveryPackage ?? null}
            loading={packageLoading}
            projectId={projectId}
          />
        </div>
      </div>
    </section>
  )
}
