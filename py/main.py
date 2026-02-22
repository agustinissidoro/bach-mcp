"""Entrypoint for the Bach MCP server (Claude/MCP path)."""

from __future__ import annotations

import os
from bach_mcp import BachMCPServer, create_mcp_app


# Load the skill doc and expose it as an MCP resource so Claude can read it
# at the start of each session via read_resource("bach://skill").
_SKILL_PATH = os.path.join(os.path.dirname(__file__), "bach_mcp", "BACH_SKILL.md")


def main() -> None:
    """Start TCP bridge, register skill resource, and run MCP over stdio."""
    bach = BachMCPServer()
    bach.start()
    mcp = create_mcp_app(bach)

    @mcp.resource("bach://skill")
    def bach_skill() -> str:
        """Bach MCP skill — session protocol, llll syntax, slots, orchestral layout."""
        try:
            with open(_SKILL_PATH) as f:
                return f.read()
        except FileNotFoundError:
            return f"[BACH_SKILL.md not found at {_SKILL_PATH}]"

    try:
        mcp.run(transport="stdio")
    finally:
        bach.stop()


if __name__ == "__main__":
    main()
