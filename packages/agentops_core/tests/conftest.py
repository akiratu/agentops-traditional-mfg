import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from agentops_core.database import get_session
from agentops_core.main import app


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import all model modules to register their tables before create_all.
    from agentops_core import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session, tmp_path):
    from unittest.mock import MagicMock

    from flows2agents.llm.fake import FakeLLMProvider

    from agentops_core.database import (
        get_langfuse_client,
        get_provider,
        get_session,
        get_storage,
    )
    from agentops_core.services.langfuse_client import LangfuseTraceClient
    from agentops_core.services.storage import LocalStorage

    def _override_session():
        yield session

    test_storage = LocalStorage(root=tmp_path)

    def _override_storage():
        return test_storage

    fake_provider = FakeLLMProvider()

    def _override_provider():
        return fake_provider

    fake_lf = MagicMock(spec=LangfuseTraceClient)
    fake_lf.is_available.return_value = False
    fake_lf.search_traces.return_value = []
    fake_lf.fetch_trace.return_value = {
        "id": "trace_test",
        "name": "test",
        "input": None,
        "output": None,
        "observations": [],
        "metadata": {},
    }

    def _override_langfuse():
        return fake_lf

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_storage] = _override_storage
    app.dependency_overrides[get_provider] = _override_provider
    app.dependency_overrides[get_langfuse_client] = _override_langfuse
    yield TestClient(app)
    app.dependency_overrides.clear()
