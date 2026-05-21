import { cn } from '@/lib/utils'
import type { AnomalySourceType } from '@/lib/types'

const STYLES: Record<AnomalySourceType, string> = {
  metric_drift: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  cost_spike: 'bg-orange-200 text-orange-900 dark:bg-orange-900/30 dark:text-orange-300',
  human_flag: 'bg-red-200 text-red-900 dark:bg-red-900/30 dark:text-red-200',
  scheduled: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
}

export function SourceTypeBadge({ type }: { type: AnomalySourceType }) {
  return (
    <span
      data-source-type={type}
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide',
        STYLES[type]
      )}
    >
      {type.replace('_', ' ')}
    </span>
  )
}
