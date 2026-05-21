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
    <span
      data-tier={tier}
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
        styles
      )}
    >
      conf {value.toFixed(2)}
    </span>
  )
}
