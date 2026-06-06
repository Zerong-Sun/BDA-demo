interface CandidateFiltersProps {
  search: string
  status: string
  priorityOnly: boolean
  onSearchChange: (value: string) => void
  onStatusChange: (value: string) => void
  onPriorityOnlyChange: (value: boolean) => void
}

const statuses = ['All', 'Validated', 'QC risk', 'Retest', 'Reserve']

export function CandidateFilters({
  search,
  status,
  priorityOnly,
  onSearchChange,
  onStatusChange,
  onPriorityOnlyChange,
}: CandidateFiltersProps) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <input
        className="min-w-[220px] flex-1 rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm"
        placeholder="Search candidate or family"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <select
        className="rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm"
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
      >
        {statuses.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <button
        type="button"
        className={`rounded-md border px-3 py-2 text-sm ${
          priorityOnly
            ? 'border-bda-cyan bg-bda-cyan/10 text-bda-cyan'
            : 'border-bda-border text-bda-muted hover:text-bda-text'
        }`}
        onClick={() => onPriorityOnlyChange(!priorityOnly)}
      >
        Priority only
      </button>
    </div>
  )
}
