from fastapi import FastAPI

from agentops_core.api.routes import router

app = FastAPI(
    title="AgentOps for Traditional Manufacturing",
    version="0.1.0",
)
app.include_router(router)
