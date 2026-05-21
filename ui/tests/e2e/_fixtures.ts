import { test as base } from '@playwright/test'

const BACKEND = process.env.E2E_BACKEND_URL || 'http://localhost:8000'

export type SeededIds = {
  factoryId: string
  agentId: string
  skillId: string
}

async function seedFactoryAgentSkill(): Promise<SeededIds> {
  const factory = await postJson(`${BACKEND}/factories`, {
    name: `e2e-factory-${Date.now()}`,
    deployment_type: 'on_prem',
  })
  const agent = await postJson(`${BACKEND}/agents`, {
    factory_id: factory.id,
    name: 'e2e-agent',
    purpose: 'e2e test agent',
    runtime_status: 'running',
  })
  const skill = await postJson(`${BACKEND}/skills`, {
    agent_id: agent.id,
    version: 1,
    status: 'active',
    prompt: 'You are an e2e agent.\nFollow SOP.',
    tool_specs: [],
    golden_test_cases: [],
    sop_source_set_id: `set-e2e-${Date.now()}`,
  })
  await postJson(
    `${BACKEND}/agents/${agent.id}/current-skill`,
    { current_skill_id: skill.id },
    'PATCH'
  )
  return { factoryId: factory.id, agentId: agent.id, skillId: skill.id }
}

async function postJson(
  url: string,
  body: unknown,
  method: 'POST' | 'PATCH' = 'POST'
): Promise<{ id: string; [k: string]: unknown }> {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${method} ${url} → ${res.status} ${await res.text()}`)
  return res.json() as Promise<{ id: string; [k: string]: unknown }>
}

export const test = base.extend<{ seed: SeededIds }>({
  seed: async ({}, use) => {
    const ids = await seedFactoryAgentSkill()
    await use(ids)
  },
})

export { BACKEND, postJson }
export { expect } from '@playwright/test'
