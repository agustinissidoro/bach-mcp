"""Entrypoint for the Bach MCP server."""

from bach_mcp import BachMCPServer, create_mcp_app


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
