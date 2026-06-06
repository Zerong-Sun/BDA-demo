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
    <div className="overflow-x-auto rounded-lg border border-bda-border bg-bda-panel">
      <table className="min-w-full text-sm">
        <thead className="border-b border-bda-border bg-bda-bg text-left text-xs uppercase tracking-wide text-bda-muted">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="cursor-pointer px-3 py-2"
                  onClick={header.column.getToggleSortingHandler()}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {{
                    asc: ' ↑',
                    desc: ' ↓',
                  }[header.column.getIsSorted() as string] ?? null}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={`cursor-pointer border-b border-bda-border/60 hover:bg-bda-panel-hover ${
                selectedId === row.original.candidate_id
                  ? 'bg-bda-cyan/10 border-l-2 border-l-bda-cyan'
                  : ''
              }`}
              onClick={() => onSelect(row.original)}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 ? (
        <div className="p-6 text-center text-sm text-bda-muted">No candidates match the current filters.</div>
      ) : null}
    </div>
  )
}
