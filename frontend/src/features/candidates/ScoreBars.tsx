interface ScoreBarsProps {
  affinity: number
  stability: number
  solubility: number
  rosettaScore: number | null | undefined
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <label className="mb-1 flex justify-between text-xs text-bda-muted">
        <span>{label}</span>
        <span>{value}</span>
      </label>
      <progress className="h-2 w-full accent-bda-cyan" value={value} max={100} />
    </div>
  )
}

export function ScoreBars({ affinity, stability, solubility, rosettaScore }: ScoreBarsProps) {
  return (
    <div className="space-y-3">
      <Bar label="Affinity (interface score)" value={affinity} />
      <Bar label="Stability / pLDDT" value={stability} />
      <Bar label="Solubility" value={solubility} />
      <div>
        <label className="mb-1 flex justify-between text-xs text-bda-muted">
          <span>Rosetta interface energy</span>
          <span>{rosettaScore ?? '—'}</span>
        </label>
        <p className="text-xs text-bda-muted">Lower energy is better; not normalized to 0–100.</p>
      </div>
    </div>
  )
}
