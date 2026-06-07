import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { useMemo, useState } from 'react'
import type { Candidate } from '../../lib/schemas/candidate'
import { StatusPill, statusTone } from '../../components/ui/StatusPill'

const columnHelper = createColumnHelper<Candidate>()

interface CandidateTableProps {
  data: Candidate[]
  selectedId?: string
  onSelect: (candidate: Candidate) => void
}

export function CandidateTable({ data, selectedId, onSelect }: CandidateTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'interface_score', desc: true },
  ])

  const columns = useMemo(
    () => [
      columnHelper.accessor('candidate_id', {
        header: 'Candidate',
        cell: (info) => (
          <span className="inline-flex items-center gap-2">
            {info.getValue()}
            {info.row.original.decision === 'Anchor' ? (
              <span className="rounded border border-bda-cyan/40 bg-bda-cyan/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-bda-cyan">
                Anchor
              </span>
            ) : null}
          </span>
        ),
      }),
      columnHelper.accessor('family', { header: 'Family' }),
      columnHelper.accessor('interface_score', { header: 'Affinity' }),
      columnHelper.accessor('pred_kd', { header: 'Pred Kd' }),
      columnHelper.accessor('plddt', { header: 'pLDDT' }),
      columnHelper.accessor('solubility_score', {
        header: 'Solubility',
        cell: (info) => info.getValue() ?? '—',
      }),
      columnHelper.accessor('interface_pae', {
        header: 'MD drift',
        cell: (info) => (info.getValue() != null ? `${info.getValue()} Å` : '—'),
      }),
      columnHelper.accessor('rosetta_score', {
        header: 'Rosetta',
        cell: (info) => info.getValue() ?? '—',
      }),
      columnHelper.accessor('clash_count', {
        header: 'Clash',
        cell: (info) => info.getValue() ?? '—',
      }),
      columnHelper.accessor('buried_sasa', {
        header: 'Buried SASA',
        cell: (info) => (info.getValue() != null ? `${info.getValue()} Å²` : '—'),
      }),
      columnHelper.accessor('expression_risk', { header: 'Expression' }),
      columnHelper.accessor('status', {
        header: 'Status',
        cell: (info) => <StatusPill label={info.getValue()} tone={statusTone(info.getValue())} />,
      }),
      columnHelper.accessor('decision', {
        header: 'Decision',
        cell: (info) => (
          <StatusPill label={info.getValue() ?? '—'} tone={statusTone(info.getValue() ?? '')} />
        ),
      }),
    ],
    [],
  )

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return (
    <div className="rounded-lg border border-bda-border bg-bda-panel">
      <p className="px-3 pt-2 text-xs text-bda-muted sm:hidden" aria-hidden="true">
        Swipe horizontally to see all columns →
      </p>
      <div
        className="overflow-x-auto"
        role="region"
        aria-label="Candidate results table (scrollable)"
        tabIndex={0}
      >
        <table className="min-w-full text-sm">
          <caption className="sr-only">
            Ranked candidates. Activate a column header to sort; activate a row to view candidate
            details.
          </caption>
          <thead className="border-b border-bda-border bg-bda-bg text-left text-xs uppercase tracking-wide text-bda-muted">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sorted = header.column.getIsSorted()
                  const ariaSort =
                    sorted === 'asc' ? 'ascending' : sorted === 'desc' ? 'descending' : 'none'
                  const toggleSort = header.column.getToggleSortingHandler()
                  return (
                    <th
                      key={header.id}
                      scope="col"
                      aria-sort={ariaSort}
                      className="px-3 py-2"
                    >
                      <button
                        type="button"
                        className="flex w-full items-center gap-1 text-left uppercase tracking-wide hover:text-bda-text"
                        onClick={toggleSort}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {{
                          asc: ' ↑',
                          desc: ' ↓',
                        }[sorted as string] ?? null}
                      </button>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => {
              const isSelected = selectedId === row.original.candidate_id
              return (
                <tr
                  key={row.id}
                  role="button"
                  tabIndex={0}
                  aria-selected={isSelected}
                  aria-label={`View details for candidate ${row.original.candidate_id}`}
                  className={`cursor-pointer border-b border-bda-border/60 hover:bg-bda-panel-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-bda-cyan ${
                    isSelected ? 'bg-bda-cyan/10 border-l-2 border-l-bda-cyan' : ''
                  }`}
                  onClick={() => onSelect(row.original)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(row.original)
                    }
                  }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {data.length === 0 ? (
        <div className="p-6 text-center text-sm text-bda-muted">No candidates match the current filters.</div>
      ) : null}
    </div>
  )
}
