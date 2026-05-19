"""LLM provider abstraction layer.

Decouples the agent loop, summariser, and RAG retriever from any specific
SDK so that adding OpenAI / Anthropic / Ollama / Together later only
requires writing a new `Provider` subclass.

Neutral types
-------------
- `ChatMessage`     — one turn of conversation (system / user / assistant / tool_response)
- `ToolSpec`        — function declaration (provider-agnostic JSON-Schema-ish)
- `FunctionCall`    — model's request to invoke a tool
- `FunctionResponse`— the result we feed back
- `ChatResponse`    — model's reply (text + zero or more function_calls)

Provider interface
------------------
- `chat(messages, tools, ...) -> ChatResponse`     — main agent call
- `complete_text(prompt, ...) -> str`              — simple text completion (for summariser)
- `embed(text, task_type) -> list[float]`          — vector embedding

To add a new provider:
1. Subclass `LLMProvider`
2. Implement the 3 methods above (translate neutral types → vendor SDK)
3. Register in `make_provider()` factory at bottom of this file
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Neutral types
# ---------------------------------------------------------------------------

Role = Literal["system", "user", "assistant", "tool_response"]


@dataclass
class FunctionCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    # OpenAI/Ollama-style providers use string IDs to match call <-> response.
    # Gemini matches by name+position so this stays None there.
    id: str | None = None


@dataclass
class FunctionResponse:
    name: str
    response: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None  # matches FunctionCall.id when present


@dataclass
class ChatMessage:
    """One conversation turn.

    A message carries ONE of:
      - text (user / assistant / system)
      - function_calls (assistant requesting tool invocations)
      - function_responses (tool results sent back)
    Multiple function calls/responses can be batched in a single message.
    """
    role: Role
    text: str | None = None
    function_calls: list[FunctionCall] = field(default_factory=list)
    function_responses: list[FunctionResponse] = field(default_factory=list)


@dataclass
class ToolSpec:
    """Provider-agnostic tool / function declaration.

    `parameters` follows a JSON Schema-ish shape:
      {"type": "object",
       "properties": {"foo": {"type": "string", "description": "..."}},
       "required": ["foo"]}
    """
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    text: str = ""
    function_calls: list[FunctionCall] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Provider base
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Vendor-agnostic LLM client."""

    name: str = "base"  # subclasses override

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
    ) -> ChatResponse:
        """Main multi-turn call. May choose to call zero or more functions."""

    @abstractmethod
    def complete_text(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 400,
    ) -> str:
        """Simple text-in / text-out, for things like summarisation."""

    @abstractmethod
    def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """Return a single embedding vector for `text`."""


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    name = "gemini"

    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_SUMMARIZER_MODEL = "gemini-2.0-flash"
    DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"

    def __init__(self, api_key: str, default_model: str | None = None):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self.default_model = default_model or self.DEFAULT_MODEL

    # ---- conversion: neutral types → Gemini SDK types ----

    @staticmethod
    def _to_gemini_contents(messages: list[ChatMessage]):
        from google.genai import types
        out = []
        for m in messages:
            parts: list = []
            if m.text:
                parts.append(types.Part.from_text(text=m.text))
            for fc in m.function_calls:
                # Use Part.from_function_call if available, else build manually
                parts.append(types.Part(function_call=types.FunctionCall(
                    name=fc.name, args=fc.args,
                )))
            for fr in m.function_responses:
                parts.append(types.Part.from_function_response(
                    name=fr.name, response=fr.response,
                ))
            role = "model" if m.role == "assistant" else "user"
            out.append(types.Content(role=role, parts=parts))
        return out

    @staticmethod
    def _to_gemini_tools(tools: list[ToolSpec]):
        from google.genai import types

        def _convert_schema(spec: dict[str, Any]) -> types.Schema:
            t = (spec.get("type") or "OBJECT").upper()
            kwargs: dict[str, Any] = {"type": t}
            if "description" in spec:
                kwargs["description"] = spec["description"]
            if t == "OBJECT":
                props = spec.get("properties", {})
                kwargs["properties"] = {k: _convert_schema(v) for k, v in props.items()}
                if "required" in spec:
                    kwargs["required"] = list(spec["required"])
            elif t == "ARRAY":
                if "items" in spec:
                    kwargs["items"] = _convert_schema(spec["items"])
            return types.Schema(**kwargs)

        decls = []
        for t in tools:
            decls.append(types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=_convert_schema(t.parameters),
            ))
        return [types.Tool(function_declarations=decls)] if decls else None

    # ---- LLMProvider methods ----

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
    ) -> ChatResponse:
        from google.genai import types

        contents = self._to_gemini_contents(messages)
        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if max_output_tokens is not None:
            config_kwargs["max_output_tokens"] = max_output_tokens

        gemini_tools = self._to_gemini_tools(tools) if tools else None
        if gemini_tools:
            config_kwargs["tools"] = gemini_tools
            config_kwargs["tool_config"] = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="AUTO"),
            )

        config = types.GenerateContentConfig(**config_kwargs)

        response = self._client.models.generate_content(
            model=model or self.default_model,
            contents=contents,
            config=config,
        )

        out = ChatResponse()
        candidate = response.candidates[0] if response.candidates else None
        if candidate is None or candidate.content is None:
            return out
        for part in candidate.content.parts or []:
            if getattr(part, "text", None):
                txt = part.text.strip()
                if txt:
                    out.text = (out.text + "\n" + txt).strip() if out.text else txt
            fc = getattr(part, "function_call", None)
            if fc is not None:
                out.function_calls.append(FunctionCall(
                    name=fc.name,
                    args=dict(fc.args) if fc.args else {},
                ))
        return out

    def complete_text(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 400,
    ) -> str:
        from google.genai import types
        resp = self._client.models.generate_content(
            model=model or self.DEFAULT_SUMMARIZER_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        return (resp.text or "").strip()

    def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        from google.genai import types
        resp = self._client.models.embed_content(
            model=self.DEFAULT_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type=task_type),
        )
        return list(resp.embeddings[0].values)


