"""
claude.py
---------
The door for Claude (Claude Desktop, Claude Code) and any other MCP host.
Claude brings its own model; Bach gives it the tools, what to read, and Max.

    mcp_app(config, bridge)   the 15 tools (tools/registry.py) plus what Claude reads:
                              the skill as the server's instructions, /score and /algo
                              as two prompts, the instrument docs as resources ([chat] docs)
    headless_apps(config, bridge)  one per mode at /mcp/headless/<mode>: only that mode's tools
                              and no instructions, for the `claude -p` Bach starts
                              (chat/headless.py). It gets its instance's part of the skill as
                              its system prompt: the same skill and tools the local model gets
    serve(config, stdio)      serves that app: over HTTP at [server] (bachmcp.server claude),
                              with the chat page beside it (chat/web.py), where prompts from
                              Max and the page are answered by Claude Code (chat/headless.py),
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

import glob
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
from .prompt.modes import MODE_TOOLS, MODES
from .utilities.status import quit_on_signals, start_bridge, watch_input
from .tools.registry import create_tools

SERVER_NAME = "bach"
MAIN_PY = os.path.join(REPO_ROOT, "py", "main.py")
CLAUDE_DESKTOP_CONFIG = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
CLAUDE_CODE_CONFIG = os.path.expanduser("~/.claude.json")
CLAUDE_CODE_PLACES = ("~/.local/bin/claude", "~/.claude/local/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude")
CLAUDE_DESKTOP_CODE = "~/Library/Application Support/Claude/claude-code/*/*/claude.app/Contents/MacOS/claude"

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

    for doc in DocLibrary().docs.values() if config.chat.docs else []:  # [chat] docs = false: none
        title = doc.text.splitlines()[0].lstrip("# ").strip()
        mcp.resource(f"bach://docs/{doc.key}", name=doc.key, mime_type="text/markdown",
                     description=f"{title}: ranges, techniques and how to mark them, in midicents.")(_reader(doc.text))
    return mcp


def headless_apps(config: Config, bridge: Any) -> List[FastMCP]:
    """For the Claude Code Bach starts itself, one app per mode: that mode's tools alone, as the
    local model has them (prompt/modes.py tools_for), and no instructions: its skill is the
    instance's part, given as its system prompt (chat/headless.py). The docs reach it inside the
    messages, as they reach the local model, so there are no resources either."""
    return [create_tools(bridge, config.algo.node, log_calls=config.server.tool_log,
                         path=f"/mcp/headless/{mode}", only=MODE_TOOLS[mode]) for mode in MODES]


def _mode_prompt(instruction: str):
    def prompt(request: str = "") -> str:
        return f"{instruction}\n\n{request}".strip()
    return prompt


def _reader(text: str):
    return lambda: text


def serve(config: Config, stdio: bool = False) -> None:
    """Serve the tools for an MCP host until it stops (stdio) or Ctrl-C (HTTP). Max can ask
    `bach status` meanwhile (status.py): it answers "claude". The hub takes the patch's
    playground and instances, so the tools work for the instance being answered, else the
    active one. Over HTTP it answers prompts with Claude Code; over stdio the host is the
    one Claude is talking to, so it answers none."""
    from .chat.headless import ClaudeConversation, settings_line
    from .chat.hub import Hub
    bridge, status = start_bridge(config, "serve")
    quit_on_signals(status)
    if not stdio:  # over stdio, the output is the host's channel
        print(f"Bach — config: {config.source}")
        print(f"  claude    {settings_line(config)}")
        print(f"  docs      {'added to messages that name an instrument' if config.chat.docs else 'off'}", flush=True)
    try:
        mcp = mcp_app(config, bridge)
        headless = [] if stdio else headless_apps(config, bridge)
        command = None if stdio else find_claude_code()
        make = None if stdio else lambda instance_type: ClaudeConversation(command, config, instance_type)
        hub = Hub(bridge, status, make)
        status.on_quit(hub.close)
        if stdio:
            status.started()
            mcp.run(transport="stdio")
            return
        _serve_http(config, hub, status, mcp, headless)
    finally:
        status.off()
        bridge.stop()


def _serve_http(config: Config, hub: Any, status: Any, mcp: FastMCP, headless: List[FastMCP]) -> None:
    """The tools at /mcp and the chat page at / on one port: the page shows every instance's
    conversation with Claude Code, and prompts written there are answered like Max's."""
    import threading
    import time
    import webbrowser

    import uvicorn

    from .chat.web import close_page_tabs, create_app
    http = uvicorn.Server(uvicorn.Config(create_app(hub, status, mcp, headless), host=config.server.host,
                                         port=config.server.port, log_level="warning",
                                         timeout_graceful_shutdown=1))  # the pages' streams never end

    def when_started() -> None:
        while not http.started and not http.should_exit:
            time.sleep(0.05)
        if http.started:
            status.started()
            print(f"Bach tools for MCP hosts at {config.mcp_url}\nChat with Claude: {config.url}", flush=True)
            if config.chat.open_browser:
                webbrowser.open(config.url)

    status.on_quit(lambda: close_page_tabs(config.url))
    threading.Thread(target=when_started, daemon=True).start()
    watch_input(status)
    try:
        http.run()
    finally:
        close_page_tabs(config.url)


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
    """What Claude should say when the tools cannot be reached. Both Bachs answer /api/state;
    only the one that serves Claude says "claude"."""
    try:
        reply = httpx.get(f"{config.url}/api/state", timeout=2)
        if reply.status_code == 200 and reply.json().get("state") != "claude":
            return "Bach is running in local mode, which does not serve Claude. Start [bachmcp.server claude] in Max."
    except (httpx.HTTPError, ValueError):
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
    """The `claude` command: on the PATH, where its installers put it, or the newest one
    that came with Claude Desktop."""
    found = shutil.which("claude")
    if found:
        return found
    places = [os.path.expanduser(p) for p in CLAUDE_CODE_PLACES]
    places += sorted(glob.glob(os.path.expanduser(CLAUDE_DESKTOP_CODE)), key=_version, reverse=True)
    return next((p for p in places if os.access(p, os.X_OK)), None)


def login_command(command: str) -> str:
    """The line a person runs to log this Claude Code in."""
    return f"{shlex.quote(command)} auth login"


def logged_in(command: str) -> Optional[bool]:
    """Whether this Claude Code can answer on its own, as it would when Max starts it: without what
    a parent Claude Code session passes down. None if it cannot tell."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE" and not k.startswith("CLAUDE_CODE_")}
    try:
        done = subprocess.run([command, "auth", "status"], capture_output=True, text=True, timeout=20, env=env)
        answer = json.loads(done.stdout).get("loggedIn")
    except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError):
        return None
    return answer if isinstance(answer, bool) else None


def _version(path: str) -> List[int]:
    """claude-code/2.1.309/... -> [2, 1, 309]"""
    folder = path.split("/claude-code/")[1].split("/")[0]
    return [int(n) for n in folder.split(".") if n.isdigit()]


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
           "login_command", "logged_in",
           "claude_code_commands", "desktop_entry", "SERVER_NAME"]
