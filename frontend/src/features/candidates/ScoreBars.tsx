interface ScoreBarsProps {
  affinity: number
  stability: number
  solubility: number
  rosetta: number
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

export function ScoreBars({ affinity, stability, solubility, rosetta }: ScoreBarsProps) {
  return (
    <div className="space-y-3">
      <Bar label="Affinity" value={affinity} />
      <Bar label="Stability / pLDDT" value={stability} />
      <Bar label="Solubility" value={solubility} />
      <Bar label="Rosetta scoring" value={rosetta} />
    </div>
  )
}
