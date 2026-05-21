import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

export function ConfidenceBadge({ value }: { value: number }) {
  // Thresholds per spec §8.2: ≥0.7 green, 0.4 ≤ x < 0.7 amber, <0.4 red
  const tier = value >= 0.7 ? 'high' : value >= 0.4 ? 'mid' : 'low'
  const styles = {
    high: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    mid: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    low: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  }[tier]
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            data-tier={tier}
            className={cn(
              'inline-flex cursor-help items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
              styles
            )}
          >
            conf {value.toFixed(2)}
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="start" className="max-w-xs text-left">
          <div className="space-y-1 text-xs leading-relaxed">
            <p className="font-medium">AI 自評信心分數</p>
            <p>AI 對自己這次分析的把握程度,主管可依此決定要不要全信。</p>
            <ul className="ml-3 list-disc space-y-0.5">
              <li>🟢 ≥ 0.7 — 高信心,可直接 Accept</li>
              <li>🟡 0.4 – 0.7 — 中信心,主管再看一下</li>
              <li>🔴 &lt; 0.4 — 低信心,建議 Reject 或補資料重跑</li>
            </ul>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
