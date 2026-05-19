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
        description="LLM provider for flows2agents: anthropic / openai / google / ollama / fake",
    )
    anthropic_api_key: str = Field(
        default="", description="Anthropic API key for Claude"
    )
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key (also accepts GOOGLE_API_KEY)",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model name. Try 'gemini-2.5-pro' for stronger tool-calling.",
    )
    trace_analyzer_model: str = Field(
        default="gemini-2.5-pro",
        description="Model name for Trace Analyzer (uses configured LLM provider's base_url)",
    )
    trace_analyzer_max_steps: int = Field(
        default=12,
        description="Hard cap on Trace Analyzer ReAct loop iterations to bound cost",
    )
    trace_analyzer_top_k_findings: int = Field(
        default=3,
        description="How many past RCAFindings to retrieve as context for the analyzer",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
