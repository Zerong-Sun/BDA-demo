import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderPlus, FlaskConical, LoaderCircle } from 'lucide-react'
import { createProject } from '../../lib/api/projects'
import { useProjectContext } from '../../lib/hooks/useProjectContext'
import { useAppStore } from '../../lib/store/appStore'

interface ProjectChooserProps {
  title?: string
  description?: string
  compact?: boolean
}

export function ProjectChooser({
  title = '选择实验项目',
  description = '工作流、候选物、实验结果和交付包都必须归属于一个实验项目。',
  compact = false,
}: ProjectChooserProps) {
  const queryClient = useQueryClient()
  const { projects, projectId, setProjectId } = useProjectContext()
  const appMode = useAppStore((state) => state.appMode)
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
          已有实验项目
          <select
            aria-label="选择实验项目"
            className="rounded-md border border-bda-border bg-bda-bg px-3 py-2 text-sm text-bda-text"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
          >
            <option value="">请选择项目…</option>
            {projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.project_name} · {project.status}
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
          {appMode === 'demo' ? '演示模式只读' : '新建项目'}
        </button>
      </div>

      {creating ? (
        <div className="mt-4 grid gap-3 rounded-md border border-bda-border bg-bda-bg p-4">
          <label className="grid gap-1 text-xs text-bda-muted">
            项目名称
            <input
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：EGFR binder design"
            />
          </label>
          <label className="grid gap-1 text-xs text-bda-muted">
            项目类型
            <select
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={projectType}
              onChange={(event) => setProjectType(event.target.value)}
            >
              <option value="protein_design">蛋白质设计</option>
              <option value="binder_design">结合蛋白设计</option>
              <option value="enzyme_design">酶设计</option>
              <option value="biomaterial_design">可编程生物材料</option>
              <option value="scaffold_redesign">蛋白支架改造</option>
            </select>
          </label>
          <label className="grid gap-1 text-xs text-bda-muted">
            目标与说明
            <textarea
              rows={2}
              className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="描述靶点、设计目标和关键约束"
            />
          </label>
          <button
            type="button"
            className="inline-flex w-fit items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
            disabled={!name.trim() || create.isPending}
            onClick={() => create.mutate()}
          >
            {create.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <FolderPlus className="h-4 w-4" />}
            创建并选择
          </button>
          {create.isError ? <p className="text-xs text-bda-red">创建项目失败，请检查后端服务。</p> : null}
        </div>
      ) : null}
    </section>
  )
}
