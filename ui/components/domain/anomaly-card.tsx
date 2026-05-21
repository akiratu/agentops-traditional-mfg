'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/card'
import { StatusBadge } from './status-badge'
import { SourceTypeBadge } from './source-type-badge'
import { ConfidenceBadge } from './confidence-badge'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import { relativeTime, shortId } from '@/lib/format'
import type { AnomalySignalRead } from '@/lib/types'

export function AnomalyCard({ signal }: { signal: AnomalySignalRead }) {
  // Look up the first finding (if any) so we can show its confidence.
  const findingsQ = useQuery({
    queryKey: qk.findings(signal.id),
    queryFn: () => api.listFindings(signal.id),
    enabled: signal.status === 'resolved',
  })
  const firstFinding = findingsQ.data?.[0]
  const isAnalyzing = signal.status === 'analyzing'

  const inner = (
    <Card
      className={
        isAnalyzing
          ? 'cursor-wait opacity-70'
          : 'cursor-pointer transition-colors hover:border-foreground/30'
      }
    >
      <CardContent className="flex items-center justify-between gap-3 p-card">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex items-center gap-2">
            <SourceTypeBadge type={signal.source_type} />
            <StatusBadge status={signal.status} />
            {firstFinding && <ConfidenceBadge value={firstFinding.confidence_score} />}
          </div>
          <div className="truncate text-xs text-muted-foreground">
            Agent {shortId(signal.agent_id)} · {signal.related_trace_refs.length} traces
          </div>
        </div>
        <div className="text-xs text-muted-foreground">{relativeTime(signal.created_at)}</div>
      </CardContent>
    </Card>
  )

  if (firstFinding) {
    return (
      <Link href={`/findings/${firstFinding.id}`} className="block">
        {inner}
      </Link>
    )
  }
  return inner
}
