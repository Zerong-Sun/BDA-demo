import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Check, ExternalLink, LoaderCircle, MessageSquare, Play, Search, Sparkles, X } from 'lucide-react'

import {
  createLiteratureSubscription,
  detectLiteratureRelations,
  ingestLiterature,
  listLiteratureClaims,
  listLiteratureRelations,
  listLiteratureSubscriptions,
  applyRoutePlan,
  planRoute,
  reviewLiteratureClaim,
  reviewLiteratureRelation,
  runLiteratureSubscription,
  searchLiteratureLibrary,
  updateLiteratureSubscription,
  type RoutePlan,
} from '../lib/api/copilot'
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
import { getProjectResearchSummary } from '../lib/api/projects'
import { useAppStore } from '../lib/store/appStore'
import { useToastStore } from '../components/ui/toastStore'

function text(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function jsonRecord(value: unknown): Record<string, unknown> {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : {}
    } catch {
      return {}
    }
  }
  return typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function jsonArray(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
}

function sourceUrl(source: string, refs: string[]): string | null {
  if (source.startsWith('http')) return source
  const hit = refs.find((ref) => ref.includes(source) || source.includes(ref))
  return hit?.startsWith('http') ? hit : null
}

function claimTitle(item: Record<string, unknown>) {
  return text(jsonRecord(item.context_json).title) || text(item.title)
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
          Save patch
        </button>
        <button
          className="rounded bg-bda-green px-3 py-1.5 text-sm text-bda-bg disabled:opacity-50"
          disabled={dirty || saving}
          onClick={() => onReview(decisionId, true)}
        >
          Approve and create next round
        </button>
        <button
          className="rounded border border-bda-red px-3 py-1.5 text-sm text-bda-red"
          onClick={() => onReview(decisionId, false)}
        >
          Reject
        </button>
      </div>
    </div>
  )
}

