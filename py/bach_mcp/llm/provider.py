"""
provider.py
-----------
Provider-agnostic LLM interface for the Bach agent.

The agent talks to every LLM backend — cloud or local — through a single
`LLMProvider` interface. Each concrete provider translates the neutral
request (OpenAI-style messages + a list of `ToolSpec`) into its own wire
format, calls the model, and returns a normalized `AssistantTurn`.

Message format
--------------
Messages are plain OpenAI-style chat dicts:
    {"role": "system"|"user"|"assistant"|"tool", "content": str, ...}
Assistant turns that call tools carry an OpenAI-style "tool_calls" list, and
tool results are returned as {"role": "tool", "tool_call_id": ..., "content": ...}.
This is the de-facto lingua franca; the OpenAI-compatible provider passes it
through unchanged, and future providers (e.g. Anthropic) translate from it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ── Neutral request/response types ───────────────────────────────────────── #

@dataclass
class ToolSpec:
    """A single tool the model may call, in provider-neutral form.

    `parameters` is a JSON Schema object describing the tool arguments —
    exactly the `inputSchema` produced by the MCP server.
    """
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ToolCall:
    """A tool invocation requested by the model."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class AssistantTurn:
    """Normalized model reply: free text plus any tool calls."""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)


# ── Provider interface ───────────────────────────────────────────────────── #

@runtime_checkable
class LLMProvider(Protocol):
    """Anything that can run one chat completion round with tool support."""

    def chat(self, messages: List[Dict[str, Any]], tools: List[ToolSpec]) -> AssistantTurn:
        """Send one request and return the model's (possibly tool-calling) reply."""
        ...


# ── Configuration + factory ──────────────────────────────────────────────── #

@dataclass
class ProviderConfig:
    """Backend selection and connection settings.

    `provider` chooses the adapter. "openai" (and its aliases ollama / llamacpp
    / vllm) all map to the single OpenAI-compatible provider, since Ollama and
    llama.cpp both expose an OpenAI-compatible /v1/chat/completions endpoint —
    there is no separate Ollama provider. "anthropic" is reserved for later.

    `base_url` must be the OpenAI-compatible base INCLUDING the version segment,
    e.g.
        Ollama     -> http://localhost:11434/v1
        llama.cpp  -> http://localhost:8080/v1
        vLLM       -> http://localhost:8000/v1
        OpenAI     -> https://api.openai.com/v1
    """
    provider: str = "openai"
    base_url: str = "http://localhost:11434/v1"
    model: str = "qwen3:8b"
    api_key: Optional[str] = None
    temperature: float = 0.35
    max_tokens: int = 2048
    request_timeout_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        """Build config from BACH_LLM_* environment variables, falling back to defaults."""
        defaults = cls()
        return cls(
            provider=os.getenv("BACH_LLM_PROVIDER", defaults.provider),
            base_url=os.getenv("BACH_LLM_BASE_URL", defaults.base_url),
            model=os.getenv("BACH_LLM_MODEL", defaults.model),
            api_key=os.getenv("BACH_LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
            temperature=float(os.getenv("BACH_LLM_TEMPERATURE", defaults.temperature)),
            max_tokens=int(os.getenv("BACH_LLM_MAX_TOKENS", defaults.max_tokens)),
            request_timeout_seconds=float(
                os.getenv("BACH_LLM_TIMEOUT", defaults.request_timeout_seconds)
            ),
        )


# Aliases that all resolve to the OpenAI-compatible provider.
_OPENAI_COMPATIBLE_ALIASES = {
    "openai", "openai-compatible", "openai_compat", "openaicompat",
    "ollama", "llamacpp", "llama.cpp", "llama-cpp", "vllm", "lmstudio", "groq", "together",
}


def build_provider(config: ProviderConfig) -> LLMProvider:
    """Construct the concrete provider selected by `config.provider`."""
    kind = config.provider.strip().lower()

    if kind in _OPENAI_COMPATIBLE_ALIASES:
        # Local import avoids a circular import (openai_compat imports these types).
        from .openai_compat import OpenAICompatibleProvider
        return OpenAICompatibleProvider(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            request_timeout_seconds=config.request_timeout_seconds,
        )

    if kind == "anthropic":
        raise NotImplementedError(
            "AnthropicProvider is not implemented yet. "
            "Use an OpenAI-compatible provider (provider='openai', e.g. against "
            "Ollama or llama.cpp) for now."
        )

    raise ValueError(
        f"Unknown LLM provider '{config.provider}'. "
        f"Use 'openai' (covers Ollama/llama.cpp/vLLM/OpenAI) or 'anthropic' (coming soon)."
    )
