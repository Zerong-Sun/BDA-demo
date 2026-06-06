import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, Play, Plus } from 'lucide-react'
import { WorkflowCanvas, type WorkflowCanvasHandle } from '../features/workflow/WorkflowCanvas'
import { NodeBuilder } from '../features/workflow/NodeBuilder'
import { mapApiNodesToGraph } from '../features/workflow/workflowMapper'
import { CopilotPanel } from '../features/copilot/CopilotPanel'
import { MolStarViewer } from '../features/pdb-viewer/MolStarViewer'
import { PDBFileUpload } from '../features/pdb-viewer/PDBFileUpload'
import { getLatestWorkflowRun } from '../lib/api/projects'
import { listWorkflowNodes, submitWorkflowRun } from '../lib/api/workflow'
import { useAppStore } from '../lib/store/appStore'
import { useToastStore } from '../components/ui/Toast'

export function WorkflowPage() {
  const [builderOpen, setBuilderOpen] = useState(true)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const canvasRef = useRef<WorkflowCanvasHandle>(null)
  const copilotOpen = useAppStore((s) => s.copilotOpen)
  const setCopilotOpen = useAppStore((s) => s.setCopilotOpen)
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const showToast = useToastStore((s) => s.show)
  const queryClient = useQueryClient()

  const { data: workflowRun } = useQuery({
    queryKey: ['workflow-run', activeProjectId],
    queryFn: () => getLatestWorkflowRun(activeProjectId),
  })

  const { data: workflowNodes = [] } = useQuery({
    queryKey: ['workflow-nodes', workflowRun?.workflow_run_id],
    queryFn: () => listWorkflowNodes(workflowRun!.workflow_run_id),
    enabled: Boolean(workflowRun?.workflow_run_id),
    refetchInterval: (query) => {
      const nodes = query.state.data ?? []
      return nodes.some((node) => node.status === 'running') ? 3000 : false
    },
  })

  const graph = useMemo(
    () => (workflowNodes.length > 0 ? mapApiNodesToGraph(workflowNodes) : null),
    [workflowNodes],
  )

  const startWorkflow = useMutation({
    mutationFn: () => submitWorkflowRun(workflowRun!.workflow_run_id),
    onSuccess: (response) => {
      if (response.status === 'blocked') {
        showToast(response.message ?? 'Compute not connected', 'info')
      } else {
        showToast('Workflow submitted to compute', 'success')
      }
      queryClient.invalidateQueries({ queryKey: ['workflow-nodes', workflowRun?.workflow_run_id] })
    },
    onError: () => showToast('Failed to start workflow', 'error'),
  })

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg"
          onClick={() => setBuilderOpen((v) => !v)}
        >
          <Plus className="h-4 w-4" />
          Add node
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md bg-bda-green px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
          disabled={!workflowRun || startWorkflow.isPending}
          onClick={() => startWorkflow.mutate()}
        >
          <Play className="h-4 w-4" />
          Start workflow
        </button>
        <button
          type="button"
          className="rounded-md border border-bda-border p-2 hover:bg-bda-panel"
          onClick={() => setCopilotOpen(!copilotOpen)}
          title="Toggle Copilot panel"
        >
          <MessageSquare className="h-4 w-4" />
        </button>
        {workflowRun ? (
          <span className="text-xs text-bda-muted">
            Run {workflowRun.workflow_run_id} · {workflowRun.status}
          </span>
        ) : null}
      </div>

      <NodeBuilder
        open={builderOpen}
        onClose={() => setBuilderOpen(false)}
        onAdd={(template, methods) => {
          canvasRef.current?.addNodeFromTemplate(template, methods)
          showToast(`Added ${template.title} to workflow`, 'success')
        }}
      />

      <div className="mb-4 grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <PDBFileUpload
          projectId={activeProjectId}
          onFileSelected={setUploadedFile}
        />
        <MolStarViewer file={uploadedFile} height={220} />
      </div>

      <div className={`grid gap-4 ${copilotOpen ? 'xl:grid-cols-[1fr_320px]' : ''}`}>
        <WorkflowCanvas
          ref={canvasRef}
          initialNodes={graph?.nodes}
          initialEdges={graph?.edges}
        />
        <CopilotPanel open={copilotOpen} />
      </div>
    </section>
  )
}
