"""Public exports for the Bach MCP module."""

from .mcp_app import create_mcp_app
from .server import BachMCPServer, MCPConfig
from .ollama_bridge import OllamaBridge, BridgeConfig

__all__ = ["BachMCPServer", "MCPConfig", "create_mcp_app", "OllamaBridge", "BridgeConfig"]

