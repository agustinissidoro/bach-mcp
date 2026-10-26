"""
claude.py
---------
The door for Claude (Claude Desktop, Claude Code) and any other MCP host.
Claude brings its own model; Bach gives it the tools, what to read, and Max.

    mcp_app(config, bridge)   the 13 tools (tools/registry.py) plus what Claude reads:
                              the skill as the server's instructions, /score and /algo
                              as two prompts, the instrument docs as resources
    serve(config, stdio)      serves that app: over stdio when Claude Desktop launches
                              Bach itself, over HTTP at [server] otherwise
    register_desktop()        adds Bach to Claude Desktop's configuration
    claude_code_commands()    the lines that add Bach to Claude Code

The local chat (`run`) serves the same app at /mcp, so Claude Code can also
join the Bach that run.command started.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from .config import REPO_ROOT, Config
from .prompt.docs import DocLibrary
from .prompt.modes import MODE_TOOLS
from .utilities.status import start_bridge
from .tools.registry import create_tools

SERVER_NAME = "bach"
MAIN_PY = os.path.join(REPO_ROOT, "py", "main.py")
CLAUDE_DESKTOP_CONFIG = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")

_MODE_PROMPTS = {
    "score": "Work in /score mode: write the notes yourself as JSON, and get every pitch from the pitch tools. "
             "Use only these tools: {tools}.",
    "algo": "Work in /algo mode: write the algorithm that generates the music, as a JavaScript file with its "
            "parameters exposed. Use only {tools}; do not write the notes with write_score.",
}


def mcp_app(config: Config, bridge: Any) -> FastMCP:
    """The tools, with the skill, the mode prompts and the instrument docs for Claude."""
    mcp = create_tools(bridge, config.algo.node, log_calls=config.server.tool_log,
                       instructions=config.system_prompt())

    @mcp.resource("bach://skill", name="skill", description="How to compose with Bach's tools.",
                  mime_type="text/markdown")
    def skill() -> str:
        return config.system_prompt()

    for mode, text in _MODE_PROMPTS.items():
        mcp.prompt(name=mode, description=f"Compose in /{mode} mode.")(_mode_prompt(text.format(tools=", ".join(MODE_TOOLS[mode]))))

    for doc in DocLibrary().docs.values():
        title = doc.text.splitlines()[0].lstrip("# ").strip()
        mcp.resource(f"bach://docs/{doc.key}", name=doc.key, mime_type="text/markdown",
                     description=f"{title}: ranges, techniques and their JSON spellings, in midicents.")(_reader(doc.text))
    return mcp


def _mode_prompt(instruction: str):
    def prompt(request: str = "") -> str:
        return f"{instruction}\n\n{request}".strip()
    return prompt


def _reader(text: str):
    return lambda: text


def serve(config: Config, stdio: bool = False) -> None:
    """Serve the tools for an MCP host until it stops (stdio) or Ctrl-C (HTTP). Max can ask
    `bach status` meanwhile (status.py): it answers "claude". The hub takes the patch's
    playground and instances, so the tools work for the active instance; it answers
    no prompts (there is no local model)."""
    from .chat.hub import Hub
    bridge, status = start_bridge(config, "serve")
    try:
        mcp = mcp_app(config, bridge)
        Hub(bridge, status)
        status.started()
        if stdio:
            mcp.run(transport="stdio")
            return
        import uvicorn
        print(f"Bach tools for MCP hosts at {config.mcp_url}", flush=True)
        uvicorn.run(mcp.streamable_http_app(), host=config.server.host, port=config.server.port, log_level="warning")
    finally:
        status.off()
        bridge.stop()


def desktop_entry() -> Dict[str, Any]:
    """Claude Desktop launches Bach with this Python and these arguments."""
    return {"command": sys.executable, "args": [MAIN_PY, "serve", "--stdio"], "cwd": REPO_ROOT}


def register_desktop(path: str = CLAUDE_DESKTOP_CONFIG) -> str:
    """Add Bach to Claude Desktop's configuration, keeping everything else in it. Returns what was done."""
    data: Dict[str, Any] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        with open(path + ".bak", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    servers = data.setdefault("mcpServers", {})
    for name in [n for n, s in servers.items() if MAIN_PY in (s.get("args") or []) and n != SERVER_NAME]:
        del servers[name]  # an earlier entry for this same Bach, under another name
    servers[SERVER_NAME] = desktop_entry()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)
    return f"Claude Desktop: \"{SERVER_NAME}\" added to {path}. Restart Claude Desktop to load it."


def claude_code_commands(config: Config) -> List[str]:
    """Claude Code: start its own Bach (stdio), or join the one run.command started (HTTP)."""
    launch = " ".join(shlex.quote(a) for a in [sys.executable, MAIN_PY, "serve", "--stdio"])
    return [f"claude mcp add --scope user {SERVER_NAME} -- {launch}",
            f"claude mcp add --scope user --transport http {SERVER_NAME} {config.mcp_url}"]


__all__ = ["mcp_app", "serve", "register_desktop", "claude_code_commands", "desktop_entry", "SERVER_NAME"]
