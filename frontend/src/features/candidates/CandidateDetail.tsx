import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MolStarViewerLazy } from '../pdb-viewer/MolStarViewerLazy'
import { artifactUrl, structureFileUrl } from '../../lib/api/client'
import { explainCandidate } from '../../lib/api/copilot'
import type { Candidate } from '../../lib/schemas/candidate'
import { ScoreBars } from './ScoreBars'
import { StatusPill, statusTone } from '../../components/ui/StatusPill'
import { useI18n } from '../../lib/i18n'
import { useToastStore } from '../../components/ui/Toast'

interface CandidateDetailProps {
  candidate: Candidate | null
  projectId: string
}

export function CandidateDetail({ candidate, projectId }: CandidateDetailProps) {
  const { t } = useI18n()
  const showToast = useToastStore((s) => s.show)
  const [structureMode, setStructureMode] = useState<'monomer' | 'complex'>('monomer')
  const [explanation, setExplanation] = useState<string | null>(null)

  if (!candidate) {
    return (
      <aside className="rounded-lg border border-bda-border bg-bda-panel p-4 text-sm text-bda-muted">
        Select a candidate to view structure, scores, and next action.
      </aside>
    )
  }

  const hasMonomer = Boolean(candidate.structure_file_path)
  const hasComplex = Boolean(candidate.complex_file_path)
  const hasStructure = hasMonomer || hasComplex
  const structureUrl =
    structureMode === 'complex' && hasComplex
      ? artifactUrl(candidate.complex_file_path!)
      : hasMonomer
        ? structureFileUrl(candidate.candidate_id)
        : hasComplex
          ? artifactUrl(candidate.complex_file_path!)
          : null

  const explain = async () => {
    try {
      const result = await explainCandidate(candidate.candidate_id)
      setExplanation(`${result.recommendation} ${result.reasons.join(' ')}`)
    } catch {
      showToast('Failed to load candidate explanation', 'error')
    }
  }

  return (
    <aside className="rounded-lg border border-bda-border bg-bda-panel p-4">
      {hasStructure ? (
        <>
          {hasMonomer && hasComplex ? (
            <div className="mb-2 flex gap-2">
              <button
                type="button"
                className={`rounded-md px-2 py-1 text-xs ${structureMode === 'monomer' ? 'bg-bda-cyan/15 text-bda-cyan' : 'border border-bda-border'}`}
                onClick={() => setStructureMode('monomer')}
              >
                Monomer
              </button>
              <button
                type="button"
                className={`rounded-md px-2 py-1 text-xs ${structureMode === 'complex' ? 'bg-bda-cyan/15 text-bda-cyan' : 'border border-bda-border'}`}
                onClick={() => setStructureMode('complex')}
              >
                Complex
              </button>
            </div>
          ) : null}
          <MolStarViewerLazy sourceUrl={structureUrl} height={280} className="mb-4" />
        </>
      ) : (
        <div className="mb-4 flex h-[280px] items-center justify-center rounded-lg border border-dashed border-bda-border bg-bda-bg text-sm text-bda-muted">
          No structure file for this candidate yet
        </div>
      )}
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{candidate.candidate_id}</h2>
        <StatusPill label={candidate.decision ?? '—'} tone={statusTone(candidate.decision ?? '')} />
      </div>
      <p className="mb-4 text-sm text-bda-muted">
        Family {candidate.family}. {candidate.next_action}
      </p>
      {explanation ? <p className="mb-4 rounded-md border border-bda-border bg-bda-bg p-3 text-sm text-bda-text">{explanation}</p> : null}
      <ScoreBars
        affinity={candidate.interface_score}
        stability={candidate.plddt}
        solubility={candidate.solubility_score ?? 70}
        rosettaScore={candidate.rosetta_score}
      />
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-bda-muted">
        <div>
          {t.candidates.predKd}: <span className="text-bda-text">{candidate.pred_kd}</span>
        </div>
        <div>
          MD drift: <span className="text-bda-text">{candidate.interface_pae ?? '—'} Å</span>
        </div>
        <div>
          Rosetta: <span className="text-bda-text">{candidate.rosetta_score ?? '—'}</span>
        </div>
        <div>
          Expression: <span className="text-bda-text">{candidate.expression_risk ?? '—'}</span>
        </div>
        {candidate.clash_count != null ? (
          <div>
            Clash count: <span className="text-bda-text">{candidate.clash_count}</span>
          </div>
        ) : null}
        {candidate.buried_sasa != null ? (
          <div>
            Buried SASA: <span className="text-bda-text">{candidate.buried_sasa} Å²</span>
          </div>
        ) : null}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md border border-bda-border px-3 py-1.5 text-sm hover:bg-bda-panel-hover"
          onClick={() => void explain()}
        >
          {t.candidates.explain}
        </button>
        <Link
          to={`/results?project=${encodeURIComponent(projectId)}&candidate=${encodeURIComponent(candidate.candidate_id)}`}
          className="rounded-md border border-bda-border px-3 py-1.5 text-sm hover:bg-bda-panel-hover"
        >
          {t.candidates.viewLabResults}
        </Link>
      </div>
      <div className="mt-4 rounded-md border border-bda-border bg-bda-bg p-3 text-sm">
        <span className="text-xs uppercase text-bda-muted">Next action</span>
        <p className="mt-1 text-bda-text">{candidate.next_action}</p>
      </div>
    </aside>
  )
}
