from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentops_core.api import (
    agent,
    anomaly_signal,
    factory,
    human_flag,
    portfolio_generation,
    rca_finding,
    regression_run,
    self_evolve,
    skill,
    skill_generation,
    sop_source,
    sop_upload,
    trace_analysis,
)
from agentops_core.api.routes import router as root_router
from agentops_core.services.anomaly_detector.orchestrator import (
    run_anomaly_check_all_agents,
)
from agentops_core.services.scheduler import (
    build_scheduler,
    start_scheduler,
    stop_scheduler,
)

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _scheduler
    _scheduler = build_scheduler(
        anomaly_check_runner=run_anomaly_check_all_agents,
        interval_seconds=3600,
    )
    start_scheduler(_scheduler)
    try:
        yield
    finally:
        stop_scheduler(_scheduler)


app = FastAPI(
    title="AgentOps for Traditional Manufacturing",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(root_router)
app.include_router(factory.router)
app.include_router(agent.router)
app.include_router(sop_source.router)
app.include_router(skill.router)
app.include_router(anomaly_signal.router)
app.include_router(rca_finding.router)
app.include_router(regression_run.router)
app.include_router(sop_upload.router)
app.include_router(skill_generation.router)
app.include_router(portfolio_generation.router)
app.include_router(self_evolve.router)
app.include_router(trace_analysis.router)
app.include_router(human_flag.router)
