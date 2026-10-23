"""FastMCP app factory and tool registration.

The tools, the same for every host (Claude over MCP, the local model through
the web chat or the terminal agent):

    score_tools.py  write_score, read_score, clear_score: the JSON score
    pitch_tools.py  exact pitch arithmetic in midicents (p2mc, get_chord, ...)
    algo_tools.py   send_algorithm: a JavaScript algorithm run in Max

They speak bach's hierarchy and units as JSON, never llll. Skill: BACH_SKILL.md.
The earlier raw llll tool set is kept in deprecated/py/bach_mcp/mcp_app_full.py.
"""

import functools
import logging
import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .algo_tools import register_algo_tools
from .modes import skill_for
from .pitch_tools import register_pitch_tools
from .score_tools import register_score_tools
from .server import BachMCPServer

_SKILL_PATH = os.path.join(os.path.dirname(__file__), "BACH_SKILL.md")


def load_skill(mode: Optional[str] = None, raw: bool = False) -> str:
    """Read the skill doc (also used as system prompt).

    mode: "score" or "algo" for that mode's part only (see modes.py); None for all of it.
    raw: the file as it is, with its mode markers.
    """
    with open(_SKILL_PATH, encoding="utf-8") as f:
        text = f.read()
    return text if raw else skill_for(text, mode)

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


def create_mcp_app(bach: BachMCPServer, instructions: Optional[str] = None) -> FastMCP:
    """Create the MCP app with every Bach tool registered."""
    # The skill doubles as the server instructions, for hosts that use them.
    mcp = FastMCP("bach", instructions=instructions or load_skill(), log_level="WARNING")

    # Wrap mcp.tool so every registered tool logs its name, arguments, and result
    # in a human-readable form. Toggle off with BACH_TOOL_LOG=0.
    if os.getenv("BACH_TOOL_LOG", "1") != "0":
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
    register_score_tools(mcp, bach)
    register_algo_tools(mcp, bach)
    return mcp
