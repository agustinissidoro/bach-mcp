"""Entrypoint for the Bach MCP server.

This module intentionally avoids side effects at import-time so Claude
can start it reliably as an MCP stdio process.
"""

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from bach_mcp import BachMCPServer


def create_mcp_app(bach: BachMCPServer) -> FastMCP:
    """Create and configure MCP tools."""
    mcp = FastMCP("max-bridge")

    @mcp.tool()
    def send_to_max(command: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """Send a command to Max/MSP."""
        success = bach.send_json(
            {
                "command": command,
                "payload": payload or {},
            }
        )
        return f"Sent '{command}' to Max" if success else "Failed to send"

    @mcp.tool()
    def ping_max() -> str:
        """Ping Max to check if it's alive."""
        success = bach.send_json(
            {
                "command": "ping",
                "payload": {},
            }
        )
        return "Pinged Max" if success else "Ping failed"

    return mcp


def main() -> None:
    """Start TCP bridge and run MCP over stdio."""
    bach = BachMCPServer()
    bach.start()
    mcp = create_mcp_app(bach)

    try:
        mcp.run(transport="stdio")
    finally:
        bach.stop()


if __name__ == "__main__":
    main()
