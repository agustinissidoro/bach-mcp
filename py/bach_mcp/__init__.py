"""Public exports for the Bach MCP module."""

from .mcp_app import create_mcp_app
from .server import BachMCPServer, MCPConfig
from .mcp_tools import McpToolBridge
from .agent import Agent, AgentConfig
from .llm import (
    AssistantTurn,
    LLMProvider,
    OpenAICompatibleProvider,
    ProviderConfig,
    ToolCall,
    ToolSpec,
    build_provider,
)

__all__ = [
    "BachMCPServer",
    "MCPConfig",
    "create_mcp_app",
    "McpToolBridge",
    "Agent",
    "AgentConfig",
    "LLMProvider",
    "ProviderConfig",
    "build_provider",
    "OpenAICompatibleProvider",
    "ToolSpec",
    "ToolCall",
    "AssistantTurn",
]
