import { useQuery, useQueryClient } from '@tanstack/react-query'
import { PackageCheck } from 'lucide-react'
import { listExperimentResults } from '../lib/api/experiments'
import { getDeliveryPackage, getResultsSummary } from '../lib/api/projects'
import { interpretResults } from '../lib/api/copilot'
import { deliveryPackageDownloadUrl } from '../lib/api/client'
import { PageHead } from '../components/ui/PageHead'
import { LoopStepper } from '../components/ui/LoopStepper'
import { ApiState } from '../components/ui/ApiState'
import { ResultsMetrics } from '../features/results/ResultsMetrics'
import { ValidationTable } from '../features/results/ValidationTable'
import { ExperimentUpload } from '../features/results/ExperimentUpload'
import { DeliveryPackage } from '../features/results/DeliveryPackage'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useToastStore } from '../components/ui/Toast'
import { useI18n } from '../lib/i18n'

export function ResultsPage() {
  const { t } = useI18n()
  const { projectId } = useProjectContext()
  const queryClient = useQueryClient()
  const showToast = useToastStore((s) => s.show)

  const {
    data: results = [],
    isLoading: resultsLoading,
    isError: resultsError,
    refetch: refetchResults,
  } = useQuery({
    queryKey: ['experiment-results', projectId],
    queryFn: () => listExperimentResults(projectId),
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['results-summary', projectId],
    queryFn: () => getResultsSummary(projectId),
  })

  const { data: deliveryPackage, isLoading: packageLoading } = useQuery({
    queryKey: ['delivery-package', projectId],
    queryFn: () => getDeliveryPackage(projectId),
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

  return (
    <section>
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
      <LoopStepper />

      <div className="mb-5 rounded-lg border border-bda-amber/30 bg-bda-panel p-4 text-sm text-bda-muted">
        {t.results.disclaimer}
      </div>

      <ResultsMetrics summary={summary ?? null} loading={summaryLoading} />

      <div className="mb-5 rounded-lg border border-bda-border bg-bda-panel p-4 text-sm text-bda-muted">
        {summary?.experiment_summary ?? t.results.disclaimer}
      </div>

      <div className="mb-5">
        <ExperimentUpload projectId={projectId} onUploaded={invalidateResults} />
      </div>

      <ApiState isError={resultsError} onRetry={() => void refetchResults()}>
        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <ValidationTable results={results} loading={resultsLoading} isError={resultsError} />
          <DeliveryPackage
            packageData={deliveryPackage ?? null}
            loading={packageLoading}
            projectId={projectId}
          />
        </div>
      </ApiState>
    </section>
  )
}
