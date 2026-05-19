"""LLM provider factory: picks a flows2agents-compatible LLMProvider from settings."""

from __future__ import annotations

import logging

from flows2agents.llm.base import LLMProvider
from flows2agents.llm.fake import FakeLLMProvider

from agentops_core.config import Settings

log = logging.getLogger(__name__)


def build_provider(settings: Settings) -> LLMProvider:
    """Return an LLMProvider matching settings.llm_provider_name.

    Falls back to FakeLLMProvider when:
    - Requested provider is unknown
    - Required credentials are missing
    - Provider SDK is not installed

    The fallback is intentional — it lets dev and CI run end-to-end without
    surprise API calls. Override LLM_PROVIDER_NAME=anthropic and set
    ANTHROPIC_API_KEY in production / staging.
    """
    name = settings.llm_provider_name.lower()

    if name == "anthropic" and settings.anthropic_api_key:
        try:
            from flows2agents.llm.anthropic import AnthropicProvider

            return AnthropicProvider()
        except ImportError:
            log.warning("anthropic SDK not installed; falling back to fake provider")
            return FakeLLMProvider()

    if name == "openai":
        try:
            from flows2agents.llm.openai import OpenAIProvider

            return OpenAIProvider()
        except ImportError:
            log.warning("openai SDK not installed; falling back to fake provider")
            return FakeLLMProvider()

    if name == "google" and settings.gemini_api_key:
        # Gemini provider reads GEMINI_API_KEY / GOOGLE_API_KEY from os.environ.
        # Mirror settings.gemini_api_key into env so the provider can find it.
        import os

        os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
        try:
            from flows2agents.llm.google import GoogleProvider

            return GoogleProvider(model=settings.gemini_model)
        except ImportError:
            log.warning("google provider unavailable; falling back to fake provider")
            return FakeLLMProvider()

    if name == "ollama":
        try:
            from flows2agents.llm.ollama import OllamaProvider

            return OllamaProvider()
        except ImportError:
            log.warning("ollama provider unavailable; falling back to fake provider")
            return FakeLLMProvider()

    if name == "fake":
        return FakeLLMProvider()

    # Default catch-all: requested provider unknown OR credentials missing.
    log.warning(
        "LLM provider %r not buildable (unknown or missing key); using fake",
        settings.llm_provider_name,
    )
    return FakeLLMProvider()