function LiteraturePanel() {
  const client = useQueryClient()
  const navigate = useNavigate()
  const { projectId } = useProjectContext()
  const setCopilotOpen = useAppStore((state) => state.setCopilotOpen)
  const setProjectWorkflowRunId = useAppStore((state) => state.setProjectWorkflowRunId)
  const showToast = useToastStore((state) => state.show)
  const isAdmin = currentRole() === 'admin'
  const [query, setQuery] = useState('sweet protein monellin brazzein TAS1R2 TAS1R3')
  const [workflowObjective, setWorkflowObjective] = useState('Build an evidence-backed sweet protein scaffold redesign workflow for monellin and brazzein candidates.')
  const [routePlan, setRoutePlan] = useState<RoutePlan | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState('')
  const [selectedModuleIds, setSelectedModuleIds] = useState<string[]>([])
  const claims = useQuery({ queryKey: ['literature-claims'], queryFn: () => listLiteratureClaims() })
  const projectResearch = useQuery({
    queryKey: ['project-research-summary', projectId],
    queryFn: () => getProjectResearchSummary(projectId),
    enabled: Boolean(projectId),
  })
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
  const generateWorkflowPlan = useMutation({
    mutationFn: () =>
      planRoute({
        project_id: projectId,
        target: query,
        objective: workflowObjective,
        constraints: {
          source: 'research_dossier',
          evidence_findings: projectResearch.data?.findings.length ?? 0,
          reviewed_claims: claims.data?.items.length ?? 0,
        },
      }),
    onSuccess: (plan) => {
      const recommended = plan.route_options.find((route) => route.recommended) ?? plan.route_options[0]
      setRoutePlan(plan)
      setSelectedRouteId(recommended?.route_id ?? '')
      setSelectedModuleIds(recommended?.modules.filter((module) => module.available).map((module) => module.module_id) ?? [])
      showToast('Workflow draft options prepared from research context', 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to prepare workflow draft', 'error'),
  })
  const selectedRoute = routePlan?.route_options.find((route) => route.route_id === selectedRouteId) ?? null
  const applyWorkflowPlan = useMutation({
    mutationFn: async () => {
      if (!selectedRoute) throw new Error('Select a route first')
      return applyRoutePlan({
        project_id: projectId,
        route_id: selectedRoute.route_id,
        objective: workflowObjective,
        target: routePlan?.target ?? query,
        selected_module_ids: selectedModuleIds,
        constraints: {
          source: 'research_dossier',
          generated_from: 'research_page',
          evidence_findings: projectResearch.data?.findings.length ?? 0,
        },
      })
    },
    onSuccess: (result) => {
      const runId = String(result.workflow_run.workflow_run_id)
      setProjectWorkflowRunId(projectId, runId)
      client.invalidateQueries({ queryKey: ['workflow-runs', projectId] })
      client.invalidateQueries({ queryKey: ['workflow-run', 'latest', projectId] })
      client.invalidateQueries({ queryKey: ['workflow-graph', runId] })
      showToast('Research workflow draft created', 'success')
      navigate('/workflow')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to create workflow draft', 'error'),
  })
  const sourceRefs = jsonArray(projectResearch.data?.brief?.source_material_json) as Array<Record<string, unknown>>
  const referenceLinks = sourceRefs.flatMap((source) => jsonArray(source.references)).filter((item): item is string => typeof item === 'string')

  return (
    <div className="space-y-4">
      <section className="bda-card">
        <div className="bda-card-header">
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Current project research</p>
            <h2 className="font-semibold">{text(projectResearch.data?.brief?.title) || 'No research brief has been created for this project.'}</h2>
            <p className="mt-1 max-w-4xl text-sm text-bda-muted">
              {text(projectResearch.data?.brief?.objective) || 'Once a research task is created or confirmed, the brief, questions, findings, and workflow plans will appear here.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-bda-muted">
            <span className="rounded border border-bda-border px-2 py-1">Questions {projectResearch.data?.questions.length ?? 0}</span>
            <span className="rounded border border-bda-border px-2 py-1">Findings {projectResearch.data?.findings.length ?? 0}</span>
            <span className="rounded border border-bda-border px-2 py-1">Runs {projectResearch.data?.runs.length ?? 0}</span>
            <span className="rounded border border-bda-border px-2 py-1">Plans {projectResearch.data?.workflow_plans.length ?? 0}</span>
          </div>
        </div>
        <div className="bda-card-body">
          {projectResearch.data?.findings.length ? (
          <div className="bda-scroll-area grid max-h-96 gap-3 pr-1 lg:grid-cols-2">
            {projectResearch.data.findings.slice(0, 6).map((item) => (
              <article key={text(item.research_finding_id)} className="rounded border border-bda-border bg-bda-bg p-3 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <strong>{text(item.title)}</strong>
                  <span className="shrink-0 rounded border border-bda-border px-1.5 py-0.5 text-[10px] uppercase text-bda-muted">
                    {text(item.track)}
                  </span>
                </div>
                <p className="mt-2 text-bda-text">{text(item.statement)}</p>
                {text(item.uncertainty) ? (
                  <p className="mt-2 rounded border border-bda-amber/30 bg-bda-amber/10 p-2 text-xs text-bda-amber">
                    Uncertainty to resolve: {text(item.uncertainty)}
                  </p>
                ) : null}
                <div className="mt-3 space-y-1">
                  <p className="text-[10px] uppercase tracking-wide text-bda-muted">Sources</p>
                  {jsonArray(item.source_refs_json).map((source, index) => {
                    const label = text(source)
                    const url = sourceUrl(label, referenceLinks)
                    return url ? (
                      <a key={`${label}-${index}`} className="block truncate text-xs text-bda-cyan hover:underline" href={url} target="_blank" rel="noreferrer">
                        <ExternalLink className="mr-1 inline h-3 w-3" />
                        {label}
                      </a>
                    ) : (
                      <span key={`${label}-${index}`} className="block truncate text-xs text-bda-muted">{label}</span>
                    )
                  })}
                </div>
              </article>
            ))}
          </div>
          ) : null}
          {referenceLinks.length ? (
          <details className="mt-4 rounded border border-bda-border bg-bda-bg p-3 text-sm">
            <summary className="cursor-pointer text-bda-cyan">View linked literature sources ({referenceLinks.length})</summary>
            <div className="bda-scroll-area mt-3 grid max-h-48 gap-1 md:grid-cols-2">
              {referenceLinks.slice(0, 40).map((url) => (
                <a key={url} className="truncate text-xs text-bda-cyan hover:underline" href={url} target="_blank" rel="noreferrer">
                  <ExternalLink className="mr-1 inline h-3 w-3" />
                  {url}
                </a>
              ))}
            </div>
          </details>
          ) : null}
        </div>
      </section>

      <section className="bda-card">
        <div className="bda-card-header">
          <div className="min-w-0 flex-1">
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Research-to-workflow draft</p>
            <h2 className="font-semibold">Create an editable workflow from the evidence dossier</h2>
            <p className="mt-1 max-w-4xl text-xs leading-relaxed text-bda-muted">
              The draft keeps model predictions separate from experimental evidence and writes route context into node parameters for audit.
            </p>
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
            disabled={!projectId || !workflowObjective.trim() || generateWorkflowPlan.isPending}
            onClick={() => generateWorkflowPlan.mutate()}
          >
            {generateWorkflowPlan.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Draft routes
          </button>
        </div>
        <div className="bda-card-body grid gap-3">
          <textarea
            className="min-h-20 w-full resize-none rounded border border-bda-border bg-bda-bg px-3 py-2 text-sm"
            value={workflowObjective}
            onChange={(event) => setWorkflowObjective(event.target.value)}
            placeholder="Describe the design objective, success criteria, assay context, and constraints."
          />
          {routePlan ? (
            <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
              <div className="grid gap-3">
                <div className="flex flex-wrap gap-2">
                  {routePlan.route_options.map((route) => (
                    <button
                      key={route.route_id}
                      type="button"
                      className={`rounded border px-3 py-2 text-left text-sm ${
                        route.route_id === selectedRouteId
                          ? 'border-bda-cyan bg-bda-cyan/10 text-bda-cyan'
                          : 'border-bda-border hover:border-bda-cyan/50'
                      }`}
                      onClick={() => {
                        setSelectedRouteId(route.route_id)
                        setSelectedModuleIds(route.modules.filter((module) => module.available).map((module) => module.module_id))
                      }}
                    >
                      <span className="block font-medium">{route.label}</span>
                      <span className="block text-xs text-bda-muted">{route.estimated_steps} modules</span>
                    </button>
                  ))}
                </div>
                {selectedRoute ? (
                  <div className="rounded border border-bda-border bg-bda-bg p-3">
                    <p className="text-sm">{selectedRoute.summary}</p>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      {selectedRoute.modules.map((module) => (
                        <label key={module.module_id} className="flex gap-2 rounded border border-bda-border p-2 text-sm">
                          <input
                            type="checkbox"
                            className="mt-1"
                            disabled={!module.available}
                            checked={selectedModuleIds.includes(module.module_id)}
                            onChange={(event) => {
                              setSelectedModuleIds((current) =>
                                event.target.checked
                                  ? [...new Set([...current, module.module_id])]
                                  : current.filter((id) => id !== module.module_id),
                              )
                            }}
                          />
                          <span>
                            <span className="block font-medium">{module.model_name}</span>
                            <span className="block text-xs text-bda-muted">{module.available ? module.summary : 'Plugin is not registered yet.'}</span>
                          </span>
                        </label>
                      ))}
                    </div>
                    <button
                      type="button"
                      className="mt-3 inline-flex items-center gap-2 rounded bg-bda-green px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
                      disabled={applyWorkflowPlan.isPending || selectedModuleIds.length === 0}
                      onClick={() => applyWorkflowPlan.mutate()}
                    >
                      {applyWorkflowPlan.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                      Create editable workflow
                    </button>
                  </div>
                ) : null}
              </div>
              <aside className="rounded border border-bda-border bg-bda-bg p-3 text-xs text-bda-muted">
                <p className="mb-2 uppercase tracking-wide text-bda-cyan">Evidence context</p>
                <ul className="bda-scroll-area grid max-h-36 gap-1">
                  {routePlan.knowledge_context.map((item) => (
                    <li key={item.knowledge_entry_id}>{item.title}</li>
                  ))}
                </ul>
              </aside>
            </div>
          ) : null}
        </div>
      </section>

      <section className="bda-card">
        <div className="bda-card-header">
          <div>
            <h2 className="font-semibold">Literature ingestion and automated surveillance</h2>
            <p className="mt-1 max-w-4xl text-xs leading-relaxed text-bda-muted">
              Local search queries the curated project library. Ingest searches Europe PMC and writes reviewed metadata into the local literature store.
            </p>
          </div>
        </div>
        <div className="bda-card-body">
        <div className="flex flex-wrap gap-2">
          <input className="min-w-72 flex-1 rounded border border-bda-border bg-bda-bg px-3 py-2 text-sm" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="rounded border border-bda-border px-3 py-2 text-sm" onClick={() => search.refetch()}><Search className="mr-1 inline h-4 w-4" />Search local library</button>
          <button className="rounded bg-bda-cyan px-3 py-2 text-sm text-bda-bg disabled:opacity-50" disabled={!isAdmin || ingest.isPending} onClick={() => ingest.mutate()}>
            {ingest.isPending ? <LoaderCircle className="mr-1 inline h-4 w-4 animate-spin" /> : null}Ingest now
          </button>
          <button className="rounded border border-bda-border px-3 py-2 text-sm disabled:opacity-50" disabled={!isAdmin} onClick={() => createSubscription.mutate()}>Create daily surveillance</button>
          <button className="rounded border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50" onClick={() => setCopilotOpen(true)}>
            <MessageSquare className="mr-1 inline h-4 w-4" />Ask Copilot to interpret or summarize
          </button>
        </div>
        {!isAdmin ? <p className="mt-2 text-xs text-bda-muted">Ingestion, automated surveillance, and relation detection require administrator privileges. Researchers may still search and review evidence.</p> : null}
        {ingest.isError || createSubscription.isError ? (
          <p className="mt-2 text-xs text-bda-red">Literature task failed. Check permissions, network access, and model configuration.</p>
        ) : null}
        <div className="bda-scroll-area mt-3 max-h-80 space-y-3 pr-1">
        {search.data?.items.map((item, index) => (
          <div key={`${text(item.document_id)}-${index}`} className="rounded border border-bda-border bg-bda-bg p-3 text-sm">
            <strong>{claimTitle(item)}</strong>
            <p className="mt-1 text-bda-muted">{text(item.statement) || text(item.abstract_text)}</p>
            <p className="mt-1 text-xs text-bda-muted">{text(item.title)}</p>
            {text(item.doi) || text(item.pmid) ? (
              <a
                className="mt-1 inline-flex items-center gap-1 text-xs text-bda-cyan hover:underline"
                href={text(item.doi) ? `https://doi.org/${text(item.doi)}` : `https://pubmed.ncbi.nlm.nih.gov/${text(item.pmid)}/`}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink className="h-3 w-3" />
                {text(item.doi) || `PMID:${text(item.pmid)}`}
              </a>
            ) : null}
          </div>
        ))}
        </div>
        <div className="bda-scroll-area mt-3 max-h-64 space-y-3 pr-1">
        {subscriptions.data?.items.map((item) => (
          <div key={item.subscription_id} className="flex items-center justify-between gap-3 rounded border border-bda-border bg-bda-bg p-3 text-sm">
            <div><strong>{item.name}</strong><p className="text-xs text-bda-muted">Every {item.interval_hours} hours · next run {item.next_run_at}</p></div>
            <div className="flex gap-2">
              <button className="rounded border border-bda-border px-2 py-1 text-xs" onClick={() => toggleSubscription.mutate(item)}>{item.enabled ? 'Pause' : 'Enable'}</button>
              <button className="rounded border border-bda-border px-2 py-1 text-xs" onClick={() => runSubscription.mutate(item.subscription_id)}><Play className="mr-1 inline h-3 w-3" />Run now</button>
            </div>
          </div>
        ))}
        </div>
        </div>
      </section>

      <section className="bda-workspace-grid lg:grid-cols-2">
        <div className="bda-card flex min-h-0 flex-col">
          <div className="bda-card-header">
            <h2 className="font-semibold">Scientific claims awaiting review</h2>
            <span className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted">{claims.data?.items.length ?? 0}</span>
          </div>
          <div className="bda-scroll-area max-h-[52vh] space-y-3 p-4 pr-3">
          {claims.data?.items.map((item) => (
            <article key={text(item.claim_id)} className="rounded border border-bda-border bg-bda-bg p-3 text-sm">
              <strong>{claimTitle(item)}</strong>
              <p className="mt-1">{text(item.statement)}</p>
              <p className="mt-1 text-xs text-bda-muted">{text(item.title)}</p>
              <blockquote className="mt-2 border-l-2 border-bda-cyan pl-2 text-xs text-bda-muted">{text(item.evidence_excerpt)}</blockquote>
              <div className="mt-2 flex gap-2">
                <button className="text-bda-green" onClick={() => reviewClaim.mutate({ id: text(item.claim_id), status: 'accepted' })}><Check className="inline h-4 w-4" /> Accept</button>
                <button className="text-bda-red" onClick={() => reviewClaim.mutate({ id: text(item.claim_id), status: 'rejected' })}><X className="inline h-4 w-4" /> Reject</button>
              </div>
            </article>
          ))}
          </div>
        </div>
        <div className="bda-card flex min-h-0 flex-col">
          <div className="bda-card-header">
            <h2 className="font-semibold">Claim relationships awaiting review</h2>
            <button className="rounded border border-bda-border px-2 py-1 text-xs disabled:opacity-50" disabled={!isAdmin || detectRelations.isPending} onClick={() => detectRelations.mutate()}>
              Detect relationships
            </button>
          </div>
          <div className="bda-scroll-area max-h-[52vh] space-y-3 p-4 pr-3">
          {relations.data?.items.map((item) => (
            <article key={text(item.relation_id)} className="rounded border border-bda-border bg-bda-bg p-3 text-sm">
              <span className="text-xs uppercase text-bda-cyan">{text(item.relation_type)}</span>
              <p>{text(item.source_statement)}</p><p className="text-bda-muted">↔ {text(item.target_statement)}</p>
              <div className="mt-2 flex gap-2">
                <button className="text-bda-green" onClick={() => reviewRelation.mutate({ id: text(item.relation_id), status: 'accepted' })}>Accept</button>
                <button className="text-bda-red" onClick={() => reviewRelation.mutate({ id: text(item.relation_id), status: 'rejected' })}>Reject</button>
              </div>
            </article>
          ))}
          </div>
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
    <div className="bda-workspace-grid lg:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="bda-card bda-sticky-panel">
        <div className="bda-card-header">
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Campaigns</p>
            <h2 className="text-sm font-semibold">Closed-loop runs</h2>
          </div>
          <span className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted">
            {campaigns.data?.items.length ?? 0}
          </span>
        </div>
        <div className="bda-card-body">
          <button className="w-full rounded bg-bda-cyan px-3 py-2 text-sm text-bda-bg" disabled={!projectId || create.isPending} onClick={() => create.mutate()}>Create closed-loop campaign</button>
          <div className="bda-scroll-area mt-3 max-h-[58vh] space-y-3 pr-1">
            {campaigns.data?.items.map((item) => (
              <button key={item.campaign_id} className="w-full rounded border border-bda-border bg-bda-bg p-3 text-left hover:border-bda-cyan/50" onClick={() => setSelected(item.campaign_id)}>
                <strong>{item.name}</strong><p className="text-xs text-bda-muted">Round {item.current_round}/{item.max_rounds} · {item.status}</p>
              </button>
            ))}
          </div>
        </div>
      </aside>
      <section className="bda-card flex min-h-0 flex-col">
        <div className="bda-card-header">
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Campaign detail</p>
            <h2 className="text-sm font-semibold">{campaign?.name ?? 'No campaign selected'}</h2>
          </div>
        </div>
        <div className="bda-card-body bda-scroll-area max-h-[68vh]">
        {actionError ? <p className="mb-3 rounded border border-bda-red/40 p-2 text-sm text-bda-red">{actionError.message}</p> : null}
        {!campaign ? <p className="text-bda-muted">Select or create a campaign.</p> : (
          <>
            <h2 className="text-lg font-semibold">{campaign.name}</h2>
            <p className="text-sm text-bda-muted">{campaign.objective}</p>
            {campaign.rounds?.map((round) => {
              const decision = round.decisions?.[0]
              const decisionId = decision ? text(decision.decision_id) : ''
              const patch = decision?.parameter_patch_json
              return (
                <article key={round.campaign_round_id} className="mt-4 rounded border border-bda-border bg-bda-bg p-4">
                  <div className="flex justify-between"><strong>Round {round.round_number}</strong><span className="text-xs text-bda-cyan">{round.status} · {round.approval_status}</span></div>
                  <p className="mt-1 text-xs text-bda-muted">Workflow: {round.workflow_run_id}</p>
                  {round.status === 'ready_for_evaluation' || round.status === 'active' ? (
                    <button className="mt-3 rounded border border-bda-border px-3 py-1.5 text-sm" onClick={() => evaluate.mutate({ id: campaign.campaign_id, round: round.round_number })}>Evaluate round</button>
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
        </div>
      </section>
    </div>
  )
}

export function ResearchPage() {
  const [tab, setTab] = useState<'literature' | 'campaigns'>('literature')
  return (
    <div className="space-y-4">
      <div className="bda-card flex flex-wrap items-end justify-between gap-3 p-4">
        <div><p className="text-xs uppercase tracking-wide text-bda-cyan">Research automation</p><h1 className="text-2xl font-semibold">Knowledge learning and closed-loop development</h1></div>
        <div className="flex gap-2">
          <button className={`rounded px-3 py-2 text-sm ${tab === 'literature' ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`} onClick={() => setTab('literature')}>Literature and evidence</button>
          <button className={`rounded px-3 py-2 text-sm ${tab === 'campaigns' ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`} onClick={() => setTab('campaigns')}>Campaign loop</button>
        </div>
      </div>
      {tab === 'literature' ? <LiteraturePanel /> : <CampaignPanel />}
    </div>
  )
}
