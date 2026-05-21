import { test, expect, postJson, BACKEND } from './_fixtures'

test('browse: factories → agent → anomaly feed shows seeded signal', async ({ page, seed }) => {
  await postJson(`${BACKEND}/anomaly-signals`, {
    agent_id: seed.agentId,
    source_type: 'human_flag',
    related_trace_refs: ['e2e-trace-1'],
  })

  await page.goto('/factories')
  await expect(page.getByRole('heading', { name: 'Factories' })).toBeVisible()
  await page.getByText(/e2e-factory-/).first().click()

  await expect(page.getByText('e2e-agent')).toBeVisible()
  await page.getByRole('link', { name: 'e2e-agent' }).click()

  await page.getByRole('link', { name: /View all anomalies/ }).click()
  await expect(page.getByTestId('anomaly-list').locator('> *')).not.toHaveCount(0)
})
