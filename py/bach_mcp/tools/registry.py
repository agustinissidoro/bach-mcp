"""
registry.py
-----------
Builds the one MCP app that holds the 15 tools. Both doors use it: the Claude
door serves it over MCP, the local chat calls its tools in-process. A tool is
defined once, here and in the modules it registers:

    pitch_tools.py  exact pitch arithmetic in midicents (p2mc, get_chord, ...)
    score_tools.py  write_score, read_score, clear_score: the JSON score
    algo_tools.py   send_algorithm: a JavaScript algorithm run in Max
    instance_tools.py  get_instances, set_active_instance: which instance the others serve

They speak bach's hierarchy and units as JSON, never llll. Which instance a
call is for, and so where its files go, the tools ask session.py.

A tool may wait for Max or for Node (seconds), so none runs on the server's event
loop: each call runs on a thread of its own, and the page's stream and the other
MCP sessions go on meanwhile. The tools share one bridge to Max and its answers, so
they still run one at a time, whichever app they were called through.
"""

import functools
import logging
import threading
from typing import Any, Callable, Dict, Iterable, Optional, Set, Type

import anyio

from mcp.server.fastmcp import FastMCP

from .algo_tools import register_algo_tools
from .instance_tools import register_instance_tools
from .pitch_tools import register_pitch_tools
from .score_tools import register_score_tools
from .session import calling_directly

_tool_log = logging.getLogger("bach.tools")
_one_at_a_time = threading.Lock()  # every app's tools: they share the bridge and what Max answers


def _configure_tool_logging() -> None:
    """Attach a human-readable handler to the bach.tools logger (once per process)."""
    if getattr(_tool_log, "_bach_configured", False):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    _tool_log.addHandler(handler)
    _tool_log.setLevel(logging.INFO)
    _tool_log.propagate = False  # don't double-print through uvicorn's root handlers
    _tool_log._bach_configured = True  # type: ignore[attr-defined]


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _format_call_args(kwargs: Dict[str, Any]) -> str:
    """Render tool kwargs as a compact, readable `key=value` list."""
    return ", ".join(f"{k}={_truncate(repr(v), 120)}" for k, v in kwargs.items())


def threaded(fn: Callable[..., Any], direct: bool = False, log_calls: bool = False) -> Callable[..., Any]:
    """fn as the app runs it: on a thread of its own (never on the event loop), one tool at a
    time, marked as a direct call when `direct`, and logged when `log_calls`."""

    def run(kwargs: Dict[str, Any]) -> Any:
        with _one_at_a_time:
            if log_calls:
                _tool_log.info("→ %s(%s)", fn.__name__, _format_call_args(kwargs))
            try:
                if direct:
                    with calling_directly():
                        result = fn(**kwargs)
                else:
                    result = fn(**kwargs)
            except Exception as exc:  # noqa: BLE001 — log then re-raise
                if log_calls:
                    _tool_log.info("✗ %s raised %s: %s", fn.__name__, type(exc).__name__, exc)
                raise
            if log_calls:
                _tool_log.info("← %s  %s", fn.__name__, _truncate(repr(result), 200))
            return result

    @functools.wraps(fn)
    async def on_a_thread(**kwargs: Any):
        return await anyio.to_thread.run_sync(run, kwargs)

    return on_a_thread


class _Registrar:
    """What the tool modules register on. It has FastMCP's `tool()` decorator, and adds each
    tool to the app as the app must run it (threaded), or leaves it out (only)."""

    def __init__(self, mcp: FastMCP, keep: Optional[Set[str]], direct: bool, log_calls: bool) -> None:
        self.mcp, self.keep, self.direct, self.log_calls = mcp, keep, direct, log_calls

    def tool(self, *args: Any, **kwargs: Any):
        def register(fn):
            name = kwargs.get("name") or (args[0] if args else fn.__name__)
            if self.keep is None or name in self.keep:
                self.mcp.add_tool(threaded(fn, self.direct, self.log_calls), *args, **kwargs)
            return fn

        return register


def create_tools(bridge: Any, node: str = "node", log_calls: bool = True,
                 instructions: Optional[str] = None,
                 path: str = "/mcp", only: Optional[Iterable[str]] = None, direct: bool = False,
                 app: Type[FastMCP] = FastMCP) -> FastMCP:
    """The MCP app with every tool registered.

    bridge: the MaxBridge (an OfflineBridge when the tools are only listed); node: [algo] node
    in bachmcp.toml; log_calls: [server] tool_log; instructions: the skill, for hosts that
    read them (Claude). The local chat sends its own. path: where it is served over HTTP.
    only: the names of the tools to keep (a mode's, prompt/modes.py MODE_TOOLS); None: all.
    direct: this app is the one a Claude written to directly reaches (/mcp): its calls are for
    the active instance, also while another instance's prompt is being answered (session.py).
    app: the FastMCP class to build (claude.py's connect passes its own, which hands calls on).
    """
    mcp = app("bach", instructions=instructions, log_level="WARNING", streamable_http_path=path)
    if log_calls:
        _configure_tool_logging()
    tools = _Registrar(mcp, None if only is None else set(only), direct, log_calls)
    register_pitch_tools(tools)
    register_score_tools(tools, bridge)
    register_algo_tools(tools, bridge, node)
    register_instance_tools(tools)
    return mcp
