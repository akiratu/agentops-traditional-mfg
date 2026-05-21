'use client'

import { Check, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatusBadge } from './status-badge'
import type { RCAFindingStatus } from '@/lib/types'

type Props = {
  status: RCAFindingStatus
  onAccept: () => void
  onReject: () => void
  isPending: boolean
  hint?: string
}

export function DecisionPanel({ status, onAccept, onReject, isPending, hint }: Props) {
  const decided = status !== 'proposed'
  return (
    <div className="sticky top-2 flex flex-col gap-2 rounded border border-border bg-background p-3 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase text-muted-foreground">Decision</span>
        <StatusBadge status={status} />
      </div>
      <Button
        type="button"
        size="sm"
        className="h-9 w-full bg-green-600 text-white hover:bg-green-700"
        onClick={onAccept}
        disabled={decided || isPending}
        data-testid="accept-button"
      >
        <Check size={14} className="mr-1" aria-hidden /> Accept → Self-Evolve
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 w-full"
        onClick={onReject}
        disabled={decided || isPending}
        data-testid="reject-button"
      >
        <X size={14} className="mr-1" aria-hidden /> Reject
      </Button>
      {hint && <p className="mt-1 text-[11px] leading-snug text-muted-foreground">{hint}</p>}
    </div>
  )
}
