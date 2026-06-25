import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, LoaderCircle, Play, Search, X } from 'lucide-react'

import {
  createResearchBrief,
  createResearchRun,
  compareResearchSequences,
  compareResearchStructures,
  createLiteratureSubscription,
  detectLiteratureRelations,
  generateResearchPlan,
  getResearchBrief,
  getResearchRun,
  ingestLiterature,
  ingestResearchMarkdown,
  listLiteratureClaims,
  listLiteratureRelations,
  listLiteratureSubscriptions,
  listResearchBriefs,
  listNotifications,
  materializeWorkflowPlan,
  reviewResearchEvidence,
  startResearchRun,
  downloadResearchDossier,
  reviewLiteratureClaim,
  reviewLiteratureRelation,
  runLiteratureSubscription,
  searchLiteratureLibrary,
  updateLiteratureSubscription,
  type ResearchRun,
  type SequenceComparison,
  type StructureComparison,
  type WorkflowPlan,
} from '../lib/api/copilot'
import { listProjectArtifacts } from '../lib/api/artifacts'
import {
  createCampaign,
  evaluateCampaignRound,
  getCampaign,
  listProjectCampaigns,
  reviewCampaignDecision,
  updateCampaignDecision,
  type Campaign,
} from '../lib/api/campaigns'
import { useProjectContext } from '../lib/hooks/useProjectContext'

