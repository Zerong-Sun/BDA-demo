import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, LoaderCircle, Play, Search, X } from 'lucide-react'

import {
  createLiteratureSubscription,
  ingestLiterature,
  listLiteratureClaims,
  listLiteratureRelations,
  listLiteratureSubscriptions,
  reviewLiteratureClaim,
  reviewLiteratureRelation,
  runLiteratureSubscription,
  searchLiteratureLibrary,
} from '../lib/api/copilot'
import {
  createCampaign,
  evaluateCampaignRound,
  getCampaign,
  listProjectCampaigns,
  reviewCampaignDecision,
  type Campaign,
} from '../lib/api/campaigns'
import { useProjectContext } from '../lib/hooks/useProjectContext'

function text(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function LiteraturePanel() {
  const client = useQueryClient()
  const [query, setQuery] = useState('protein binder design')
  const claims = useQuery({ queryKey: ['literature-claims'], queryFn: () => listLiteratureClaims() })
  const relations = useQuery({ queryKey: ['literature-relations'], queryFn: () => listLiteratureRelations() })
  const subscriptions = useQuery({
    queryKey: ['literature-subscriptions'],
    queryFn: listLiteratureSubscriptions,
    retry: false,
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

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-bda-border bg-bda-panel p-4">
        <h2 className="font-semibold">文献摄取与自动订阅</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <input className="min-w-72 flex-1 rounded border border-bda-border bg-bda-bg px-3 py-2 text-sm" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="rounded border border-bda-border px-3 py-2 text-sm" onClick={() => search.refetch()}><Search className="mr-1 inline h-4 w-4" />检索本地库</button>
          <button className="rounded bg-bda-cyan px-3 py-2 text-sm text-bda-bg" disabled={ingest.isPending} onClick={() => ingest.mutate()}>
            {ingest.isPending ? <LoaderCircle className="mr-1 inline h-4 w-4 animate-spin" /> : null}立即摄取
          </button>
          <button className="rounded border border-bda-border px-3 py-2 text-sm" onClick={() => createSubscription.mutate()}>每日自动阅读</button>
        </div>
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
            <button className="rounded border border-bda-border px-2 py-1 text-xs" onClick={() => runSubscription.mutate(item.subscription_id)}><Play className="mr-1 inline h-3 w-3" />运行</button>
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
          <h2 className="font-semibold">待审核主张关系</h2>
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

  const campaign = detail.data as Campaign | undefined
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
        {!campaign ? <p className="text-bda-muted">选择或创建一个 Campaign。</p> : (
          <>
            <h2 className="text-lg font-semibold">{campaign.name}</h2>
            <p className="text-sm text-bda-muted">{campaign.objective}</p>
            {campaign.rounds?.map((round) => {
              const decision = round.decisions?.[0]
              const decisionId = decision ? text(decision.decision_id) : ''
              return (
                <article key={round.campaign_round_id} className="mt-4 rounded border border-bda-border p-4">
                  <div className="flex justify-between"><strong>Round {round.round_number}</strong><span className="text-xs text-bda-cyan">{round.status} · {round.approval_status}</span></div>
                  <p className="mt-1 text-xs text-bda-muted">Workflow: {round.workflow_run_id}</p>
                  {round.status === 'ready_for_evaluation' || round.status === 'active' ? (
                    <button className="mt-3 rounded border border-bda-border px-3 py-1.5 text-sm" onClick={() => evaluate.mutate({ id: campaign.campaign_id, round: round.round_number })}>评价本轮</button>
                  ) : null}
                  {decisionId && text(decision?.status) === 'proposed' ? (
                    <div className="mt-3 flex gap-2">
                      <button className="rounded bg-bda-green px-3 py-1.5 text-sm text-bda-bg" onClick={() => review.mutate({ id: decisionId, approve: true })}>批准并创建下一轮</button>
                      <button className="rounded border border-bda-red px-3 py-1.5 text-sm text-bda-red" onClick={() => review.mutate({ id: decisionId, approve: false })}>拒绝</button>
                    </div>
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

export function ResearchPage() {
  const [tab, setTab] = useState<'literature' | 'campaigns'>('literature')
  return (
    <div>
      <div className="mb-6 flex items-end justify-between">
        <div><p className="text-xs uppercase tracking-wide text-bda-cyan">Research automation</p><h1 className="text-2xl font-semibold">知识学习与闭环研发</h1></div>
        <div className="flex gap-2">
          <button className={`rounded px-3 py-2 text-sm ${tab === 'literature' ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`} onClick={() => setTab('literature')}>文献与证据</button>
          <button className={`rounded px-3 py-2 text-sm ${tab === 'campaigns' ? 'bg-bda-cyan text-bda-bg' : 'border border-bda-border'}`} onClick={() => setTab('campaigns')}>Campaign 闭环</button>
        </div>
      </div>
      {tab === 'literature' ? <LiteraturePanel /> : <CampaignPanel />}
    </div>
  )
}
