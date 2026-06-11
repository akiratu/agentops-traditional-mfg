'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Factory as FactoryIcon,
  GitCompare,
  ListChecks,
  TrendingUp,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { StatusBadge } from '@/components/domain/status-badge'
import { SourceTypeBadge } from '@/components/domain/source-type-badge'
import { ConfidenceBadge } from '@/components/domain/confidence-badge'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import { relativeTime, shortId } from '@/lib/format'
import type { AnomalySignalRead, RCAFindingRead } from '@/lib/types'

export default function DashboardPage() {
  const factoriesQ = useQuery({
    queryKey: qk.factories(),
    queryFn: () => api.listFactories(),
    refetchInterval: 30_000,
  })
  const agentsQ = useQuery({
    queryKey: qk.agents(),
    queryFn: () => api.listAgents(),
    refetchInterval: 30_000,
  })
  const anomaliesQ = useQuery({
    queryKey: qk.anomalySignals({}),
    queryFn: () => api.listAnomalySignals({}),
    refetchInterval: 10_000,
  })
  const findingsQ = useQuery({
    queryKey: qk.findings(),
    queryFn: () => api.listFindings(),
    refetchInterval: 10_000,
  })
  const regressionsQ = useQuery({
    queryKey: qk.regressionRuns(),
    queryFn: () => api.listRegressionRuns(),
    refetchInterval: 30_000,
  })

  // KPI computations
  const factoryCount = factoriesQ.data?.length ?? 0
  const agentCount = agentsQ.data?.length ?? 0
  const runningAgents = agentsQ.data?.filter((a) => a.runtime_status === 'running').length ?? 0
  const pendingFindings = findingsQ.data?.filter((f) => f.status === 'proposed').length ?? 0
  const acceptedFindings = findingsQ.data?.filter((f) => f.status === 'accepted').length ?? 0
  const totalRegressions = regressionsQ.data?.length ?? 0
  const passedRegressions = regressionsQ.data?.filter((r) => r.verdict === 'pass').length ?? 0
  const passRate = totalRegressions > 0 ? Math.round((passedRegressions / totalRegressions) * 100) : 0

  // Build agent label map for richer activity rows
  const agentMap = new Map(agentsQ.data?.map((a) => [a.id, a.name]) ?? [])
  const factoryMap = new Map(factoriesQ.data?.map((f) => [f.id, f.name]) ?? [])
  const factoryOfAgent = new Map(
    agentsQ.data?.map((a) => [a.id, factoryMap.get(a.factory_id) ?? '—']) ?? []
  )

  const recentAnomalies = (anomaliesQ.data ?? [])
    .slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 6)

  const recentFindings = (findingsQ.data ?? [])
    .slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 6)

  return (
    <div className="flex flex-col gap-5">
      <BreadcrumbNav crumbs={[{ label: '總覽 Overview' }]} />
      <div>
        <h1 className="text-xl font-semibold">AgentOps 平台總覽 Overview</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          整合 3 個政府計畫場域(金屬加工 / 半導體封測 / 客服)的 AI agent 統一管理平台。
          下方數字每 10-30 秒自動更新。
        </p>
      </div>

      {/* KPI cards row */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <KpiCard
          icon={<FactoryIcon size={14} />}
          label="場域 Factories"
          value={factoryCount}
          sub="政府計畫整合場域"
          query={factoriesQ}
        />
        <KpiCard
          icon={<Bot size={14} />}
          label="部署中 Agents"
          value={`${runningAgents}/${agentCount}`}
          sub="running / 全部"
          query={agentsQ}
        />
        <KpiCard
          icon={<AlertTriangle size={14} />}
          label="累計異常 Anomalies"
          value={anomaliesQ.data?.length ?? 0}
          sub="所有 source / status"
          query={anomaliesQ}
        />
        <KpiCard
          icon={<ListChecks size={14} />}
          label="待主管處理 Findings"
          value={pendingFindings}
          sub={`${acceptedFindings} 已接受`}
          query={findingsQ}
          highlight={pendingFindings > 0}
        />
        <KpiCard
          icon={<GitCompare size={14} />}
          label="回歸測試 Runs"
          value={totalRegressions}
          sub={`${passedRegressions} PASS`}
          query={regressionsQ}
        />
        <KpiCard
          icon={<TrendingUp size={14} />}
          label="通過率 Pass Rate"
          value={`${passRate}%`}
          sub="Self-Evolve 品質"
          query={regressionsQ}
          highlight={passRate >= 90}
        />
      </div>

      {/* 2-column activity */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-medium">最近異常 Recent Anomalies</h2>
            <Link href="/anomalies" className="text-xs text-primary underline-offset-4 hover:underline">
              看全部 →
            </Link>
          </div>
          <DataState query={anomaliesQ} isEmpty={(d) => d.length === 0}>
            {() => (
              <ul className="flex flex-col gap-1.5">
                {recentAnomalies.map((s) => (
                  <AnomalyRow
                    key={s.id}
                    signal={s}
                    agentLabel={agentMap.get(s.agent_id) ?? shortId(s.agent_id)}
                    factoryLabel={factoryOfAgent.get(s.agent_id) ?? '—'}
                    finding={findingsQ.data?.find((f) => f.anomaly_signal_id === s.id)}
                  />
                ))}
              </ul>
            )}
          </DataState>
        </section>

        <section>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-medium">最近 RCA Finding</h2>
            <Link
              href="/anomalies"
              className="text-xs text-primary underline-offset-4 hover:underline"
            >
              看異常列表 →
            </Link>
          </div>
          <DataState query={findingsQ} isEmpty={(d) => d.length === 0}>
            {() => (
              <ul className="flex flex-col gap-1.5">
                {recentFindings.map((f) => {
                  const signal = anomaliesQ.data?.find((s) => s.id === f.anomaly_signal_id)
                  const agentName = signal ? agentMap.get(signal.agent_id) : undefined
                  return (
                    <FindingRow
                      key={f.id}
                      finding={f}
                      agentLabel={agentName ?? '—'}
                      factoryLabel={
                        signal ? factoryOfAgent.get(signal.agent_id) ?? '—' : '—'
                      }
                    />
                  )
                })}
              </ul>
            )}
          </DataState>
        </section>
      </div>

      {/* Factory health row */}
      <section>
        <h2 className="mb-2 text-sm font-medium">場域健康 Factory Health</h2>
        <DataState query={factoriesQ} isEmpty={(d) => d.length === 0}>
          {(factories) => (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {factories.map((f) => {
                const factoryAgents = agentsQ.data?.filter((a) => a.factory_id === f.id) ?? []
                const factorySignals = anomaliesQ.data?.filter((s) =>
                  factoryAgents.some((a) => a.id === s.agent_id)
                ) ?? []
                const factoryFindings = findingsQ.data?.filter((fd) =>
                  factorySignals.some((s) => s.id === fd.anomaly_signal_id)
                ) ?? []
                const proposed = factoryFindings.filter((fd) => fd.status === 'proposed').length
                return (
                  <Link key={f.id} href={`/factories/${f.id}`} className="block">
                    <Card className="hover:border-foreground/30">
                      <CardContent className="flex flex-col gap-2 p-card">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold">{f.name}</span>
                          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] uppercase tracking-wide">
                            {f.deployment_type}
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div>
                            <div className="text-muted-foreground">Agents</div>
                            <div className="font-medium">{factoryAgents.length}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">異常</div>
                            <div className="font-medium">{factorySignals.length}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">待處理</div>
                            <div
                              className={
                                proposed > 0
                                  ? 'font-medium text-orange-700 dark:text-orange-400'
                                  : 'font-medium'
                              }
                            >
                              {proposed}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                )
              })}
            </div>
          )}
        </DataState>
      </section>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function KpiCard({
  icon,
  label,
  value,
  sub,
  highlight,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  sub: string
  query: { isPending: boolean }
  highlight?: boolean
}) {
  return (
    <Card
      className={
        highlight
          ? 'border-green-300 bg-green-50/50 dark:border-green-900/40 dark:bg-green-950/10'
          : ''
      }
    >
      <CardContent className="flex flex-col gap-1 p-card">
        <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {icon}
          {label}
        </div>
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
        <div className="text-[11px] text-muted-foreground">{sub}</div>
      </CardContent>
    </Card>
  )
}

function AnomalyRow({
  signal,
  agentLabel,
  factoryLabel,
  finding,
}: {
  signal: AnomalySignalRead
  agentLabel: string
  factoryLabel: string
  finding?: RCAFindingRead
}) {
  const inner = (
    <div className="flex items-center justify-between gap-2 rounded border border-border bg-background p-2 text-xs hover:border-foreground/30">
      <div className="flex min-w-0 flex-col gap-0.5">
        <div className="flex items-center gap-1.5">
          <SourceTypeBadge type={signal.source_type} />
          <StatusBadge status={signal.status} />
          {finding && <ConfidenceBadge value={finding.confidence_score} />}
        </div>
        <div className="truncate text-[11px] text-foreground">
          <span className="font-medium">{agentLabel}</span>
          <span className="text-muted-foreground"> · {factoryLabel}</span>
        </div>
      </div>
      <span className="shrink-0 text-[11px] text-muted-foreground">
        {relativeTime(signal.created_at)}
      </span>
    </div>
  )
  return finding ? (
    <li>
      <Link href={`/findings/${finding.id}`}>{inner}</Link>
    </li>
  ) : (
    <li>{inner}</li>
  )
}

function FindingRow({
  finding,
  agentLabel,
  factoryLabel,
}: {
  finding: RCAFindingRead
  agentLabel: string
  factoryLabel: string
}) {
  const summary = finding.root_cause_summary.split('\n')[0]?.slice(0, 90) ?? ''
  return (
    <li>
      <Link href={`/findings/${finding.id}`}>
        <div className="flex flex-col gap-1 rounded border border-border bg-background p-2 text-xs hover:border-foreground/30">
          <div className="flex items-center gap-1.5">
            <StatusBadge status={finding.status} />
            <ConfidenceBadge value={finding.confidence_score} />
            <span className="ml-auto inline-flex items-center gap-1 text-[11px] text-muted-foreground">
              {finding.status === 'accepted' && <CheckCircle2 size={11} className="text-green-600" />}
              {relativeTime(finding.created_at)}
            </span>
          </div>
          <div className="truncate text-[11px]">
            <span className="font-medium">{agentLabel}</span>
            <span className="text-muted-foreground"> · {factoryLabel}</span>
          </div>
          <div className="line-clamp-1 text-[11px] text-foreground">{summary}</div>
        </div>
      </Link>
    </li>
  )
}
