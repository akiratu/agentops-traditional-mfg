import { ExternalLink } from 'lucide-react'
import type { FailureCase } from '@/lib/types'

export function FailureCaseCard({
  failureCase: fc,
  langfuseTraceUrl,
}: {
  failureCase: FailureCase
  langfuseTraceUrl?: string
}) {
  return (
    <div className="rounded border border-red-200 bg-red-50 p-3 text-xs dark:border-red-900/40 dark:bg-red-950/20">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] font-semibold text-red-900 dark:text-red-300">
          ⚠️ {fc.id}
        </span>
        {langfuseTraceUrl && (
          <a
            href={langfuseTraceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
          >
            View trace in Langfuse <ExternalLink size={10} aria-hidden />
          </a>
        )}
      </div>
      <dl className="flex flex-col gap-1.5 text-[11px] leading-snug">
        <div>
          <dt className="font-semibold text-muted-foreground">Query</dt>
          <dd>{fc.query}</dd>
        </div>
        <div>
          <dt className="font-semibold text-green-700 dark:text-green-400">Expected</dt>
          <dd>{fc.expected_outcome}</dd>
        </div>
        <div>
          <dt className="font-semibold text-red-700 dark:text-red-400">Actual</dt>
          <dd>{fc.actual_outcome}</dd>
        </div>
        {fc.context && (
          <div>
            <dt className="font-semibold text-muted-foreground">Context</dt>
            <dd className="text-muted-foreground">{fc.context}</dd>
          </div>
        )}
      </dl>
    </div>
  )
}
