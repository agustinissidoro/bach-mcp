"""Single entrypoint for Bach — two roles, one shared core.

    serve  (default)   MCP server for MCP host apps such as Claude Desktop (or
                       any MCP-capable client). The HOST owns the model and the
                       agent loop; here we only expose the bach.roll tools and
                       wait to be driven. Serves over HTTP by default; pass
                       --stdio for the subprocess transport.

    agent              Self-hosted agent REPL. For driving any OpenAI-compatible
                       LLM endpoint yourself (Ollama, llama.cpp, vLLM, OpenAI,
                       ...). THIS process owns the model loop and calls the same
                       tools in-process. Configured via BACH_LLM_* env vars.

Usage:
    python main.py                       # serve over HTTP (default) at 127.0.0.1:8000/mcp
    python main.py serve
    python main.py serve --host 0.0.0.0 --port 9000   # bind for remote clients
    python main.py serve --stdio         # serve over stdio (host launches this process)
    python main.py agent                 # self-hosted REPL against an OpenAI-compatible provider

Both roles share the same core: BachMCPServer (TCP bridge to Max),
create_mcp_app (the single tool definition), and BACH_SKILL.md.
"""

from __future__ import annotations

import argparse
import os

from bach_mcp import (
    Agent,
    AgentConfig,
    BachMCPServer,
    McpToolBridge,
    ProviderConfig,
    build_provider,
    create_mcp_app,
)

_SKILL_PATH = os.path.join(os.path.dirname(__file__), "bach_mcp", "BACH_SKILL.md")


def _read_skill() -> str:
    with open(_SKILL_PATH, encoding="utf-8") as f:
        return f.read()


def run_serve(stdio: bool = False, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the MCP server for an external MCP host (e.g. Claude Desktop).

    By default serves over streamable HTTP (a standalone, long-lived listener at
    http://{host}:{port}/mcp). Pass stdio=True to instead speak MCP over the
    process's stdin/stdout, the transport an MCP host uses when it launches this
    process itself. host/port are ignored under stdio.

    The skill doc is exposed as an MCP resource so the host can read it at the
    start of each session via read_resource("bach://skill").
    """
    bach = BachMCPServer()
    bach.start()
    mcp = create_mcp_app(bach)

    @mcp.resource("bach://skill")
    def bach_skill() -> str:
        """Bach MCP skill — session protocol, llll syntax, slots, orchestral layout."""
        try:
            return _read_skill()
        except FileNotFoundError:
            return f"[BACH_SKILL.md not found at {_SKILL_PATH}]"

    if stdio:
        transport = "stdio"
    else:
        transport = "streamable-http"
        mcp.settings.host = host
        mcp.settings.port = port
        url = f"http://{host}:{port}{mcp.settings.streamable_http_path}"
        print(f"Bach MCP server (streamable HTTP) listening at {url}", flush=True)

    try:
        mcp.run(transport=transport)
    finally:
        bach.stop()


def run_agent() -> None:
    """Run the self-hosted agent REPL against an OpenAI-compatible provider.

    Provider/model/connection come from BACH_LLM_* env vars (see ProviderConfig).
    The skill doc is used directly as the system prompt — the same single source
    of truth the serve path exposes as a resource.
    """
    try:
        system_prompt = _read_skill()
    except FileNotFoundError:
        raise RuntimeError(
            f"BACH_SKILL.md not found at {_SKILL_PATH}. "
            "Make sure the file exists inside the bach_mcp/ folder."
        )

    provider_cfg = ProviderConfig.from_env()
    provider = build_provider(provider_cfg)

    bach = BachMCPServer()
    bach.start()
    mcp = create_mcp_app(bach)
    tools = McpToolBridge(mcp)
    agent = Agent(provider, tools, AgentConfig(system_prompt=system_prompt))

    print(f"\nBach — {provider_cfg.provider}:{provider_cfg.model} @ {provider_cfg.base_url}")
    print(f"{len(agent.tool_specs)} tools exposed.")

    try:
        try:
            greeting = agent.chat(
                "Introduce yourself in one sentence, starting with: I am ready"
            )
        except RuntimeError as exc:
            print(f"[Error] {exc}")
            return
        print(f"\nBach: {greeting}\n")
        bach.send_info(f"bach_ready {greeting}")

        print("Type a message and press Enter. Ctrl-C to quit.\n")
        while True:
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                bach.send_info("bach_offline")
                break
            if not user_input:
                continue
            try:
                reply = agent.chat(user_input)
                print(f"\nBach: {reply}\n")
            except RuntimeError as exc:
                print(f"[Error] {exc}")
    finally:
        tools.close()
        bach.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bach",
        description="Bridge bach.roll in Max to an LLM.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="serve",
        choices=["serve", "agent"],
        help=(
            "serve = MCP server for Claude Desktop / MCP hosts (default; HTTP "
            "unless --stdio). agent = self-hosted REPL against an "
            "OpenAI-compatible provider."
        ),
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="serve over stdio instead of HTTP (host launches this process).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP bind address for serve (default: 127.0.0.1; use 0.0.0.0 for remote clients).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port for serve (default: 8000).",
    )
    args = parser.parse_args()

    if args.mode == "agent":
        run_agent()
    else:
        run_serve(stdio=args.stdio, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