function text(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function currentRole() {
  try {
    const raw = sessionStorage.getItem('bda_user')
    return raw ? text((JSON.parse(raw) as { role?: unknown }).role) : ''
  } catch {
    return ''
  }
}

function DecisionReview({
  decisionId,
  roundNumber,
  patch,
  onSave,
  onReview,
  saving,
}: {
  decisionId: string
  roundNumber: number
  patch: unknown
  onSave: (id: string, patch: Record<string, unknown>) => Promise<unknown>
  onReview: (id: string, approve: boolean) => void
  saving: boolean
}) {
  const initial = JSON.stringify(patch ?? { models: {} }, null, 2)
  const [draft, setDraft] = useState(initial)
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState('')

  const save = async () => {
    try {
      const parsed = JSON.parse(draft) as Record<string, unknown>
      await onSave(decisionId, parsed)
      setDirty(false)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Invalid parameter patch')
    }
  }

  return (
    <div className="mt-3 space-y-2">
      <textarea
        aria-label={`Round ${roundNumber} parameter patch`}
        className="min-h-28 w-full rounded border border-bda-border bg-bda-bg p-2 font-mono text-xs"
        value={draft}
        onChange={(event) => {
          setDraft(event.target.value)
          setDirty(true)
          setError('')
        }}
      />
      {error ? <p className="text-xs text-bda-red">{error}</p> : null}
      <div className="flex flex-wrap gap-2">
        <button
          className="rounded border border-bda-border px-3 py-1.5 text-sm disabled:opacity-50"
          disabled={!dirty || saving}
          onClick={() => void save()}
        >
          保存 Patch
        </button>
        <button
          className="rounded bg-bda-green px-3 py-1.5 text-sm text-bda-bg disabled:opacity-50"
          disabled={dirty || saving}
          onClick={() => onReview(decisionId, true)}
        >
          批准并创建下一轮
        </button>
        <button
          className="rounded border border-bda-red px-3 py-1.5 text-sm text-bda-red"
          onClick={() => onReview(decisionId, false)}
        >
          拒绝
        </button>
      </div>
    </div>
  )
}

function LiteraturePanel() {
  const client = useQueryClient()
  const isAdmin = currentRole() === 'admin'
  const [query, setQuery] = useState('protein binder design')
  const claims = useQuery({ queryKey: ['literature-claims'], queryFn: () => listLiteratureClaims() })
  const relations = useQuery({ queryKey: ['literature-relations'], queryFn: () => listLiteratureRelations() })
  const subscriptions = useQuery({
    queryKey: ['literature-subscriptions'],
    queryFn: listLiteratureSubscriptions,
    retry: false,
    enabled: isAdmin,
  })
  const search = useQuery({
    queryKey: ['literature-search', query],
    queryFn: () => searchLiteratureLibrary(query),
    enabled: false,
  })
  const ingest = useMutation({
    mutationFn: () => ingestLiterature(query),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['literature-claims'] })
      search.refetch()
    },
  })
  const reviewClaim = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'accepted' | 'rejected' }) =>
      reviewLiteratureClaim(id, status),
    onSuccess: () => client.invalidateQueries({ queryKey: ['literature-claims'] }),
  })
  const reviewRelation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'accepted' | 'rejected' }) =>
      reviewLiteratureRelation(id, status),
    onSuccess: () => client.invalidateQueries({ queryKey: ['literature-relations'] }),
  })
  const detectRelations = useMutation({
    mutationFn: () => detectLiteratureRelations(false),
    onSuccess: () => client.invalidateQueries({ queryKey: ['literature-relations'] }),
  })
  const createSubscription = useMutation({
    mutationFn: () => createLiteratureSubscription({
      name: query,
      query,
      enabled: true,
      interval_hours: 24,
      result_limit: 5,
      fetch_full_text: true,
      extract_claims: true,
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['literature-subscriptions'] }),
  })
  const runSubscription = useMutation({
    mutationFn: runLiteratureSubscription,
    onSuccess: () => client.invalidateQueries({ queryKey: ['literature-subscriptions'] }),
  })
  const toggleSubscription = useMutation({
    mutationFn: (item: NonNullable<typeof subscriptions.data>['items'][number]) =>
      updateLiteratureSubscription(item.subscription_id, {
        name: item.name,
        query: item.query,
        enabled: !item.enabled,
        interval_hours: item.interval_hours,
        result_limit: item.result_limit,
        fetch_full_text: item.fetch_full_text,
        extract_claims: item.extract_claims,
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['literature-subscriptions'] }),
  })

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-bda-border bg-bda-panel p-4">
        <h2 className="font-semibold">文献摄取与自动订阅</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <input className="min-w-72 flex-1 rounded border border-bda-border bg-bda-bg px-3 py-2 text-sm" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="rounded border border-bda-border px-3 py-2 text-sm" onClick={() => search.refetch()}><Search className="mr-1 inline h-4 w-4" />检索本地库</button>
          <button className="rounded bg-bda-cyan px-3 py-2 text-sm text-bda-bg disabled:opacity-50" disabled={!isAdmin || ingest.isPending} onClick={() => ingest.mutate()}>
            {ingest.isPending ? <LoaderCircle className="mr-1 inline h-4 w-4 animate-spin" /> : null}立即摄取
          </button>
          <button className="rounded border border-bda-border px-3 py-2 text-sm disabled:opacity-50" disabled={!isAdmin} onClick={() => createSubscription.mutate()}>每日自动阅读</button>
        </div>
        {!isAdmin ? <p className="mt-2 text-xs text-bda-muted">摄取、自动订阅和关系检测需要管理员权限；研究员仍可检索并审核证据。</p> : null}
        {ingest.isError || createSubscription.isError ? (
          <p className="mt-2 text-xs text-bda-red">文献任务失败，请检查权限、网络和模型配置。</p>
        ) : null}
        {search.data?.items.map((item, index) => (
          <div key={`${text(item.document_id)}-${index}`} className="mt-3 rounded border border-bda-border p-3 text-sm">
            <strong>{text(item.title)}</strong>
            <p className="mt-1 text-bda-muted">{text(item.statement) || text(item.abstract_text)}</p>
            <p className="mt-1 text-xs text-bda-cyan">{text(item.doi) || text(item.pmid)}</p>
          </div>
        ))}
        {subscriptions.data?.items.map((item) => (
          <div key={item.subscription_id} className="mt-3 flex items-center justify-between rounded border border-bda-border p-3 text-sm">
            <div><strong>{item.name}</strong><p className="text-xs text-bda-muted">每 {item.interval_hours} 小时 · 下次 {item.next_run_at}</p></div>
            <div className="flex gap-2">
              <button className="rounded border border-bda-border px-2 py-1 text-xs" onClick={() => toggleSubscription.mutate(item)}>{item.enabled ? '暂停' : '启用'}</button>
              <button className="rounded border border-bda-border px-2 py-1 text-xs" onClick={() => runSubscription.mutate(item.subscription_id)}><Play className="mr-1 inline h-3 w-3" />运行</button>
            </div>
          </div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-bda-border bg-bda-panel p-4">
          <h2 className="font-semibold">待审核科学主张</h2>
          {claims.data?.items.map((item) => (
            <article key={text(item.claim_id)} className="mt-3 rounded border border-bda-border p-3 text-sm">
              <strong>{text(item.title)}</strong>
              <p className="mt-1">{text(item.statement)}</p>
              <blockquote className="mt-2 border-l-2 border-bda-cyan pl-2 text-xs text-bda-muted">{text(item.evidence_excerpt)}</blockquote>
              <div className="mt-2 flex gap-2">
                <button className="text-bda-green" onClick={() => reviewClaim.mutate({ id: text(item.claim_id), status: 'accepted' })}><Check className="inline h-4 w-4" /> 接受</button>
                <button className="text-bda-red" onClick={() => reviewClaim.mutate({ id: text(item.claim_id), status: 'rejected' })}><X className="inline h-4 w-4" /> 拒绝</button>
              </div>
            </article>
          ))}
        </div>
        <div className="rounded-lg border border-bda-border bg-bda-panel p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">待审核主张关系</h2>
            <button className="rounded border border-bda-border px-2 py-1 text-xs disabled:opacity-50" disabled={!isAdmin || detectRelations.isPending} onClick={() => detectRelations.mutate()}>
              检测关系
            </button>
          </div>
          {relations.data?.items.map((item) => (
            <article key={text(item.relation_id)} className="mt-3 rounded border border-bda-border p-3 text-sm">
              <span className="text-xs uppercase text-bda-cyan">{text(item.relation_type)}</span>
              <p>{text(item.source_statement)}</p><p className="text-bda-muted">↔ {text(item.target_statement)}</p>
              <div className="mt-2 flex gap-2">
                <button className="text-bda-green" onClick={() => reviewRelation.mutate({ id: text(item.relation_id), status: 'accepted' })}>接受</button>
                <button className="text-bda-red" onClick={() => reviewRelation.mutate({ id: text(item.relation_id), status: 'rejected' })}>拒绝</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function CampaignPanel() {
  const client = useQueryClient()
  const { projectId } = useProjectContext()
  const campaigns = useQuery({
    queryKey: ['campaigns', projectId],
    queryFn: () => listProjectCampaigns(projectId),
    enabled: Boolean(projectId),
  })
  const [selected, setSelected] = useState('')
  const detail = useQuery({
    queryKey: ['campaign', selected],
    queryFn: () => getCampaign(selected),
    enabled: Boolean(selected),
    refetchInterval: 5000,
  })
  const create = useMutation({
    mutationFn: () => createCampaign({
      project_id: projectId,
      name: 'Protein design optimization',
      objective: 'Iteratively improve structure, developability, and experimental validation metrics.',
      max_rounds: 3,
      stop_conditions: [{ metric: 'experiments.bli.pass_rate', operator: '>=', value: 0.5, required: true }],
    }),
    onSuccess: (item) => {
      setSelected(item.campaign_id)
      client.invalidateQueries({ queryKey: ['campaigns', projectId] })
    },
  })
  const evaluate = useMutation({
    mutationFn: ({ id, round }: { id: string; round: number }) => evaluateCampaignRound(id, round),
    onSuccess: () => client.invalidateQueries({ queryKey: ['campaign', selected] }),
  })
  const review = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) => reviewCampaignDecision(id, approve),
    onSuccess: () => client.invalidateQueries({ queryKey: ['campaign', selected] }),
  })
  const updateDecision = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Record<string, unknown> }) =>
      updateCampaignDecision(id, patch, 'Reviewed in Research workspace.'),
    onSuccess: () => client.invalidateQueries({ queryKey: ['campaign', selected] }),
  })

  const campaign = detail.data as Campaign | undefined
  const actionError = create.error || evaluate.error || review.error || updateDecision.error
  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <aside className="rounded-lg border border-bda-border bg-bda-panel p-4">
        <button className="w-full rounded bg-bda-cyan px-3 py-2 text-sm text-bda-bg" disabled={!projectId || create.isPending} onClick={() => create.mutate()}>新建闭环 Campaign</button>
        {campaigns.data?.items.map((item) => (
          <button key={item.campaign_id} className="mt-3 w-full rounded border border-bda-border p-3 text-left" onClick={() => setSelected(item.campaign_id)}>
            <strong>{item.name}</strong><p className="text-xs text-bda-muted">Round {item.current_round}/{item.max_rounds} · {item.status}</p>
          </button>
        ))}
      </aside>
      <section className="rounded-lg border border-bda-border bg-bda-panel p-4">
        {actionError ? <p className="mb-3 rounded border border-bda-red/40 p-2 text-sm text-bda-red">{actionError.message}</p> : null}
        {!campaign ? <p className="text-bda-muted">选择或创建一个 Campaign。</p> : (
          <>
            <h2 className="text-lg font-semibold">{campaign.name}</h2>
            <p className="text-sm text-bda-muted">{campaign.objective}</p>
            {campaign.rounds?.map((round) => {
              const decision = round.decisions?.[0]
              const decisionId = decision ? text(decision.decision_id) : ''
              const patch = decision?.parameter_patch_json
              return (
                <article key={round.campaign_round_id} className="mt-4 rounded border border-bda-border p-4">
                  <div className="flex justify-between"><strong>Round {round.round_number}</strong><span className="text-xs text-bda-cyan">{round.status} · {round.approval_status}</span></div>
                  <p className="mt-1 text-xs text-bda-muted">Workflow: {round.workflow_run_id}</p>
                  {round.status === 'ready_for_evaluation' || round.status === 'active' ? (
                    <button className="mt-3 rounded border border-bda-border px-3 py-1.5 text-sm" onClick={() => evaluate.mutate({ id: campaign.campaign_id, round: round.round_number })}>评价本轮</button>
                  ) : null}
                  {decisionId && text(decision?.status) === 'proposed' ? (
                    <DecisionReview
                      decisionId={decisionId}
                      roundNumber={round.round_number}
                      patch={patch}
                      saving={updateDecision.isPending}
                      onSave={(id, nextPatch) => updateDecision.mutateAsync({ id, patch: nextPatch })}
                      onReview={(id, approve) => review.mutate({ id, approve })}
                    />
                  ) : null}
                </article>
              )
            })}
          </>
        )}
      </section>
    </div>
  )
}

