'use client'

import Link from 'next/link'
import { ArrowRight, Check, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { StatusBadge } from './status-badge'
import type { RCAFindingStatus } from '@/lib/types'

type Props = {
  status: RCAFindingStatus
  onAccept: () => void
  onReject: () => void
  isPending: boolean
  hint?: ReactNode
  /** When set, render a primary CTA "看新版 Skill v_next →" linking here. */
  skillTimelineHref?: string
}

export function DecisionPanel({
  status,
  onAccept,
  onReject,
  isPending,
  hint,
  skillTimelineHref,
}: Props) {
  const decided = status !== 'proposed'
  return (
    <div className="sticky top-2 flex flex-col gap-2 rounded border border-border bg-background p-3 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase text-muted-foreground">決策 Decision</span>
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
        <Check size={14} className="mr-1" aria-hidden /> 接受 → Self-Evolve
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
        <X size={14} className="mr-1" aria-hidden /> 拒絕 Reject
      </Button>
      {skillTimelineHref && (
        <Link
          href={skillTimelineHref}
          className="mt-1 inline-flex items-center justify-center gap-1 rounded border border-green-600 px-2 py-1.5 text-xs font-medium text-green-700 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-950/30"
          data-testid="goto-skill-timeline"
        >
          看新版 Skill v_next <ArrowRight size={12} aria-hidden />
        </Link>
      )}
      {hint && <p className="mt-1 text-[11px] leading-snug text-muted-foreground">{hint}</p>}
    </div>
  )
}
