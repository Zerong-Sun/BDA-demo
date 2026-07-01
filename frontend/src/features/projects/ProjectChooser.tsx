import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderPlus, FlaskConical, LoaderCircle, Trash2 } from 'lucide-react'
import { createProject } from '../../lib/api/projects'
import { useDeleteProjectLifecycle } from '../../lib/hooks/useDeleteProjectLifecycle'
import { useProjectContext } from '../../lib/hooks/useProjectContext'
import { useAppStore } from '../../lib/store/appStore'

interface ProjectChooserProps {
  title?: string
  description?: string
  compact?: boolean
}

export function ProjectChooser({
  title = 'Select a research project',
  description = 'Workflow runs, candidates, experimental results, and delivery packages must belong to a research project.',
  compact = false,
}: ProjectChooserProps) {
  const queryClient = useQueryClient()
  const { projects, projectId, setProjectId } = useProjectContext()
  const appMode = useAppStore((state) => state.appMode)
  const selectedProject = projects.find((project) => project.project_id === projectId) ?? null
  const projectDelete = useDeleteProjectLifecycle()
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [projectType, setProjectType] = useState('protein_design')
  const [summary, setSummary] = useState('')

  const create = useMutation({
    mutationFn: () =>
      createProject({
        project_name: name.trim(),
        project_type: projectType,
        summary: summary.trim() || undefined,
      }),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] })
      setProjectId(project.project_id)
      setCreating(false)
      setName('')
      setSummary('')
    },
  })
  const chooseProject = (nextProjectId: string) => {
    projectDelete.reset()
    setProjectId(nextProjectId)
  }

  const confirmDelete = () => {
    if (!selectedProject) return
    projectDelete.confirmAndDeleteProject(selectedProject)
  }

  return (
    <section className={`rounded-lg border border-bda-border bg-bda-panel ${compact ? 'p-3' : 'p-5'}`}>
      <div className="flex items-start gap-3">
        <FlaskConical className="mt-0.5 h-5 w-5 shrink-0 text-bda-cyan" />
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-bda-text">{title}</h2>
          <p className="mt-1 text-sm text-bda-muted">{description}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
        <label className="grid gap-1 text-xs text-bda-muted">
          Existing research project
          <select
            aria-label="Select research project"
            className="rounded-md border border-bda-border bg-bda-bg px-3 py-2 text-sm text-bda-text"
            value={projectId}
            onChange={(event) => chooseProject(event.target.value)}
          >
            <option value="">Select a project...</option>
            {projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.project_name} · {project.status} · {project.local_workspace?.status ?? 'local pending'}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 self-end rounded-md border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50"
          disabled={appMode === 'demo'}
          onClick={() => setCreating((value) => !value)}
        >
          <FolderPlus className="h-4 w-4" />
          {appMode === 'demo' ? 'Read-only demo' : 'Create project'}
        </button>
      </div>
      {selectedProject ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-bda-border bg-bda-bg px-3 py-2 text-xs text-bda-muted">
          <span className="min-w-0 truncate">
            Local workspace: {selectedProject.local_workspace?.root ?? 'pending'}
          </span>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded border border-bda-red/40 px-2 py-1 text-bda-red hover:bg-bda-red/10 disabled:opacity-50"
            disabled={appMode === 'demo' || projectDelete.isPending}
            onClick={confirmDelete}
          >
            {projectDelete.isPending && projectDelete.deletingProjectId === selectedProject.project_id ? (
              <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
            Move to trash
          </button>
        </div>
      ) : null}
      {projectDelete.isSuccess ? (
        <p className="mt-2 text-xs text-bda-muted">
          Project moved to {projectDelete.data.workspace.trash_root ?? 'project trash'}.
        </p>
      ) : null}
      {projectDelete.isError ? (
        <p className="mt-2 text-xs text-bda-red">
          {projectDelete.error instanceof Error ? projectDelete.error.message : 'Project deletion failed. Check the backend service.'}
        </p>
      ) : null}

      {creating ? (
        <div className="mt-4 grid gap-3 rounded-md border border-bda-border bg-bda-bg p-4">
          <label className="grid gap-1 text-xs text-bda-muted">
            Project name
            <input
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Example: EGFR binder design"
            />
          </label>
          <label className="grid gap-1 text-xs text-bda-muted">
            Project type
            <select
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={projectType}
              onChange={(event) => setProjectType(event.target.value)}
            >
              <option value="protein_design">Protein design</option>
              <option value="sweet_protein_design">Sweet-protein design</option>
              <option value="binder_design">Binder design</option>
              <option value="enzyme_design">Enzyme design</option>
              <option value="biomaterial_design">Programmable biomaterials</option>
              <option value="scaffold_redesign">Scaffold redesign</option>
            </select>
          </label>
          <label className="grid gap-1 text-xs text-bda-muted">
            Objective and constraints
            <textarea
              rows={2}
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="Describe the target, design objective, and key constraints"
            />
          </label>
          <button
            type="button"
            className="inline-flex w-fit items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
            disabled={!name.trim() || create.isPending}
            onClick={() => create.mutate()}
          >
            {create.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <FolderPlus className="h-4 w-4" />}
            Create and select
          </button>
          {create.isError ? (
            <p className="text-xs text-bda-red">
              {create.error instanceof Error ? create.error.message : 'Project creation failed. Check the backend service.'}
            </p>
          ) : null}
          {create.isSuccess && create.data.local_workspace ? (
            <p className="text-xs text-bda-muted">
              Local workspace ready at {create.data.local_workspace.root}. Cloud sync is {create.data.cloud_sync?.status ?? 'not configured'}.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
