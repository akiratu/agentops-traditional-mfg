'use client'

import Link from 'next/link'
import { use } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import { relativeTime, shortId } from '@/lib/format'
import type { RuntimeStatus } from '@/lib/types'

const STATUSES: RuntimeStatus[] = ['pending', 'deploying', 'running', 'stopped', 'error']

export default function AgentDashboardPage({
  params,
}: {
  params: Promise<{ agentId: string }>
}) {
  const { agentId } = use(params)
  const qc = useQueryClient()

  const agentQ = useQuery({
    queryKey: qk.agent(agentId),
    queryFn: () => api.getAgent(agentId),
    refetchInterval: 10_000,
  })
  const skillsQ = useQuery({
    queryKey: qk.skills(agentId),
    queryFn: () => api.listSkills(agentId),
  })
  const anomaliesQ = useQuery({
    queryKey: qk.anomalySignals({ agent_id: agentId }),
    queryFn: () => api.listAnomalySignals({ agent_id: agentId }),
    refetchInterval: 10_000,
  })

  const mutateStatus = useMutation({
    mutationFn: (status: RuntimeStatus) =>
      api.patchAgentRuntimeStatus(agentId, { runtime_status: status }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.agent(agentId) })
      toast.success('Runtime status updated')
    },
    onError: (err) => toast.error(`Update failed: ${(err as Error).message}`),
  })

  const currentVersion = (() => {
    if (!agentQ.data?.current_skill_id) return null
    return skillsQ.data?.find((s) => s.id === agentQ.data?.current_skill_id)?.version ?? null
  })()

  return (
    <div className="flex flex-col gap-4">
      <DataState query={agentQ}>
        {(agent) => (
          <>
            <BreadcrumbNav
              crumbs={[
                { href: '/factories', label: 'Factories' },
                { href: `/factories/${agent.factory_id}`, label: shortId(agent.factory_id) },
                { label: agent.name },
              ]}
            />
            <Card>
              <CardHeader className="p-card pb-2">
                <CardTitle className="flex items-center justify-between text-base">
                  <span>{agent.name}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[11px]">
                      v{currentVersion ?? '?'}
                    </Badge>
                    <Select
                      value={agent.runtime_status}
                      onValueChange={(v) => mutateStatus.mutate(v as RuntimeStatus)}
                    >
                      <SelectTrigger className="h-7 w-32 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STATUSES.map((s) => (
                          <SelectItem key={s} value={s} className="text-xs">
                            {s}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-card pt-0 text-xs text-muted-foreground">
                <div>{agent.purpose}</div>
                <div>
                  Deployed: {agent.deployed_at ? relativeTime(agent.deployed_at) : 'not yet'}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </DataState>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-medium">Recent Anomalies</h2>
          <DataState query={anomaliesQ} isEmpty={(d) => d.length === 0}>
            {(signals) => (
              <ul className="flex flex-col gap-1">
                {signals.slice(0, 10).map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between rounded border border-border px-2 py-1.5 text-xs"
                  >
                    <span className="truncate">
                      {s.source_type} · {s.status}
                    </span>
                    <span className="text-muted-foreground">{relativeTime(s.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </DataState>
          <Link
            href="/anomalies"
            className="mt-2 inline-block text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            View all anomalies →
          </Link>
        </div>

        <div>
          <h2 className="mb-2 text-sm font-medium">Skill Versions</h2>
          <DataState query={skillsQ} isEmpty={(d) => d.length === 0}>
            {(skills) => (
              <ul className="flex flex-col gap-1">
                {[...skills]
                  .sort((a, b) => b.version - a.version)
                  .slice(0, 5)
                  .map((s) => (
                    <li
                      key={s.id}
                      className="flex items-center justify-between rounded border border-border px-2 py-1.5 text-xs"
                    >
                      <span>
                        v{s.version} · {s.status}
                      </span>
                      <span className="text-muted-foreground">{relativeTime(s.created_at)}</span>
                    </li>
                  ))}
              </ul>
            )}
          </DataState>
          <Link
            href={`/skills/${agentId}`}
            className="mt-2 inline-block text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            View skill timeline + diff →
          </Link>
        </div>
      </div>
    </div>
  )
}
