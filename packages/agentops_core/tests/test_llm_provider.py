from agentops_core.config import Settings
from agentops_core.services.llm_provider import build_provider


def test_build_fake_provider_when_provider_name_is_fake():
    settings = Settings(llm_provider_name="fake", anthropic_api_key="")
    provider = build_provider(settings)
    assert provider.name == "fake"
    assert provider.is_available() is True


def test_build_fake_when_no_key_and_default_is_anthropic():
    settings = Settings(llm_provider_name="anthropic", anthropic_api_key="")
    provider = build_provider(settings)
    # Fallback to fake when key missing (avoids surprise API calls in dev/CI)
    assert provider.name == "fake"


def test_build_anthropic_provider_when_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
    settings = Settings(llm_provider_name="anthropic", anthropic_api_key="sk-test-123")
    provider = build_provider(settings)
    assert provider.name == "anthropic"
    # is_available may be True without making a network call


def test_unknown_provider_falls_back_to_fake():
    settings = Settings(llm_provider_name="not-a-real-provider")
    provider = build_provider(settings)
    assert provider.name == "fake"
