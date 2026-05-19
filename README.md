# AgentOps for Traditional Manufacturing

> Vertical AgentOps platform for the traditional manufacturing industry.
> Turns master craftsman knowledge into AI agent skills, deploys to the factory,
> automatically observes, diagnoses, and self-evolves.

## Status

**v0.1 — Foundation & Data Model (W1-2 of MVP)**

This phase establishes the platform's skeleton:

- FastAPI service with all 7 core entities (Factory / Agent / Skill / SOPSource / AnomalySignal / RCAFinding / RegressionRun)
- PostgreSQL for entity metadata, Langfuse (self-hosted) for traces
- flows2agents integrated as git submodule
- rca-agent-demo vendored into `packages/showcase_agents/factory_rca/`

## Architecture

See full design at: `docs/superpowers/specs/2026-05-19-agentops-traditional-mfg-design.md`

## Quickstart

```bash
# 1. Boot infrastructure
docker compose up -d

# 2. Install Python deps
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -e packages/flows2agents

# 3. Apply migrations
alembic upgrade head

# 4. Run the API
uvicorn agentops_core.main:app --reload --port 8000

# 5. Run tests
pytest
```

## URLs after `docker compose up`

| Service | URL |
|---|---|
| AgentOps API | http://localhost:8000 (after uvicorn) |
| API docs (Swagger) | http://localhost:8000/docs |
| Langfuse UI | http://localhost:3000 (login: dev@agentops.local / dev_password) |
| Postgres | localhost:5432 (agentops / agentops_dev) |

## Project structure

```
agentops-traditional-mfg/
├── docker-compose.yml
├── pyproject.toml
├── alembic/
├── packages/
│   ├── agentops_core/        # Platform service (this plan's main output)
│   ├── flows2agents/         # Submodule: skill generation engine
│   └── showcase_agents/
│       └── factory_rca/      # Vendored rca-agent-demo for dogfood
└── docs/
```

## Next phases

| Plan | Phase | Status |
|---|---|---|
| Plan 1 (this) | W1-2 Foundation | This plan |
| Plan 2 | W3-4 flows2agents service wrapper | TBD |
| Plan 3 | W5-6 Trace Analyzer + Langfuse | TBD |
| Plan 4 | W7-8 Anomaly Detector | TBD |
| Plan 5 | W9-11 Developer UI (Next.js) | TBD |
| Plan 6 | W12-13 Factory UI + Dogfood | TBD |
| Plan 7 | W14 Deployment & Release | TBD |

## Known tech debt (to address in Plan 2 or earlier)

1. **`updated_at` not auto-refreshed on row update.** `TimestampedModel.updated_at` uses `default_factory=_utcnow` which runs only at creation time. Needs a SQLAlchemy `onupdate` hook or `before_flush` event listener. Will matter when Plan 2 adds PATCH endpoints to mutate rows.

2. **Missing PATCH endpoints for Agent.runtime_status and Skill.status.** Workflow operations like "promote skill v2 to active" or "transition agent to running" have no API today. RCAFinding has a status PATCH endpoint as the only example. Will be needed in Plan 2.

3. **`docker-compose.yml` has obsolete `version:` key.** Docker Compose v2 warns but still works. Remove the line when convenient.

4. **`AnomalySourceType` adds `COST_SPIKE` beyond spec.** Reasonable extension (it's in the North Star scenario) but worth flagging.
