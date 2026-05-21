import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { AnomalySourceType } from '@/lib/types'

const STYLES: Record<AnomalySourceType, string> = {
  metric_drift: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  cost_spike: 'bg-orange-200 text-orange-900 dark:bg-orange-900/30 dark:text-orange-300',
  human_flag: 'bg-red-200 text-red-900 dark:bg-red-900/30 dark:text-red-200',
  scheduled: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
}

const EXPLANATIONS: Record<AnomalySourceType, string> = {
  metric_drift: '系統自動偵測 KPI 偏離正常區間(例如:良率掉、UPH 降)',
  cost_spike: '系統自動偵測 LLM / API 成本暴漲',
  human_flag: '主管 / 工程師 / 線上人員手動報修',
  scheduled: '定時自動健康檢查(例如:每天早上 8 點掃一次)',
}

export function SourceTypeBadge({ type }: { type: AnomalySourceType }) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            data-source-type={type}
            className={cn(
              'inline-flex cursor-help items-center rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide',
              STYLES[type]
            )}
          >
            {type.replace('_', ' ')}
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="start" className="max-w-xs text-left">
          <p className="text-xs leading-relaxed">{EXPLANATIONS[type]}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
