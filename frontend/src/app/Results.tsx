import { useQuery, useQueryClient } from '@tanstack/react-query'
import { PackageCheck } from 'lucide-react'
import { listExperimentResults } from '../lib/api/experiments'
import { getDeliveryPackage, getResultsSummary } from '../lib/api/projects'
import { PageHead } from '../components/ui/PageHead'
import { ResultsMetrics } from '../features/results/ResultsMetrics'
import { ValidationTable } from '../features/results/ValidationTable'
import { ExperimentUpload } from '../features/results/ExperimentUpload'
import { DeliveryPackage } from '../features/results/DeliveryPackage'
import { useAppStore } from '../lib/store/appStore'
import { useToastStore } from '../components/ui/Toast'

export function ResultsPage() {
  const projectId = useAppStore((s) => s.activeProjectId)
  const queryClient = useQueryClient()
  const showToast = useToastStore((s) => s.show)

  const {
    data: results = [],
    isLoading: resultsLoading,
    isError: resultsError,
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
  }

  return (
    <section>
      <PageHead
        eyebrow="Closed-loop evidence"
        title="Results and delivery"
        actions={
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg"
            onClick={() => showToast('Delivery package queued (demo)', 'success')}
          >
            <PackageCheck className="h-4 w-4" />
            Prepare package
          </button>
        }
      />

      <ResultsMetrics summary={summary ?? null} loading={summaryLoading} />

      <div className="mb-5 rounded-lg border border-bda-border bg-bda-panel p-4 text-sm text-bda-muted">
        {summary?.experiment_summary ??
          'BDA validated this route: AI-generated binders produced measurable wet-lab hits, but stronger developability constraints are needed before scaling to larger experimental batches.'}
      </div>

      <div className="mb-5">
        <ExperimentUpload projectId={projectId} onUploaded={invalidateResults} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <ValidationTable results={results} loading={resultsLoading} isError={resultsError} />
        <DeliveryPackage packageData={deliveryPackage ?? null} loading={packageLoading} />
      </div>
    </section>
  )
}
