from fastapi import FastAPI

from agentops_core.api import agent, anomaly_signal, factory, rca_finding, regression_run, skill, sop_source
from agentops_core.api.routes import router as root_router

app = FastAPI(
    title="AgentOps for Traditional Manufacturing",
    version="0.1.0",
)
app.include_router(root_router)
app.include_router(factory.router)
app.include_router(agent.router)
app.include_router(sop_source.router)
app.include_router(skill.router)
app.include_router(anomaly_signal.router)
app.include_router(rca_finding.router)
app.include_router(regression_run.router)