function SweetProteinBuilder() {
  const { projectId } = useProjectContext()
  const client = useQueryClient()
  const [objective, setObjective] = useState(
    '设计一个适合饮料应用的 AI 甜味蛋白；比较 single-chain monellin、brazzein 与 de novo 路线，并生成可审核的计算和实验 workflow。',
  )
  const [plan, setPlan] = useState<WorkflowPlan | null>(null)
  const [selectedRoute, setSelectedRoute] = useState('monellin_redesign')
  const [sourceFile, setSourceFile] = useState<File | null>(null)
  const [sourceSummary, setSourceSummary] = useState('')
  const [researchRun, setResearchRun] = useState<ResearchRun | null>(null)
  const [dossierTab, setDossierTab] = useState<'evidence' | 'scaffolds' | 'comparison' | 'workflow' | 'risks'>('evidence')
  const [sequenceInput, setSequenceInput] = useState(
    'reference|ACDEFGHIKLMNPQRSTVWY\ncandidate|ACDEYGHIKLMNPQRSTVWY',
  )
  const [sequenceComparison, setSequenceComparison] = useState<SequenceComparison | null>(null)
  const [structureComparison, setStructureComparison] = useState<StructureComparison | null>(null)
  const [selectedStructureIds, setSelectedStructureIds] = useState<string[]>([])
  const [builderStage, setBuilderStage] = useState('')
  const applyPlan = (generated: WorkflowPlan) => {
    setPlan(generated)
    setSelectedRoute(generated.selected_route ?? 'monellin_redesign')
  }
  const briefs = useQuery({
    queryKey: ['research-briefs', projectId],
    queryFn: () => listResearchBriefs(projectId),
    enabled: Boolean(projectId),
  })
  const notifications = useQuery({
    queryKey: ['notifications', projectId],
    queryFn: () => listNotifications(projectId),
    enabled: Boolean(projectId),
    refetchInterval: 5000,
  })
  const artifacts = useQuery({
    queryKey: ['artifacts', projectId],
    queryFn: () => listProjectArtifacts(projectId),
    enabled: Boolean(projectId),
  })
  const create = useMutation({
    mutationFn: async () => {
      setBuilderStage('创建 Research Brief')
      const brief = await createResearchBrief({
        project_id: projectId,
        title: 'AI 甜味蛋白研发',
        objective,
        product_context: 'food_ingredient',
        constraints: {
          first_application: 'beverage',
          receptor_species: 'human',
          require_node_confirmation: true,
        },
        source_material: [{
          title: 'AI甜味蛋白_天然骨架_受体机制_计算设计与实验验证_2026-06-20',
          kind: 'markdown_research_seed',
          reference_count: 35,
        }],
      })
      let ingested: { chunk_count: number; reference_count: number } | null = null
      if (sourceFile) {
        setBuilderStage('摄取参考资料')
        ingested = await ingestResearchMarkdown(brief.research_brief_id, {
          title: sourceFile.name,
          content: await sourceFile.text(),
          source_uri: `upload://${sourceFile.name}`,
        })
      }
      setBuilderStage('生成问题树')
      const run = await createResearchRun(brief.research_brief_id)
      setBuilderStage('执行多源检索与证据综合')
      const completedRun = await startResearchRun(run.research_run_id)
      setBuilderStage('生成证据驱动路线')
      const generated = await generateResearchPlan(brief.research_brief_id)
      return { generated, ingested, completedRun }
    },
    onSuccess: ({ generated, ingested, completedRun }) => {
      if (ingested) {
        setSourceSummary(`已摄取 ${ingested.chunk_count} 个章节块、${ingested.reference_count} 个引用链接`)
      }
      setResearchRun(completedRun)
      applyPlan(generated)
      setBuilderStage('')
      client.invalidateQueries({ queryKey: ['research-briefs', projectId] })
    },
    onError: () => {
      setBuilderStage('')
      client.invalidateQueries({ queryKey: ['research-briefs', projectId] })
    },
  })
  const resume = useMutation({
    mutationFn: async () => {
      const latest = briefs.data?.items[0]
      if (!latest) throw new Error('No saved Research Brief')
      setBuilderStage('恢复已保存的 Research Brief')
      const detail = await getResearchBrief(latest.research_brief_id)
      const previousRun = detail.research_runs[0]
      let completedRun: ResearchRun
      if (previousRun?.status === 'completed' || previousRun?.status === 'partial') {
        completedRun = await getResearchRun(previousRun.research_run_id)
      } else if (previousRun?.research_run_id) {
        setBuilderStage('继续未完成的多源检索')
        completedRun = await startResearchRun(previousRun.research_run_id)
      } else {
        setBuilderStage('创建并执行 Research Run')
        const run = await createResearchRun(latest.research_brief_id)
        completedRun = await startResearchRun(run.research_run_id)
      }
      setBuilderStage('重新生成证据驱动路线')
      const generated = await generateResearchPlan(latest.research_brief_id)
      return { generated, completedRun }
    },
    onSuccess: ({ generated, completedRun }) => {
      setResearchRun(completedRun)
      applyPlan(generated)
      setBuilderStage('')
    },
    onError: () => setBuilderStage(''),
  })
  const changeRoute = useMutation({
    mutationFn: (routeId: string) => {
      if (!plan) throw new Error('No workflow plan')
      return generateResearchPlan(plan.research_brief_id, routeId)
    },
    onSuccess: applyPlan,
  })
  const materialize = useMutation({
    mutationFn: () => {
      if (!plan) throw new Error('No workflow plan')
      return materializeWorkflowPlan(plan.workflow_plan_id, selectedRoute)
    },
    onSuccess: (result) => {
      setPlan((current) => current ? {
        ...current,
        selected_route: result.selected_route,
        materialized_workflow_run_id: result.workflow_run_id,
        status: 'materialized',
      } : current)
    },
  })
  const reviewEvidence = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'accepted' | 'rejected' }) =>
      reviewResearchEvidence(id, status),
    onSuccess: (updated) => {
      setResearchRun((current) => current ? {
        ...current,
        evidence: current.evidence.map((item) =>
          item.evidence_link_id === updated.evidence_link_id ? updated : item),
      } : current)
    },
  })
  const compareSequences = useMutation({
    mutationFn: () => {
      if (!plan) throw new Error('No research brief')
      const sequences = sequenceInput.split('\n').map((line) => {
        const [name, ...sequence] = line.split('|')
        return { name: name.trim(), sequence: sequence.join('|').trim() }
      }).filter((item) => item.name && item.sequence)
      if (sequences.length < 2) throw new Error('至少输入两行 name|SEQUENCE')
      return compareResearchSequences(plan.research_brief_id, sequences)
    },
    onSuccess: setSequenceComparison,
  })
  const compareStructures = useMutation({
    mutationFn: () => {
      if (!plan) throw new Error('No research brief')
      if (selectedStructureIds.length < 2) throw new Error('至少选择两个 PDB artifact')
      return compareResearchStructures(plan.research_brief_id, selectedStructureIds)
    },
    onSuccess: setStructureComparison,
  })
  const actionError = create.error || materialize.error || compareSequences.error || compareStructures.error

  return (
    <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <aside className="space-y-4 rounded-lg border border-bda-border bg-bda-panel p-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-bda-cyan">Research brief</p>
          <h2 className="font-semibold">甜味蛋白 Research Builder</h2>
        </div>
        <textarea
          className="min-h-40 w-full rounded border border-bda-border bg-bda-bg p-3 text-sm"
          value={objective}
          onChange={(event) => setObjective(event.target.value)}
        />
        <select
          className="w-full rounded border border-bda-border bg-bda-bg px-3 py-2 text-sm"
          value={selectedRoute}
          onChange={(event) => setSelectedRoute(event.target.value)}
        >
          <option value="monellin_redesign">Single-chain monellin 定向改造</option>
          <option value="brazzein_redesign">Brazzein-53/54 定向改造</option>
          <option value="ph_responsive_research">pH-responsive 研究路线</option>
          <option value="de_novo_binder">De novo 受体 binder（高风险）</option>
        </select>
        <label className="block rounded border border-dashed border-bda-border p-3 text-xs text-bda-muted">
          <span className="block font-medium text-bda-text">参考资料 Markdown</span>
          <input
            className="mt-2 block w-full text-xs"
            type="file"
            accept=".md,text/markdown,text/plain"
            onChange={(event) => {
              setSourceFile(event.target.files?.[0] ?? null)
              setSourceSummary('')
            }}
          />
          <span className="mt-1 block">
            {sourceFile ? sourceFile.name : '可上传已有研究资料；系统将按章节切块并提取引用。'}
          </span>
        </label>
        <button
          className="w-full rounded bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
          disabled={!projectId || objective.trim().length < 10 || create.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? <LoaderCircle className="mr-1 inline h-4 w-4 animate-spin" /> : null}
          建立 dossier 与路线
        </button>
        {briefs.data?.items.length ? (
          <button
            className="w-full rounded border border-bda-border px-3 py-2 text-sm disabled:opacity-50"
            disabled={create.isPending || resume.isPending}
            onClick={() => resume.mutate()}
          >
            继续最近一次 Brief
          </button>
        ) : null}
        {builderStage ? (
          <p className="rounded border border-bda-cyan/40 bg-bda-cyan/10 p-2 text-xs text-bda-cyan">
            {builderStage}；外部数据库与 LLM 综合可能需要约 1–2 分钟。
          </p>
        ) : null}
        <div className="border-t border-bda-border pt-3">
          <p className="text-xs text-bda-muted">当前项目 Brief：{briefs.data?.total ?? 0}</p>
          <p className="mt-1 text-xs text-bda-muted">
            内置资料作为 research seed；FDA 状态、近期结构和预印本仍进入待核验队列。
          </p>
          {sourceSummary ? <p className="mt-2 text-xs text-bda-green">{sourceSummary}</p> : null}
          {notifications.data?.items.slice(0, 3).map((item, index) => (
            <div key={`${text(item.notification_id)}-${index}`} className="mt-2 rounded border border-bda-border p-2 text-xs">
              <strong>{text(item.title)}</strong>
              <p className="text-bda-muted">{text(item.message)}</p>
            </div>
          ))}
        </div>
      </aside>

      <section className="space-y-4">
        {actionError || resume.error ? <p className="rounded border border-bda-red/40 p-3 text-sm text-bda-red">{(actionError || resume.error)?.message}</p> : null}
        {!plan ? (
          <div className="rounded-lg border border-dashed border-bda-border bg-bda-panel p-8 text-center text-sm text-bda-muted">
            输入目标后，系统会生成骨架比较、证据边界、实验 gates 和可物化 workflow。
          </div>
        ) : (
          <>
            <div className="rounded-lg border border-bda-border bg-bda-panel p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-xs uppercase tracking-wide text-bda-cyan">Research dossier</p>
                  <h2 className="font-semibold">证据、骨架与风险 · v{plan.version ?? 1}</h2>
                  <p className="mt-1 text-xs text-bda-muted">
                    规划模式：{text((plan.dossier_json.planning_provenance as Record<string, unknown> | undefined)?.mode) || 'deterministic_fallback'}
                    {plan.dossier_json.planning_summary ? ` · ${text(plan.dossier_json.planning_summary)}` : ''}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button className="rounded border border-bda-border px-2 py-1 text-xs" onClick={() => void downloadResearchDossier(plan.research_brief_id, 'markdown')}>导出 Markdown</button>
                  <button className="rounded border border-bda-border px-2 py-1 text-xs" onClick={() => void downloadResearchDossier(plan.research_brief_id, 'json')}>导出 JSON</button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(['evidence', 'scaffolds', 'comparison', 'workflow', 'risks'] as const).map((item) => (
                  <button
                    key={item}
                    className={`rounded px-2 py-1 text-xs ${dossierTab === item ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`}
                    onClick={() => setDossierTab(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
              {dossierTab === 'evidence' ? (
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-bda-muted">
                    Research run: {researchRun?.status ?? 'not started'} · evidence {researchRun?.evidence.length ?? 0}
                  </p>
                  {researchRun?.evidence.slice(0, 30).map((item) => (
                    <article key={item.evidence_link_id} className="rounded border border-bda-border p-3 text-sm">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[10px] uppercase text-bda-cyan">{item.source_type} · {item.evidence_level}</span>
                          <h3 className="font-medium">{item.title}</h3>
                        </div>
                        <span className="text-xs text-bda-muted">{item.review_status}</span>
                      </div>
                      {item.evidence_excerpt ? <p className="mt-2 line-clamp-3 text-xs text-bda-muted">{item.evidence_excerpt}</p> : null}
                      <div className="mt-2 flex gap-3 text-xs">
                        {item.uri ? <a className="text-bda-cyan" href={item.uri} target="_blank" rel="noreferrer">Source</a> : null}
                        <button className="text-bda-green" onClick={() => reviewEvidence.mutate({ id: item.evidence_link_id, status: 'accepted' })}>Accept</button>
                        <button className="text-bda-red" onClick={() => reviewEvidence.mutate({ id: item.evidence_link_id, status: 'rejected' })}>Reject</button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : dossierTab === 'scaffolds' ? (
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  {((plan.dossier_json.scaffolds as Array<Record<string, unknown>>) ?? []).map((item) => (
                    <article key={text(item.id)} className="rounded border border-bda-border p-3 text-sm">
                      <strong>{text(item.name)}</strong>
                      <p className="mt-1 text-xs text-bda-muted">Focus: {Array.isArray(item.design_focus) ? item.design_focus.join(', ') : ''}</p>
                      <p className="mt-1 text-xs text-bda-amber">Risks: {Array.isArray(item.risks) ? item.risks.join(', ') : ''}</p>
                    </article>
                  ))}
                </div>
              ) : dossierTab === 'comparison' ? (
                <div className="mt-3 grid gap-4 lg:grid-cols-2">
                  <div className="rounded border border-bda-border p-3">
                    <h3 className="text-sm font-medium">序列全局比对</h3>
                    <p className="mt-1 text-xs text-bda-muted">每行使用 name|SEQUENCE；第一行为参考序列。</p>
                    <textarea
                      className="mt-2 min-h-28 w-full rounded border border-bda-border bg-bda-bg p-2 font-mono text-xs"
                      value={sequenceInput}
                      onChange={(event) => setSequenceInput(event.target.value)}
                    />
                    <button className="mt-2 rounded border border-bda-border px-2 py-1 text-xs disabled:opacity-40" disabled={compareSequences.isPending} onClick={() => compareSequences.mutate()}>
                      运行序列比对
                    </button>
                    {sequenceComparison ? (
                      <div className="mt-3 space-y-2 text-xs">
                        {sequenceComparison.alignments.map((item) => (
                          <div key={item.query} className="rounded bg-bda-bg p-2">
                            <strong>{item.query}</strong> · identity {(item.identity * 100).toFixed(1)}% · coverage {(item.coverage * 100).toFixed(1)}%
                            <pre className="mt-1 overflow-auto font-mono text-[10px] text-bda-muted">{item.aligned_reference}{'\n'}{item.aligned_query}</pre>
                          </div>
                        ))}
                        <p className="text-bda-muted">保守参考位点：{sequenceComparison.conserved_reference_positions.join(', ') || '无'}</p>
                      </div>
                    ) : null}
                  </div>
                  <div className="rounded border border-bda-border p-3">
                    <h3 className="text-sm font-medium">结构叠合</h3>
                    <p className="mt-1 text-xs text-bda-muted">选择项目中的 PDB；第一项作为参考，按 CA 文件顺序计算 Kabsch RMSD。</p>
                    <div className="mt-2 max-h-36 space-y-1 overflow-auto">
                      {(artifacts.data ?? []).filter((item) => item.format === 'pdb').map((item) => (
                        <label key={item.artifact_id} className="flex items-center gap-2 text-xs">
                          <input
                            type="checkbox"
                            checked={selectedStructureIds.includes(item.artifact_id)}
                            onChange={(event) => setSelectedStructureIds((current) =>
                              event.target.checked
                                ? [...current, item.artifact_id]
                                : current.filter((id) => id !== item.artifact_id))}
                          />
                          {item.display_name}
                        </label>
                      ))}
                    </div>
                    <button className="mt-2 rounded border border-bda-border px-2 py-1 text-xs disabled:opacity-40" disabled={compareStructures.isPending || selectedStructureIds.length < 2} onClick={() => compareStructures.mutate()}>
                      运行结构叠合
                    </button>
                    {structureComparison ? (
                      <div className="mt-3 space-y-2 text-xs">
                        {structureComparison.comparisons.map((item) => (
                          <p key={item.query_artifact_id} className="rounded bg-bda-bg p-2">
                            {item.reference_name} ↔ {item.query_name}: RMSD {item.ca_rmsd.toFixed(3)} Å · coverage {(item.coverage * 100).toFixed(1)}%
                          </p>
                        ))}
                        <p className="text-bda-muted">{structureComparison.note}</p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : dossierTab === 'workflow' ? (
                <ol className="mt-3 space-y-2 text-sm">
                  {plan.nodes_json.map((node, index) => (
                    <li key={`${text(node.key)}-${index}`} className="rounded border border-bda-border p-2">
                      {index + 1}. {text(node.name)}
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                  <div className="space-y-2 text-sm text-bda-muted">
                    <h3 className="font-medium text-bda-text">待核验事项</h3>
                  {((plan.dossier_json.verification_queue as string[]) ?? []).map((item) => (
                    <p key={item} className="rounded border border-bda-border p-2">{item}</p>
                  ))}
                  </div>
                  <div className="space-y-2 text-sm text-bda-muted">
                    <h3 className="font-medium text-bda-text">风险与缓解</h3>
                    {((plan.dossier_json.risks as Array<Record<string, unknown>>) ?? []).map((item, index) => (
                      <div key={`${text(item.risk)}-${index}`} className="rounded border border-bda-border p-2">
                        <strong className="text-bda-text">{text(item.risk)}</strong>
                        <p>{text(item.severity)} · {text(item.mitigation)}</p>
                        {item.gate ? <p className="text-bda-cyan">Gate: {text(item.gate)}</p> : null}
                      </div>
                    ))}
                    <h3 className="pt-2 font-medium text-bda-text">成功标准</h3>
                    {((plan.dossier_json.success_criteria as Array<Record<string, unknown>>) ?? []).map((item, index) => (
                      <div key={`${text(item.stage)}-${index}`} className="rounded border border-bda-border p-2">
                        <strong className="text-bda-text">{text(item.stage)}</strong>
                        <p>{text(item.criterion)}</p>
                        <p className="text-bda-cyan">{text(item.evidence_required)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="rounded-lg border border-bda-border bg-bda-panel p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-bda-cyan">Route comparison</p>
                  <h2 className="font-semibold">{plan.name}</h2>
                </div>
                <button
                  className="rounded bg-bda-green px-3 py-2 text-sm text-bda-bg disabled:opacity-50"
                  disabled={materialize.isPending || Boolean(plan.materialized_workflow_run_id)}
                  onClick={() => materialize.mutate()}
                >
                  生成真实 Workflow
                </button>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {plan.route_options_json.map((route) => (
                  <button
                    key={route.route_id}
                    className={`rounded border p-3 text-left ${selectedRoute === route.route_id ? 'border-bda-cyan bg-bda-cyan/10' : 'border-bda-border'}`}
                    disabled={changeRoute.isPending}
                    onClick={() => {
                      setSelectedRoute(route.route_id)
                      changeRoute.mutate(route.route_id)
                    }}
                  >
                    <strong className="text-sm">{route.name}</strong>
                    <p className="mt-1 text-xs text-bda-muted">{route.rationale}</p>
                    <p className="mt-2 text-[11px] uppercase text-bda-amber">{route.recommendation}</p>
                    {route.required_evidence?.length ? (
                      <p className="mt-2 text-xs text-bda-cyan">Evidence: {route.required_evidence.join(', ')}</p>
                    ) : null}
                  </button>
                ))}
              </div>
              {plan.materialized_workflow_run_id ? (
                <p className="mt-3 text-sm text-bda-green">
                  已生成 Workflow：{plan.materialized_workflow_run_id}
                </p>
              ) : null}
            </div>

            <div className="rounded-lg border border-bda-border bg-bda-panel p-4 text-sm text-bda-muted">
              生成真实 Workflow 后，请在 Workflow 页面选择 RFdiffusion 节点，附加已审核的结构 artifact，
              编辑参数并生成与实际 runner 一致的提交预览。
            </div>
          </>
        )}
      </section>
    </div>
  )
}

export function ResearchPage() {
  const [tab, setTab] = useState<'builder' | 'literature' | 'campaigns'>('builder')
  return (
    <div>
      <div className="mb-6 flex items-end justify-between">
        <div><p className="text-xs uppercase tracking-wide text-bda-cyan">Research automation</p><h1 className="text-2xl font-semibold">知识学习与闭环研发</h1></div>
        <div className="flex gap-2">
          <button className={`rounded px-3 py-2 text-sm ${tab === 'builder' ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`} onClick={() => setTab('builder')}>甜味蛋白 Builder</button>
          <button className={`rounded px-3 py-2 text-sm ${tab === 'literature' ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`} onClick={() => setTab('literature')}>文献与证据</button>
          <button className={`rounded px-3 py-2 text-sm ${tab === 'campaigns' ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`} onClick={() => setTab('campaigns')}>Campaign 闭环</button>
        </div>
      </div>
      {tab === 'builder' ? <SweetProteinBuilder /> : tab === 'literature' ? <LiteraturePanel /> : <CampaignPanel />}
    </div>
  )
}
