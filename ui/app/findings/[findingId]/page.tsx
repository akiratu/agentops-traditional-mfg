'use client'

import { use, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { NotebookViewer } from '@/components/domain/notebook-viewer'
import { FailureCaseCard } from '@/components/domain/failure-case-card'
import { DecisionPanel } from '@/components/domain/decision-panel'
import { ConfidenceBadge } from '@/components/domain/confidence-badge'
import { SourceTypeBadge } from '@/components/domain/source-type-badge'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import { relativeTime, shortId } from '@/lib/format'
import type { SkillRead } from '@/lib/types'

const ACCEPT_POLL_WINDOW_MS = 5 * 60 * 1000

export default function FindingDetailPage({
  params,
}: {
  params: Promise<{ findingId: string }>
}) {
  const { findingId } = use(params)
  const qc = useQueryClient()
  const acceptedAtRef = useRef<number | null>(null)
  const [pollExpired, setPollExpired] = useState(false)

  const findingQ = useQuery({
    queryKey: qk.finding(findingId),
    queryFn: () => api.getFinding(findingId),
    refetchInterval: (q) => {
      const data = q.state.data
      if (!data || data.status !== 'accepted') return false
      if (!acceptedAtRef.current) acceptedAtRef.current = Date.now()
      if (Date.now() - acceptedAtRef.current > ACCEPT_POLL_WINDOW_MS) {
        if (!pollExpired) setPollExpired(true)
        return false
      }
      return 5_000
    },
  })

  const signalQ = useQuery({
    queryKey: ['anomaly-signals', findingQ.data?.anomaly_signal_id],
    enabled: !!findingQ.data,
    queryFn: () => api.getAnomalySignal(findingQ.data!.anomaly_signal_id),
  })

  const agentId = signalQ.data?.agent_id

  // Skill polling: only active right after accept; stops once a newer skill appears.
  const skillsBefore = useRef<Map<string, SkillRead> | null>(null)
  const skillsQ = useQuery({
    queryKey: agentId ? qk.skills(agentId) : ['skills', 'pending'],
    enabled: !!agentId,
    queryFn: () => api.listSkills(agentId!),
    refetchInterval: (q) => {
      if (!findingQ.data) return false
      if (findingQ.data.status !== 'accepted') return false
      if (pollExpired) return false
      const cur = q.state.data
      if (!cur) return 5_000
      if (!skillsBefore.current) {
        skillsBefore.current = new Map(cur.map((s) => [s.id, s]))
      }
      const newSkill = cur.find((s) => !skillsBefore.current?.has(s.id))
      return newSkill ? false : 5_000
    },
  })

  const newSkill = useMemo(() => {
    if (!skillsQ.data || !skillsBefore.current) return null
    return skillsQ.data.find((s) => !skillsBefore.current?.has(s.id)) ?? null
  }, [skillsQ.data])

  useEffect(() => {
    if (newSkill) {
      toast.success(`Skill v${newSkill.version} 已產生 — 前往 Skill Timeline 檢視`)
    }
  }, [newSkill])

  const acceptM = useMutation({
    mutationFn: () => api.patchFindingStatus(findingId, { status: 'accepted' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.finding(findingId) })
      toast.success('Accepted — Self-Evolve 已啟動,~4 分鐘後完成')
    },
    onError: (err) => toast.error(`Accept failed: ${(err as Error).message}`),
  })
  const rejectM = useMutation({
    mutationFn: () => api.patchFindingStatus(findingId, { status: 'rejected' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.finding(findingId) })
      toast.message('Rejected')
    },
    onError: (err) => toast.error(`Reject failed: ${(err as Error).message}`),
  })

  return (
    <div className="flex flex-col gap-4">
      <DataState query={findingQ}>
        {(f) => {
          const failures = f.suggested_fix_payload.failure_cases ?? []
          return (
            <>
              <BreadcrumbNav
                crumbs={[
                  { href: '/anomalies', label: 'Anomalies' },
                  { label: `Finding ${shortId(f.id)}` },
                ]}
              />
              <header className="flex flex-col gap-2 rounded border border-border bg-background p-card">
                <div className="flex flex-wrap items-center gap-2">
                  {signalQ.data && <SourceTypeBadge type={signalQ.data.source_type} />}
                  <ConfidenceBadge value={f.confidence_score} />
                  <span className="text-xs text-muted-foreground">
                    Anomaly {shortId(f.anomaly_signal_id)} · {relativeTime(f.created_at)}
                  </span>
                </div>
                <h1 className="text-base font-semibold leading-snug">
                  {f.root_cause_summary.split('\n')[0]}
                </h1>
              </header>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
                <section className="flex flex-col gap-3">
                  <h2 className="text-sm font-medium">📓 Notebook</h2>
                  <NotebookViewer markdown={f.evidence.notebook ?? ''} />
                  <div className="text-[11px] text-muted-foreground">
                    {f.evidence.plan_steps_completed != null && (
                      <>plan steps: {f.evidence.plan_steps_completed} · </>
                    )}
                    {f.evidence.total_iterations != null && (
                      <>iterations: {f.evidence.total_iterations} · </>
                    )}
                    {f.evidence.termination && <>termination: {f.evidence.termination}</>}
                  </div>
                </section>

                <aside className="flex flex-col gap-3">
                  <h2 className="text-sm font-medium">⚠️ {failures.length} Failure Cases</h2>
                  <div className="flex flex-col gap-2">
                    {failures.map((fc) => (
                      <FailureCaseCard key={fc.id} failureCase={fc} />
                    ))}
                    {failures.length === 0 && (
                      <p className="text-xs text-muted-foreground">No failure cases recorded.</p>
                    )}
                  </div>
                  <DecisionPanel
                    status={f.status}
                    isPending={acceptM.isPending || rejectM.isPending}
                    onAccept={() => acceptM.mutate()}
                    onReject={() => rejectM.mutate()}
                    hint={
                      f.status === 'accepted'
                        ? pollExpired
                          ? 'Self-Evolve 仍在處理 — 手動 refresh 重試,或到 Skill Timeline 檢查'
                          : '等候 Self-Evolve 完成 (polling 5s)'
                        : undefined
                    }
                  />
                </aside>
              </div>
            </>
          )
        }}
      </DataState>
    </div>
  )
}
