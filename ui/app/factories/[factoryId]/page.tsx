'use client'

import Link from 'next/link'
import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import { relativeTime, shortId } from '@/lib/format'

export default function FactoryDetailPage({
  params,
}: {
  params: Promise<{ factoryId: string }>
}) {
  const { factoryId } = use(params)
  const factoryQ = useQuery({
    queryKey: qk.factory(factoryId),
    queryFn: () => api.getFactory(factoryId),
  })
  const agentsQ = useQuery({
    queryKey: qk.agents(factoryId),
    queryFn: () => api.listAgents(factoryId),
  })

  return (
    <div className="flex flex-col gap-4">
      <BreadcrumbNav
        crumbs={[
          { href: '/factories', label: 'Factories' },
          { label: factoryQ.data?.name ?? shortId(factoryId) },
        ]}
      />
      <DataState query={factoryQ}>
        {(f) => (
          <Card>
            <CardHeader className="p-card pb-2">
              <CardTitle className="flex items-center justify-between text-base">
                {f.name}
                <Badge variant="outline">{f.deployment_type}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-card pt-0 text-xs text-muted-foreground">
              <div>Langfuse 端點: {f.langfuse_endpoint ?? '—'}</div>
              <div>專案: {f.langfuse_project_id ?? '—'}</div>
              <div>更新時間: {relativeTime(f.updated_at)}</div>
            </CardContent>
          </Card>
        )}
      </DataState>

      <h2 className="mt-2 text-sm font-medium">Agent 清單</h2>
      <DataState query={agentsQ} isEmpty={(d) => d.length === 0}>
        {(agents) => (
          <Table>
            <TableHeader>
              <TableRow className="h-9">
                <TableHead>名稱</TableHead>
                <TableHead>用途</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>當前 Skill</TableHead>
                <TableHead>更新時間</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agents.map((a) => (
                <TableRow key={a.id} className="h-9">
                  <TableCell className="font-medium">
                    <Link href={`/agents/${a.id}`} className="underline-offset-2 hover:underline">
                      {a.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{a.purpose}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[11px]">
                      {a.runtime_status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {a.current_skill_id ? a.current_skill_id.slice(0, 8) : '—'}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {relativeTime(a.updated_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DataState>
    </div>
  )
}
