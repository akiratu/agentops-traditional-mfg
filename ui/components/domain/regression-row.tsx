'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { relativeTime, shortId } from '@/lib/format'
import type { PerCaseResult, RegressionRunRead, RegressionVerdict } from '@/lib/types'

const VERDICT_STYLES: Record<RegressionVerdict, string> = {
  pass: 'bg-green-100 text-green-800',
  fail: 'bg-red-100 text-red-800',
  needs_review: 'bg-amber-100 text-amber-800',
}

const CASE_STYLES: Record<PerCaseResult['verdict'], string> = {
  resolved: 'text-green-700',
  partial: 'text-amber-700',
  still_broken: 'text-red-700',
}

export function RegressionRow({ run }: { run: RegressionRunRead }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded border border-border">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 p-3 text-left text-xs hover:bg-muted/40"
        data-testid={`regression-row-${run.id}`}
      >
        <div className="flex flex-1 items-center gap-2">
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase',
              VERDICT_STYLES[run.verdict]
            )}
          >
            {run.verdict}
          </span>
          <span className="font-mono text-[11px] text-muted-foreground">
            {shortId(run.skill_id_old, 6)} → {shortId(run.skill_id_new, 6)}
          </span>
          <span className="text-muted-foreground">
            通過 {run.pass_count}/{run.test_case_count} · 失敗 {run.fail_count} · 策略{' '}
            {run.test_set_strategy}
          </span>
        </div>
        <span className="text-muted-foreground">{relativeTime(run.created_at)}</span>
      </button>
      {open && (
        <div className="border-t border-border px-3 py-2">
          {run.regression_findings.length > 0 && (
            <div className="mb-2 rounded bg-amber-50 p-2 text-[11px] text-amber-900 dark:bg-amber-950/20 dark:text-amber-300">
              <strong>增量違規:</strong> {run.regression_findings.join('; ')}
            </div>
          )}
          {run.per_case_results.length === 0 ? (
            <p className="text-[11px] text-muted-foreground">無 per-case 結果記錄</p>
          ) : (
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="py-1 pr-2">Failure ID</th>
                  <th className="py-1 pr-2">判定 Verdict</th>
                  <th className="py-1">說明 Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {run.per_case_results.map((r) => (
                  <tr key={r.failure_id}>
                    <td className="py-1 pr-2 font-mono">{r.failure_id}</td>
                    <td className={cn('py-1 pr-2 font-semibold', CASE_STYLES[r.verdict])}>
                      {r.verdict}
                    </td>
                    <td className="py-1 text-muted-foreground">{r.reasoning ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
