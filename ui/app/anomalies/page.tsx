'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnomalyCard } from '@/components/domain/anomaly-card'
import { AnomalyFilters } from '@/components/domain/anomaly-filters'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { api } from '@/lib/api'
import { qk, type AnomalyFilters as Filters } from '@/lib/query-keys'

export default function AnomalyFeedPage() {
  const [filters, setFilters] = useState<Filters>({})

  // Backend only supports agent_id; source_type + status filter client-side
  // via TanStack Query's select (memoized by data reference).
  const query = useQuery({
    queryKey: qk.anomalySignals(filters),
    queryFn: () => api.listAnomalySignals({ agent_id: filters.agent_id }),
    refetchInterval: 5_000,
    select: (data) =>
      data.filter((s) => {
        if (filters.source_type && s.source_type !== filters.source_type) return false
        if (filters.status && s.status !== filters.status) return false
        return true
      }),
  })

  return (
    <div className="flex flex-col gap-4">
      <BreadcrumbNav crumbs={[{ label: 'Anomalies' }]} />
      <div className="flex items-end justify-between gap-4">
        <h1 className="text-xl font-semibold">Anomaly Feed</h1>
        <AnomalyFilters value={filters} onChange={setFilters} />
      </div>
      <DataState query={query} isEmpty={(d) => !d || d.length === 0}>
        {(signals) => (
          <div className="flex flex-col gap-2" data-testid="anomaly-list">
            {[...signals]
              .sort((a, b) => b.created_at.localeCompare(a.created_at))
              .map((s) => (
                <AnomalyCard key={s.id} signal={s} />
              ))}
          </div>
        )}
      </DataState>
    </div>
  )
}
