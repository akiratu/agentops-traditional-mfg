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
        <div className="text-[11px] font-medium uppercase text-muted-foreground">來源 Source</div>
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
            <SelectItem value="all">全部來源</SelectItem>
            <SelectItem value="metric_drift">Metric drift 指標偏移</SelectItem>
            <SelectItem value="cost_spike">Cost spike 成本爆增</SelectItem>
            <SelectItem value="human_flag">Human flag 人工標記</SelectItem>
            <SelectItem value="scheduled">Scheduled 排程</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <div className="text-[11px] font-medium uppercase text-muted-foreground">狀態 Status</div>
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
            <SelectItem value="all">全部狀態</SelectItem>
            <SelectItem value="new">New 新進</SelectItem>
            <SelectItem value="analyzing">Analyzing 分析中</SelectItem>
            <SelectItem value="resolved">Resolved 已解決</SelectItem>
            <SelectItem value="dismissed">Dismissed 已關閉</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
