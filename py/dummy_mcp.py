"""Minimal MCP server for connection testing."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("max-bridge")


@mcp.tool()
def alive() -> str:
    """Return a constant response."""
    return "ok"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Return a + b."""
    return a + b


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
