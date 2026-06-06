import { MolStarViewer } from '../pdb-viewer/MolStarViewer'
import { structureFileUrl } from '../../lib/api/client'
import type { Candidate } from '../../lib/schemas/candidate'
import { ScoreBars } from './ScoreBars'
import { StatusPill, statusTone } from '../../components/ui/StatusPill'

interface CandidateDetailProps {
  candidate: Candidate | null
}

export function CandidateDetail({ candidate }: CandidateDetailProps) {
  if (!candidate) {
    return (
      <aside className="rounded-lg border border-bda-border bg-bda-panel p-4 text-sm text-bda-muted">
        Select a candidate to view structure, scores, and next action.
      </aside>
    )
  }

  const hasStructure = Boolean(candidate.structure_file_path || candidate.complex_file_path)

  return (
    <aside className="rounded-lg border border-bda-border bg-bda-panel p-4">
      {hasStructure ? (
        <MolStarViewer
          sourceUrl={structureFileUrl(candidate.candidate_id)}
          height={280}
          className="mb-4"
        />
      ) : (
        <div className="mb-4 flex h-[280px] items-center justify-center rounded-lg border border-dashed border-bda-border bg-bda-bg text-sm text-bda-muted">
          No structure file for this candidate yet
        </div>
      )}
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{candidate.candidate_id}</h2>
        <StatusPill label={candidate.decision} tone={statusTone(candidate.decision)} />
      </div>
      <p className="mb-4 text-sm text-bda-muted">
        Family {candidate.family}. {candidate.next_action}
      </p>
      <ScoreBars
        affinity={candidate.interface_score}
        stability={candidate.plddt}
        solubility={candidate.solubility_score ?? 70}
        rosetta={Math.min(100, Math.abs(candidate.rosetta_score ?? 20))}
      />
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-bda-muted">
        <div>Pred Kd: <span className="text-bda-text">{candidate.pred_kd}</span></div>
        <div>MD drift: <span className="text-bda-text">{candidate.interface_pae ?? '—'} Å</span></div>
        <div>Rosetta: <span className="text-bda-text">{candidate.rosetta_score ?? '—'}</span></div>
        <div>Expression: <span className="text-bda-text">{candidate.expression_risk ?? '—'}</span></div>
        {candidate.interface_energy != null ? (
          <div>Interface energy: <span className="text-bda-text">{candidate.interface_energy}</span></div>
        ) : null}
        {candidate.clash_count != null ? (
          <div>Clash count: <span className="text-bda-text">{candidate.clash_count}</span></div>
        ) : null}
        {candidate.buried_sasa != null ? (
          <div>Buried SASA: <span className="text-bda-text">{candidate.buried_sasa} Å²</span></div>
        ) : null}
      </div>
      <div className="mt-4 rounded-md border border-bda-border bg-bda-bg p-3 text-sm">
        <span className="text-xs uppercase text-bda-muted">Next action</span>
        <p className="mt-1 text-bda-text">{candidate.next_action}</p>
      </div>
    </aside>
  )
}
