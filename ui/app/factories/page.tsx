'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'

export default function FactoriesPage() {
  const query = useQuery({
    queryKey: qk.factories(),
    queryFn: () => api.listFactories(),
    refetchInterval: 30_000,
  })

  return (
    <div className="flex flex-col gap-4">
      <BreadcrumbNav crumbs={[{ label: 'Factories' }]} />
      <h1 className="text-xl font-semibold">Factories</h1>
      <DataState query={query} isEmpty={(d) => d.length === 0}>
        {(factories) => (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {factories.map((f) => (
              <Link key={f.id} href={`/factories/${f.id}`} className="block">
                <Card className="hover:border-foreground/30">
                  <CardHeader className="p-card pb-2">
                    <CardTitle className="flex items-center justify-between text-base">
                      {f.name}
                      <Badge variant="outline" className="text-[11px]">
                        {f.deployment_type}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-card pt-0 text-xs text-muted-foreground">
                    {f.kpi_targets && Object.keys(f.kpi_targets).length > 0
                      ? `${Object.keys(f.kpi_targets).length} KPI targets`
                      : 'No KPI targets'}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </DataState>
    </div>
  )
}
