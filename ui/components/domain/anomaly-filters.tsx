'use client'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { InfoHint } from '@/components/ui/info-hint'
import type { AnomalyFilters as Filters } from '@/lib/query-keys'

type Props = {
  value: Filters
  onChange: (next: Filters) => void
}

export function AnomalyFilters({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <div className="flex items-center gap-1 text-[11px] font-medium uppercase text-muted-foreground">
          來源 Source
          <InfoHint>
            <div className="space-y-1.5 text-xs leading-relaxed">
              <p className="font-medium">異常怎麼被發現的(4 種進入管道):</p>
              <ul className="ml-3 list-disc space-y-1">
                <li><b>Metric drift 指標偏移</b> — 系統自動偵測 KPI 偏離正常區間(良率掉、UPH 降)</li>
                <li><b>Cost spike 成本爆增</b> — 系統自動偵測 LLM / API 成本暴漲</li>
                <li><b>Human flag 人工標記</b> — 主管 / 工程師 / 線上人員手動報修</li>
                <li><b>Scheduled 排程</b> — 定時自動健康檢查(例如每天早上 8 點掃一次)</li>
              </ul>
            </div>
          </InfoHint>
        </div>
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
        <div className="flex items-center gap-1 text-[11px] font-medium uppercase text-muted-foreground">
          狀態 Status
          <InfoHint>
            <div className="space-y-1.5 text-xs leading-relaxed">
              <p className="font-medium">異常從進來到處理完的 4 個階段:</p>
              <ul className="ml-3 list-disc space-y-1">
                <li><b>New 新進</b> — 剛偵測到,還沒分析</li>
                <li><b>Analyzing 分析中</b> — AI 在跑根因分析(1-3 分鐘)</li>
                <li><b>Resolved 已解決</b> — 分析完成,產出 RCA finding 可看</li>
                <li><b>Dismissed 已關閉</b> — 主管判定不需處理 / 誤報</li>
              </ul>
            </div>
          </InfoHint>
        </div>
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
