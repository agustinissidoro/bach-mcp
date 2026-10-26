"""
inprocess.py
------------
The tools of the MCP app (registry.py), called directly in this process: this
is how the local chat uses them. Claude reaches the same app over MCP. The
tools are defined only once, in the app; nothing here repeats a schema.

    specs()            every tool in the OpenAI format the model server takes
    call(name, args)   run a tool and return its answer as text for the model
"""

from __future__ import annotations

import asyncio
import json
import math
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP


def _json_safe(obj: Any) -> Any:
    """Drop values JSON cannot hold (NaN, Infinity) from a tool schema; the parameter stays optional."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items() if not (isinstance(v, float) and not math.isfinite(v))}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj if not (isinstance(v, float) and not math.isfinite(v))]
    return obj


def _as_text(result: Any) -> str:
    """A FastMCP call_tool result ((content blocks, structured) in mcp>=1.x) as text for the model."""
    blocks: Any = result
    structured: Any = None
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], (list, tuple)):
        blocks, structured = result
    if isinstance(blocks, (list, tuple)):
        texts = [t for t in (getattr(b, "text", None) for b in blocks) if t is not None]
        if texts:
            return "\n".join(texts)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)
    return json.dumps(blocks if isinstance(blocks, dict) else {"ok": True}, ensure_ascii=False)


class LocalTools:
    """The tools of one MCP app, for a caller in the same process."""

    def __init__(self, app: FastMCP) -> None:
        self.app = app

    def specs(self) -> List[Dict[str, Any]]:
        tools = asyncio.run(self.app.list_tools())
        return [{"type": "function", "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": _json_safe(t.inputSchema or {"type": "object", "properties": {}}),
                }} for t in tools]

    def call(self, name: str, arguments: Dict[str, Any]) -> str:
        try:
            return _as_text(asyncio.run(self.app.call_tool(name, arguments or {})))
        except Exception as exc:  # unknown tool, wrong arguments, ...: the model reads it and corrects itself
            return f"ERROR: {type(exc).__name__}: {exc}"


__all__ = ["LocalTools"]
