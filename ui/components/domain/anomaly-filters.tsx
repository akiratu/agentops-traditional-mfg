'use client'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { AnomalyFilters as Filters } from '@/lib/query-keys'

type Props = {
  value: Filters
  onChange: (next: Filters) => void
}

export function AnomalyFilters({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <div className="text-[11px] font-medium uppercase text-muted-foreground">Source</div>
        <Select
          value={value.source_type ?? 'all'}
          onValueChange={(v) =>
            onChange({
              ...value,
              source_type:
                v === 'all'
                  ? undefined
                  : (v as NonNullable<Filters['source_type']>),
            })
          }
        >
          <SelectTrigger className="h-7 w-40 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sources</SelectItem>
            <SelectItem value="metric_drift">Metric drift</SelectItem>
            <SelectItem value="cost_spike">Cost spike</SelectItem>
            <SelectItem value="human_flag">Human flag</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <div className="text-[11px] font-medium uppercase text-muted-foreground">Status</div>
        <Select
          value={value.status ?? 'all'}
          onValueChange={(v) =>
            onChange({
              ...value,
              status:
                v === 'all'
                  ? undefined
                  : (v as NonNullable<Filters['status']>),
            })
          }
        >
          <SelectTrigger className="h-7 w-40 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="new">New</SelectItem>
            <SelectItem value="analyzing">Analyzing</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="dismissed">Dismissed</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
