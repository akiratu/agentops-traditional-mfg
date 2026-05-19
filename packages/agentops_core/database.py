from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from agentops_core.config import get_settings


def _make_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )


engine = _make_engine()


def init_db() -> None:
    """Create all tables (for tests / first boot — production uses Alembic)."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


from pathlib import Path

from agentops_core.services.storage import LocalStorage


def _make_storage() -> LocalStorage:
    return LocalStorage(root=Path("data"))


storage = _make_storage()


def get_storage() -> LocalStorage:
    return storage


from flows2agents.llm.base import LLMProvider
from flows2agents.llm.fake import FakeLLMProvider  # noqa: F401 — imported for type hints

from agentops_core.services.llm_provider import build_provider


def get_provider() -> LLMProvider:
    """FastAPI dependency: return the configured LLM provider.

    Test conftest overrides this to inject FakeLLMProvider directly.
    """
    return build_provider(get_settings())
