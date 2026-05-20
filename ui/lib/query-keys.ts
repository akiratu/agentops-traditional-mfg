import type { AnomalySourceType, AnomalyStatus, UUID } from './types'

/**
 * Client-side filter shape for the anomaly feed page.
 * Only agent_id hits the backend today; source_type / status are
 * applied via TanStack Query select() in the feed component.
 */
export type AnomalyFilters = {
  agent_id?: UUID
  source_type?: AnomalySourceType
  status?: AnomalyStatus
}

export const qk = {
  factories: () => ['factories'] as const,
  factory: (id: UUID) => ['factories', id] as const,
  agents: (factoryId?: UUID) =>
    factoryId ? (['agents', { factoryId }] as const) : (['agents'] as const),
  agent: (id: UUID) => ['agents', id] as const,
  skills: (agentId?: UUID) =>
    agentId ? (['skills', { agentId }] as const) : (['skills'] as const),
  skill: (id: UUID) => ['skills', id] as const,
  anomalySignals: (filters: AnomalyFilters) =>
    ['anomaly-signals', filters] as const,
  finding: (id: UUID) => ['rca-findings', id] as const,
  findings: (anomalySignalId?: UUID) =>
    anomalySignalId
      ? (['rca-findings', { anomalySignalId }] as const)
      : (['rca-findings'] as const),
  regressionRuns: () => ['regression-runs'] as const,
  regressionRun: (id: UUID) => ['regression-runs', id] as const,
}
