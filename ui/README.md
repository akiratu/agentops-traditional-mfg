# AgentOps UI v0.5 (Developer Mode)

Next.js 15 admin UI for the AgentOps Build → Diagnose → Evolve loop.

## Quick start

```bash
# Prereqs: Node 20+, pnpm 9+, backend running on :8000
cp .env.local.example .env.local
pnpm install
pnpm dev
# http://localhost:3001
```

## Architecture

- **App Router pages**: `app/factories/`, `app/agents/`, `app/anomalies/`, `app/findings/`, `app/skills/`, `app/regression-runs/`, `app/sop-upload/`
- **State**: TanStack Query v5; per-page `refetchInterval`
- **Styling**: shadcn/ui (zinc preset) + Tailwind v4 + compact density (14px base, 16px card padding, 36px table rows)
- **API**: `lib/api.ts` — every backend endpoint typed; `next.config.mjs` rewrites `/api/*` to `${NEXT_PUBLIC_BACKEND_URL}`

## Pages

| Route | Purpose | Polling |
|---|---|---|
| `/factories` | Factory list | 30s |
| `/factories/[id]` | Factory detail + agents | off |
| `/agents/[id]` | Agent dashboard + runtime PATCH | 10s |
| `/anomalies` | Anomaly feed + filters (source/status filter client-side) | **5s** |
| `/findings/[id]` | RCA hero (notebook + cases + accept) | **5s while ACCEPTED, ≤5 min** |
| `/skills/[agentId]` | Skill timeline + diff + promote | 10s |
| `/regression-runs` | Regression history | off |
| `/sop-upload` | SOP drag-drop → generate skill | off |

## Tests

```bash
pnpm test:e2e   # 5 critical happy paths
```

E2E tests require a backend on `:8000` with `LLM_PROVIDER_NAME=fake`. Component tests (CT) were deferred to v0.6 — Playwright CT 1.49 + React 19 + Tailwind v4 beta combo currently hangs the Vite production build. Badge / NotebookViewer / FailureCaseCard / SkillDiff behavior is verified through the E2E happy paths instead.

## Backend limitations honored

- `GET /anomaly-signals` only filters by `agent_id` server-side; `source_type` and `status` filters are applied client-side via TanStack Query `select`.
- `GET /anomaly-signals/{id}` doesn't exist — `/findings/[id]` finds parent signal via list-and-filter.

## Spec
`docs/superpowers/specs/2026-05-21-agentops-ui-v0.5-design.md`
