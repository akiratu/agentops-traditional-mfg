import { chromium } from '@playwright/test'
import { mkdir, readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const BASE = process.env.BASE_URL ?? 'http://localhost:3001'
const OUT_DIR = resolve(__dirname, '../../docs/screenshots')

const ids = JSON.parse(await readFile('/tmp/demo-ids.json', 'utf-8'))

const SHOTS = [
  { name: '00_dashboard', path: '/dashboard', waitForText: 'AgentOps 平台總覽' },
  { name: '01_factories', path: '/factories', waitForText: 'ACME Metals' },
  { name: '02_factory_metal_detail', path: `/factories/${ids.metal_factory_id}`, waitForText: 'CNC RCA Agent' },
  { name: '03_agent_dashboard', path: `/agents/${ids.metal_agent_id}`, waitForText: 'CNC RCA Agent' },
  { name: '04_anomalies_feed', path: '/anomalies', waitForText: '異常列表' },
  { name: '05_finding_hero', path: `/findings/${ids.metal_finding_id}`, waitForText: '推理筆記' },
  { name: '06_skill_timeline', path: `/skills/${ids.metal_agent_id}`, waitForText: '技能版本演進' },
  { name: '07_regression_runs', path: '/regression-runs', waitForText: '回歸測試' },
  { name: '08_sop_upload', path: '/sop-upload', waitForText: '上傳 SOP' },
]

await mkdir(OUT_DIR, { recursive: true })
const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
for (const shot of SHOTS) {
  console.log(`▶ ${shot.name}  ${BASE}${shot.path}`)
  await page.goto(`${BASE}${shot.path}`, { waitUntil: 'networkidle', timeout: 30_000 })
  if (shot.waitForText) {
    try { await page.getByText(shot.waitForText).first().waitFor({ timeout: 10_000 }) }
    catch { console.log(`  ⚠ text "${shot.waitForText}" not found`) }
  }
  await page.waitForTimeout(1500)
  const out = resolve(OUT_DIR, `${shot.name}.png`)
  await page.screenshot({ path: out, fullPage: true })
  console.log(`  ✓ ${out}`)
}
await browser.close()
console.log(`\nDone. ${SHOTS.length} screenshots in ${OUT_DIR}`)
