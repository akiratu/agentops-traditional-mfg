import type {
  AgentCurrentSkillUpdate,
  AgentRead,
  AgentRuntimeStatusUpdate,
  AnomalySignalRead,
  FactoryRead,
  RCAFindingRead,
  RCAFindingStatusUpdate,
  RegressionRunRead,
  SOPSourceRead,
  SOPSourceType,
  SkillGenerationRequest,
  SkillRead,
  SkillStatusUpdate,
  UUID,
} from './types'

const BASE = '/api'

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public url: string
  ) {
    super(`${status} ${detail} (${url})`)
    this.name = 'ApiError'
  }
}

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      // FastAPI 422 validation errors: array of { loc, msg, type }
      return body.detail
        .map((e: unknown) => {
          if (typeof e === 'object' && e !== null && 'msg' in e) {
            return String((e as { msg: unknown }).msg)
          }
          return JSON.stringify(e)
        })
        .join('; ')
    }
    return res.statusText
  } catch {
    return res.statusText
  }
}

async function http<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const url = `${BASE}${path}`
  const { json, headers, ...rest } = init ?? {}
  const res = await fetch(url, {
    ...rest,
    headers: {
      Accept: 'application/json',
      ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })
  if (!res.ok) {
    const detail = await extractErrorDetail(res)
    throw new ApiError(res.status, detail, url)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const usp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') usp.set(k, String(v))
  }
  const s = usp.toString()
  return s ? `?${s}` : ''
}

export const api = {
  // factories
  listFactories: () => http<FactoryRead[]>('/factories'),
  getFactory: (id: UUID) => http<FactoryRead>(`/factories/${id}`),

  // agents
  listAgents: (factoryId?: UUID) =>
    http<AgentRead[]>(`/agents${qs({ factory_id: factoryId })}`),
  getAgent: (id: UUID) => http<AgentRead>(`/agents/${id}`),
  patchAgentRuntimeStatus: (id: UUID, body: AgentRuntimeStatusUpdate) =>
    http<AgentRead>(`/agents/${id}/runtime-status`, { method: 'PATCH', json: body }),
  patchAgentCurrentSkill: (id: UUID, body: AgentCurrentSkillUpdate) =>
    http<AgentRead>(`/agents/${id}/current-skill`, { method: 'PATCH', json: body }),

  // skills
  listSkills: (agentId?: UUID) =>
    http<SkillRead[]>(`/skills${qs({ agent_id: agentId })}`),
  getSkill: (id: UUID) => http<SkillRead>(`/skills/${id}`),
  patchSkillStatus: (id: UUID, body: SkillStatusUpdate) =>
    http<SkillRead>(`/skills/${id}/status`, { method: 'PATCH', json: body }),

  // anomalies
  /**
   * GET /anomaly-signals — backend currently only filters by agent_id.
   * For source_type / status filtering, fetch and filter client-side
   * (see app/anomalies/page.tsx).
   */
  listAnomalySignals: (filter: { agent_id?: UUID } = {}) =>
    http<AnomalySignalRead[]>(`/anomaly-signals${qs(filter)}`),
  getAnomalySignal: (id: UUID) =>
    http<AnomalySignalRead>(`/anomaly-signals/${id}`),

  // findings
  getFinding: (id: UUID) => http<RCAFindingRead>(`/rca-findings/${id}`),
  listFindings: (anomalySignalId?: UUID) =>
    http<RCAFindingRead[]>(
      `/rca-findings${qs({ anomaly_signal_id: anomalySignalId })}`
    ),
  patchFindingStatus: (id: UUID, body: RCAFindingStatusUpdate) =>
    http<RCAFindingRead>(`/rca-findings/${id}/status`, { method: 'PATCH', json: body }),

  // regression
  listRegressionRuns: () => http<RegressionRunRead[]>('/regression-runs'),
  getRegressionRun: (id: UUID) => http<RegressionRunRead>(`/regression-runs/${id}`),

  // sop upload (multipart)
  uploadSOP: async (factoryId: UUID, file: File, type: SOPSourceType): Promise<SOPSourceRead> => {
    const form = new FormData()
    form.append('file', file)
    form.append('type', type)
    const res = await fetch(`${BASE}/factories/${factoryId}/sop-uploads`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const detail = await extractErrorDetail(res)
      throw new ApiError(res.status, detail, res.url)
    }
    return (await res.json()) as SOPSourceRead
  },

  // skill generation — long-running (2-3 min Gemini mining). Bypass Next.js
  // dev proxy because it times out the socket at ~30s; go straight to the
  // backend (CORS is configured for localhost:3001). Other endpoints can
  // keep using the proxy because they're sub-second.
  generateSkill: async (body: SkillGenerationRequest): Promise<SkillRead> => {
    const directBackend =
      process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'
    const res = await fetch(`${directBackend}/skill-generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const detail = await extractErrorDetail(res)
      throw new ApiError(res.status, detail, res.url)
    }
    return (await res.json()) as SkillRead
  },
}

export { ApiError }
