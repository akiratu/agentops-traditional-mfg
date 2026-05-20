// Mirrors agentops_core schemas. Update in lockstep if backend models change.
// Source: packages/agentops_core/models/*.py + schemas/failure_case.py

export type UUID = string
export type ISODateTime = string

// --- Factory ---
export type DeploymentType = 'on_prem' | 'private_cloud'
export interface FactoryRead {
  id: UUID
  name: string
  deployment_type: DeploymentType
  langfuse_endpoint: string | null
  langfuse_project_id: string | null
  contact_info: Record<string, unknown> | null
  kpi_targets: Record<string, unknown> | null
  created_at: ISODateTime
  updated_at: ISODateTime
}

// --- Agent ---
export type RuntimeStatus = 'pending' | 'deploying' | 'running' | 'stopped' | 'error'
export interface AgentRead {
  id: UUID
  factory_id: UUID
  name: string
  purpose: string
  current_skill_id: UUID | null
  runtime_status: RuntimeStatus
  deployed_at: ISODateTime | null
  created_at: ISODateTime
  updated_at: ISODateTime
}
export interface AgentRuntimeStatusUpdate {
  runtime_status: RuntimeStatus
}
export interface AgentCurrentSkillUpdate {
  current_skill_id: UUID | null
}

// --- Skill ---
export type SkillStatus = 'draft' | 'active' | 'archived'
export interface SkillRead {
  id: UUID
  agent_id: UUID
  version: number
  status: SkillStatus
  prompt: string
  tool_specs: Array<Record<string, unknown>>
  golden_test_cases: Array<Record<string, unknown>>
  sop_source_set_id: string
  generated_by_run_id: string | null
  created_at: ISODateTime
  updated_at: ISODateTime
}
export interface SkillStatusUpdate {
  status: SkillStatus
}

// --- AnomalySignal ---
export type AnomalySourceType = 'metric_drift' | 'cost_spike' | 'human_flag' | 'scheduled'
export type AnomalyStatus = 'new' | 'analyzing' | 'resolved' | 'dismissed'
export interface AnomalySignalRead {
  id: UUID
  agent_id: UUID
  source_type: AnomalySourceType
  related_trace_refs: string[]
  status: AnomalyStatus
  created_at: ISODateTime
  updated_at: ISODateTime
}

// --- RCAFinding ---
export type SuggestedFixType =
  | 'prompt_change'
  | 'add_skill'
  | 'supplement_sop'
  | 'swap_model'
  | 'retraining'
export type RCAFindingStatus = 'proposed' | 'accepted' | 'rejected' | 'auto_applied'
export interface FailureCase {
  id: string
  query: string
  expected_outcome: string
  actual_outcome: string
  context: string | null
}
export interface RCAFindingEvidence {
  notebook?: string
  failure_case_ids?: string[]
  plan_steps_completed?: number
  total_iterations?: number
  termination?: string
}
export interface RCAFindingRead {
  id: UUID
  anomaly_signal_id: UUID
  root_cause_summary: string
  evidence: RCAFindingEvidence
  suggested_fix_type: SuggestedFixType
  suggested_fix_payload: { failure_cases?: FailureCase[] }
  confidence_score: number
  status: RCAFindingStatus
  created_at: ISODateTime
  updated_at: ISODateTime
}
export interface RCAFindingStatusUpdate {
  status: RCAFindingStatus
}

// --- RegressionRun ---
export type TestSetStrategy = 'replay_recent' | 'golden' | 'mixed'
export type RegressionVerdict = 'pass' | 'fail' | 'needs_review'
export interface PerCaseResult {
  failure_id: string
  verdict: 'resolved' | 'partial' | 'still_broken'
  reasoning?: string
}
export interface RegressionRunRead {
  id: UUID
  skill_id_old: UUID
  skill_id_new: UUID
  test_set_strategy: TestSetStrategy
  test_case_count: number
  pass_count: number
  fail_count: number
  per_case_results: PerCaseResult[]
  regression_findings: string[]
  verdict: RegressionVerdict
  created_at: ISODateTime
  updated_at: ISODateTime
}

// --- SOPSource ---
export type SOPSourceType = 'pdf' | 'transcript' | 'table' | 'qc_spec' | 'case_library'
export interface SOPSourceRead {
  id: UUID
  factory_id: UUID
  type: SOPSourceType
  storage_ref: string
  metadata: Record<string, unknown>
  ingested_at: ISODateTime | null
  created_at: ISODateTime
  updated_at: ISODateTime
}

// --- SkillGenerationRequest (POST body) ---
export interface SkillGenerationRequest {
  agent_id: UUID
  sop_source_ids: UUID[]
  sop_source_set_id?: string
  strategy?: 'mining' | 'single'
}
