"""Provider-agnostic LLM layer for the Bach agent."""

from .provider import (
    AssistantTurn,
    LLMProvider,
    ProviderConfig,
    ToolCall,
    ToolSpec,
    build_provider,
)
from .openai_compat import OpenAICompatibleProvider

__all__ = [
    "LLMProvider",
    "ProviderConfig",
    "build_provider",
    "ToolSpec",
    "ToolCall",
    "AssistantTurn",
    "OpenAICompatibleProvider",
]