# ---------------------------------------------------------------------------
# Ollama Cloud implementation
# ---------------------------------------------------------------------------

class OllamaProvider(LLMProvider):
    """Ollama Cloud via the official `ollama` Python SDK.

    Embedding is NOT done through Ollama — we delegate to an optional
    `embedding_provider` (typically Gemini) to keep the existing RAG index
    compatible (gemini-embedding-001 vectors are 3072-dim and incompatible
    with any other embedder).
    """

    name = "ollama"
    DEFAULT_HOST = "https://ollama.com"
    DEFAULT_MODEL = "gemma4:31b-cloud"

    def __init__(
        self,
        api_key: str,
        default_model: str | None = None,
        host: str | None = None,
        embedding_provider: LLMProvider | None = None,
    ):
        from ollama import Client
        self._client = Client(
            host=host or self.DEFAULT_HOST,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        self.default_model = default_model or self.DEFAULT_MODEL
        self._embedder = embedding_provider

    # ---- conversion: neutral types → Ollama (OpenAI-shaped) messages ----

    @staticmethod
    def _to_ollama_messages(
        messages: list[ChatMessage], system: str | None,
    ) -> list[dict[str, Any]]:
        import json as _json
        out: list[dict[str, Any]] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "user":
                if m.text:
                    out.append({"role": "user", "content": m.text})
                # standalone function_responses on a user-role message also
                # serialise as tool messages
                for fr in m.function_responses:
                    out.append({
                        "role": "tool",
                        "tool_call_id": fr.call_id or f"call_{fr.name}",
                        "name": fr.name,
                        "content": _json.dumps(fr.response, ensure_ascii=False),
                    })
            elif m.role == "assistant":
                msg: dict[str, Any] = {"role": "assistant", "content": m.text or ""}
                if m.function_calls:
                    msg["tool_calls"] = [{
                        "id": fc.id or f"call_{fc.name}_{i}",
                        "type": "function",
                        "function": {
                            "name": fc.name,
                            # Ollama SDK's Pydantic model expects a dict here,
                            # not the JSON-encoded string OpenAI uses.
                            "arguments": fc.args or {},
                        },
                    } for i, fc in enumerate(m.function_calls)]
                out.append(msg)
            elif m.role == "tool_response":
                for fr in m.function_responses:
                    out.append({
                        "role": "tool",
                        "tool_call_id": fr.call_id or f"call_{fr.name}",
                        "name": fr.name,
                        "content": _json.dumps(fr.response, ensure_ascii=False),
                    })
            elif m.role == "system":
                out.append({"role": "system", "content": m.text or ""})
        return out

    @staticmethod
    def _to_ollama_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        } for t in tools]

    # ---- LLMProvider methods ----

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
    ) -> ChatResponse:
        import json as _json
        import time as _time
        ollama_messages = self._to_ollama_messages(messages, system_instruction)
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": ollama_messages,
            "options": {"temperature": temperature},
        }
        if tools:
            kwargs["tools"] = self._to_ollama_tools(tools)
        if max_output_tokens is not None:
            kwargs["options"]["num_predict"] = max_output_tokens

        # Retry transient 5xx errors (Ollama Cloud occasionally hiccups).
        last_err: Exception | None = None
        for attempt, delay in enumerate([0, 2, 5]):
            if delay:
                _time.sleep(delay)
            try:
                resp = self._client.chat(**kwargs)
                break
            except Exception as e:
                last_err = e
                err_str = str(e)
                # Only retry on server errors; bail on auth/validation issues
                if not any(code in err_str for code in ("500", "502", "503", "504")):
                    raise
        else:
            raise last_err if last_err else RuntimeError("Ollama call failed")

        msg = resp.message  # ollama returns an object with .content, .tool_calls

        out = ChatResponse(text=(msg.content or "").strip())
        for tc in getattr(msg, "tool_calls", None) or []:
            fn = tc.function
            args = fn.arguments
            # ollama SDK returns args as either dict or JSON string
            if isinstance(args, str):
                try:
                    args = _json.loads(args)
                except Exception:
                    args = {}
            out.function_calls.append(FunctionCall(
                name=fn.name,
                args=dict(args) if args else {},
                id=getattr(tc, "id", None),
            ))
        return out

    def complete_text(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 400,
    ) -> str:
        resp = self._client.chat(
            model=model or self.default_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature, "num_predict": max_output_tokens},
        )
        return (resp.message.content or "").strip()

    def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        if self._embedder is None:
            raise RuntimeError(
                "OllamaProvider has no embedding backend. Provide a Gemini key "
                "(GEMINI_API_KEY) so RAG can keep using gemini-embedding-001."
            )
        return self._embedder.embed(text, task_type)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

