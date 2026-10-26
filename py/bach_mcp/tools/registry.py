"""
registry.py
-----------
Builds the one MCP app that holds the 13 tools. Both doors use it: the Claude
door serves it over MCP, the local chat calls its tools in-process. A tool is
defined once, here and in the modules it registers:

    pitch_tools.py  exact pitch arithmetic in midicents (p2mc, get_chord, ...)
    score_tools.py  write_score, read_score, clear_score: the JSON score
    algo_tools.py   send_algorithm: a JavaScript algorithm run in Max

They speak bach's hierarchy and units as JSON, never llll. Which instance a
call is for, and so where its files go, the tools ask session.py.
"""

import functools
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .algo_tools import register_algo_tools
from .pitch_tools import register_pitch_tools
from .score_tools import register_score_tools

_tool_log = logging.getLogger("bach.tools")


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


def create_tools(bridge: Any, node: str = "node", log_calls: bool = True,
                 instructions: Optional[str] = None) -> FastMCP:
    """The MCP app with every tool registered.

    bridge: the MaxBridge (an OfflineBridge when the tools are only listed); node: [algo] node
    in bachmcp.toml; log_calls: [server] tool_log; instructions: the skill, for hosts that
    read them (Claude). The local chat sends its own.
    """
    mcp = FastMCP("bach", instructions=instructions, log_level="WARNING")

    # Wrap mcp.tool so every registered tool logs its name, arguments, and result
    # in a human-readable form.
    if log_calls:
        _configure_tool_logging()
        _register_tool = mcp.tool

        def _logging_tool(*d_args: Any, **d_kwargs: Any):
            decorator = _register_tool(*d_args, **d_kwargs)

            def wrap(fn):
                @functools.wraps(fn)
                def logged(*args: Any, **kwargs: Any):
                    _tool_log.info("→ %s(%s)", fn.__name__, _format_call_args(kwargs))
                    try:
                        result = fn(*args, **kwargs)
                    except Exception as exc:  # noqa: BLE001 — log then re-raise
                        _tool_log.info("✗ %s raised %s: %s", fn.__name__, type(exc).__name__, exc)
                        raise
                    _tool_log.info("← %s  %s", fn.__name__, _truncate(repr(result), 200))
                    return result

                return decorator(logged)

            return wrap

        mcp.tool = _logging_tool  # type: ignore[method-assign]

    register_pitch_tools(mcp)
    register_score_tools(mcp, bridge)
    register_algo_tools(mcp, bridge, node)
    return mcp
