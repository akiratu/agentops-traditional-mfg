from fastapi import FastAPI

from agentops_core.api import agent, anomaly_signal, factory, skill, sop_source
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