# Model-name patterns that route to Ollama Cloud. Add more if you host other
# open models there (e.g. "qwen", "llama").
OLLAMA_MODEL_PREFIXES = ("gemma", "qwen", "llama", "mistral", "deepseek", "gpt-oss")


def _is_ollama_model(model: str) -> bool:
    """Heuristic: Ollama-hosted models typically include ':' (size suffix),
    e.g. 'gemma4:31b'. Gemini-hosted 'gemma-3-27b-it' uses dashes only."""
    if not model:
        return False
    if ":" in model:
        return True
    return False


def make_provider(model: str | None = None, api_key: str | None = None) -> LLMProvider:
    """Return the right provider for a given model name.

    Routing:
      - model contains ':' → Ollama Cloud (e.g. 'gemma4:31b')
      - everything else    → Gemini (incl. gemma-*-it via Gemini API)

    The `api_key` argument is treated as the *Gemini* key. Ollama Cloud reads
    its key from the OLLAMA_API_KEY env var only (so a Gemini key passed in
    won't accidentally be sent to ollama.com).

    Embedding always uses Gemini (the RAG index is gemini-embedding-001 vectors;
    switching would invalidate it).
    """
    gemini_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if _is_ollama_model(model or ""):
        ollama_key = os.environ.get("OLLAMA_API_KEY")
        if not ollama_key:
            raise RuntimeError(
                "Missing OLLAMA_API_KEY — set it as an environment variable "
                "or via the sidebar input."
            )
        embedder = GeminiProvider(api_key=gemini_key) if gemini_key else None
        return OllamaProvider(
            api_key=ollama_key,
            default_model=model,
            embedding_provider=embedder,
        )

    # Default: Gemini
    if not gemini_key:
        raise RuntimeError("Missing API key (set GEMINI_API_KEY)")
    return GeminiProvider(api_key=gemini_key, default_model=model)
