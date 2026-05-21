import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AnomalyStatus, RCAFindingStatus, SkillStatus } from '@/lib/types'

type Status = AnomalyStatus | RCAFindingStatus | SkillStatus

const STYLES: Record<Status, string> = {
  // anomaly
  new: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  analyzing: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  dismissed: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400',
  // finding
  proposed: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  accepted: 'bg-green-200 text-green-900 dark:bg-green-900/40 dark:text-green-200',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  auto_applied: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  // skill
  draft: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  archived: 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-500',
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span
      data-status={status}
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide',
        STYLES[status]
      )}
    >
      {status === 'analyzing' && <Loader2 size={10} className="animate-spin" aria-hidden />}
      {status}
    </span>
  )
}
