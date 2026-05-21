'use client'

import { useQuery } from '@tanstack/react-query'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { RegressionRow } from '@/components/domain/regression-row'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'

export default function RegressionRunsPage() {
  const query = useQuery({
    queryKey: qk.regressionRuns(),
    queryFn: () => api.listRegressionRuns(),
  })

  return (
    <div className="flex flex-col gap-4">
      <BreadcrumbNav crumbs={[{ label: 'Regression Runs' }]} />
      <h1 className="text-xl font-semibold">回歸測試 Regression Runs</h1>
      <DataState query={query} isEmpty={(d) => d.length === 0}>
        {(runs) => (
          <div className="flex flex-col gap-2">
            {[...runs]
              .sort((a, b) => b.created_at.localeCompare(a.created_at))
              .map((r) => (
                <RegressionRow key={r.id} run={r} />
              ))}
          </div>
        )}
      </DataState>
    </div>
  )
}
