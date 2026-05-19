from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default="postgresql+psycopg://agentops:agentops_dev@localhost:5432/agentops",
        description="Postgres DSN for application metadata",
    )
    langfuse_host: str = Field(default="http://localhost:3000")
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    llm_provider_name: str = Field(
        default="anthropic",
        description="LLM provider for flows2agents: anthropic / openai / ollama / fake",
    )
    anthropic_api_key: str = Field(
        default="", description="Anthropic API key for Claude"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
