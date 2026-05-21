import * as path from 'node:path'
import * as fs from 'node:fs'
import * as os from 'node:os'
import { test, expect } from './_fixtures'

test('SOP upload → /skill-generations → redirect to /skills/[agentId]', async ({ page, seed }) => {
  const tmpFile = path.join(os.tmpdir(), `e2e-sop-${Date.now()}.md`)
  fs.writeFileSync(
    tmpFile,
    '# Test SOP\n\n## Triggers\n- thermal drift detected\n\n## Procedure\n1. call query_environment'
  )

  await page.goto('/sop-upload')
  await page.getByRole('combobox').first().click()
  await page.getByRole('option', { name: /e2e-agent/ }).click()

  await page.getByTestId('sop-file-input').setInputFiles(tmpFile)
  await expect(page.getByText(/e2e-sop-/)).toBeVisible()

  await page.getByTestId('sop-submit').click()
  await page.waitForURL(`**/skills/${seed.agentId}`, { timeout: 30_000 })
  await expect(page.getByRole('heading', { name: 'Skill Timeline' })).toBeVisible()
})
