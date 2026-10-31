"""
claude.py
---------
The door for Claude (Claude Desktop, Claude Code) and any other MCP host.
Claude brings its own model; Bach gives it the tools, what to read, and Max.

    mcp_app(config, bridge)   the 13 tools (tools/registry.py) plus what Claude reads:
                              the skill as the server's instructions, /score and /algo
                              as two prompts, the instrument docs as resources
    serve(config, stdio)      serves that app: over HTTP at [server] (bachmcp.server claude),
                              or over stdio for a host that starts Bach itself
    connect(config)           Claude Desktop's side: it can only launch a command, so this
                              answers it and passes the tool calls to the Bach Max started.
                              It holds no port, so opening Claude blocks nothing in Max
    register_desktop()        adds Bach to Claude Desktop's configuration
    register_code(config)     adds Bach to Claude Code: with its command, or in its file
    claude_code_commands()    the lines that add Bach to Claude Code

The local chat (`run`) does not serve Claude: with bachmcp.server local, Claude has no way in.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
from typing import Any, Dict, List, Optional

import httpx
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP

from .bridge.max import OfflineBridge
from .config import REPO_ROOT, Config
from .prompt.docs import DocLibrary
from .prompt.modes import MODE_TOOLS
from .utilities.status import quit_on_signals, start_bridge, watch_input
from .tools.registry import create_tools

SERVER_NAME = "bach"
MAIN_PY = os.path.join(REPO_ROOT, "py", "main.py")
CLAUDE_DESKTOP_CONFIG = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
CLAUDE_CODE_CONFIG = os.path.expanduser("~/.claude.json")
CLAUDE_CODE_PLACES = ("~/.local/bin/claude", "~/.claude/local/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude")

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
    quit_on_signals(status)
    try:
        mcp = mcp_app(config, bridge)
        Hub(bridge, status)
        status.started()
        if stdio:
            mcp.run(transport="stdio")
            return
        import uvicorn
        watch_input(status)
        print(f"Bach tools for MCP hosts at {config.mcp_url}", flush=True)
        uvicorn.run(mcp.streamable_http_app(), host=config.server.host, port=config.server.port, log_level="warning")
    finally:
        status.off()
        bridge.stop()


def connect(config: Config) -> None:
    """Claude Desktop's Bach: what Claude reads is answered here, the same with Max on or off,
    and each tool call goes to the Bach that bachmcp.server claude started."""
    mcp = mcp_app(config, OfflineBridge())

    @mcp._mcp_server.call_tool(validate_input=False)
    async def call_tool(name: str, arguments: Dict[str, Any]) -> types.CallToolResult:
        try:
            async with streamablehttp_client(config.mcp_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.call_tool(name, arguments)
        except Exception:  # noqa: BLE001 — the transport ends in an exception group, whatever the cause
            return types.CallToolResult(isError=True,
                                        content=[types.TextContent(type="text", text=_why_unreachable(config))])

    mcp.run(transport="stdio")


def _why_unreachable(config: Config) -> str:
    """What Claude should say when the tools cannot be reached. Only the chat page has /api/state."""
    try:
        if httpx.get(f"{config.url}/api/state", timeout=2).status_code == 200:
            return "Bach is running in local mode, which does not serve Claude. Start [bachmcp.server claude] in Max."
    except httpx.HTTPError:
        pass
    return f"Bach is not running at {config.mcp_url}. Start [bachmcp.server claude] in Max."


def desktop_entry() -> Dict[str, Any]:
    """Claude Desktop launches this Python with these arguments."""
    return {"command": sys.executable, "args": [MAIN_PY, "connect"], "cwd": REPO_ROOT}


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
    """Claude Code: join the Bach that Max started (HTTP), or start its own (stdio: it then holds Max's port)."""
    launch = " ".join(shlex.quote(a) for a in [sys.executable, MAIN_PY, "serve", "--stdio"])
    return [f"claude mcp add --scope user --transport http {SERVER_NAME} {config.mcp_url}",
            f"claude mcp add --scope user {SERVER_NAME} -- {launch}"]


def find_claude_code() -> Optional[str]:
    """The `claude` command: on the PATH, or where its installers put it."""
    found = shutil.which("claude")
    if found:
        return found
    places = (os.path.expanduser(p) for p in CLAUDE_CODE_PLACES)
    return next((p for p in places if os.access(p, os.X_OK)), None)


def register_code(config: Config, command: Optional[str] = None, path: str = CLAUDE_CODE_CONFIG) -> bool:
    """Add Bach to Claude Code, for all its projects: with its command, or else in its file,
    which is where the command writes. False if Claude Code is not on this computer."""
    if command:
        subprocess.run([command, "mcp", "remove", "--scope", "user", SERVER_NAME], capture_output=True)
        add = claude_code_commands(config)[0].split()[1:]
        if subprocess.run([command, *add], capture_output=True).returncode == 0:
            return True
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    shutil.copy2(path, path + ".bak")
    data.setdefault("mcpServers", {})[SERVER_NAME] = {"type": "http", "url": config.mcp_url}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))  # it holds the account: only its owner reads it
    os.replace(tmp, path)
    with open(path, encoding="utf-8") as f:
        return SERVER_NAME in json.load(f).get("mcpServers", {})


__all__ = ["mcp_app", "serve", "connect", "register_desktop", "register_code", "find_claude_code",
           "claude_code_commands", "desktop_entry", "SERVER_NAME"]
