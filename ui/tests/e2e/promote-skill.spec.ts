import { test, expect, postJson, BACKEND } from './_fixtures'

test('promote skill: DRAFT v2 → ACTIVE, prior ACTIVE → ARCHIVED', async ({ page, seed }) => {
  await postJson(`${BACKEND}/skills`, {
    agent_id: seed.agentId,
    version: 2,
    status: 'draft',
    prompt: 'You are an e2e agent.\nFollow SOP v2.\nAlso call query_environment.',
    tool_specs: [],
    golden_test_cases: [],
    sop_source_set_id: `set-e2e-v2-${Date.now()}`,
  })

  await page.goto(`/skills/${seed.agentId}`)
  await expect(page.getByLabel(/Select v1 for diff/)).toBeVisible()
  await expect(page.getByLabel(/Select v2 for diff/)).toBeVisible()

  await page.getByTestId('promote-2').click()
  await expect(
    page.locator('span[data-status="active"]').filter({ hasText: /^active$/ })
  ).toHaveCount(1, { timeout: 15_000 })
  await expect(page.locator('span[data-status="archived"]')).toBeVisible({ timeout: 15_000 })
})
