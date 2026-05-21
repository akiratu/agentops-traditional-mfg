import { test, expect, postJson, BACKEND } from './_fixtures'

test('accept finding: 4 sections + 3 cases + accept → status badge flips', async ({ page, seed }) => {
  const signal = await postJson(`${BACKEND}/anomaly-signals`, {
    agent_id: seed.agentId,
    source_type: 'metric_drift',
    related_trace_refs: ['e2e-trace-2'],
    status: 'resolved',
  })
  const finding = await postJson(`${BACKEND}/rca-findings`, {
    anomaly_signal_id: signal.id,
    root_cause_summary: 'Skill gap: missing query_environment call',
    evidence: {
      notebook:
        '## 🔍 已查到什麼\n- trace shows thermal drift on 3 machines\n\n' +
        '## 💡 目前推論\nAgent fails to map scenario to query_environment.\n\n' +
        '## ❓ 還需驗證\n(足夠了)\n\n' +
        '## 🚫 已排除\n- 不是 intermittent',
      failure_case_ids: ['fc-1', 'fc-2', 'fc-3'],
      plan_steps_completed: 3,
      total_iterations: 7,
      termination: 'submit_failure_cases',
    },
    suggested_fix_type: 'supplement_sop',
    suggested_fix_payload: {
      failure_cases: [
        { id: 'fc-1', query: '3 機台同時 X 軸漸進性偏移', expected_outcome: 'call query_environment', actual_outcome: 'called query_tool_life', context: null },
        { id: 'fc-2', query: 'shift change drift', expected_outcome: 'call query_recent_changes', actual_outcome: 'generic response', context: null },
        { id: 'fc-3', query: 'batch change', expected_outcome: 'call query_material_batch', actual_outcome: 'generic response', context: null },
      ],
    },
    confidence_score: 0.85,
    status: 'proposed',
  })

  await page.goto(`/findings/${finding.id}`)
  await expect(page.getByTestId('notebook-cell-found')).toBeVisible()
  await expect(page.getByTestId('notebook-cell-hypothesis')).toBeVisible()
  await expect(page.getByTestId('notebook-cell-todo')).toBeVisible()
  await expect(page.getByTestId('notebook-cell-excluded')).toBeVisible()
  await expect(page.getByText('fc-1')).toBeVisible()
  await expect(page.getByText('fc-2')).toBeVisible()
  await expect(page.getByText('fc-3')).toBeVisible()

  await page.getByTestId('accept-button').click()
  await expect(page.locator('[data-status="accepted"]')).toBeVisible({ timeout: 10_000 })
})
