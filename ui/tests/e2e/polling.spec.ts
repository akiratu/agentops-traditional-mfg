import { test, expect, postJson, BACKEND } from './_fixtures'

test('polling: new signal appears within 7s without manual refresh', async ({ page, seed }) => {
  await page.goto('/anomalies')
  await expect(page.getByRole('heading', { name: 'Anomaly Feed' })).toBeVisible()
  const initialCount = await page.getByTestId('anomaly-list').locator('> *').count()

  await postJson(`${BACKEND}/anomaly-signals`, {
    agent_id: seed.agentId,
    source_type: 'human_flag',
    related_trace_refs: ['poll-trace'],
  })

  await expect
    .poll(async () => page.getByTestId('anomaly-list').locator('> *').count(), {
      timeout: 7_000,
      intervals: [1000, 1000, 1000, 1000, 1000, 1000, 1000],
    })
    .toBeGreaterThan(initialCount)
})
