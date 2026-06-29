"""
mcp_tools.py
------------
In-process bridge between the FastMCP server and the provider-agnostic agent.

The FastMCP app built by `create_mcp_app()` is the SINGLE source of truth for
tools — the same definitions an MCP host (e.g. Claude Desktop) consumes over the
serve transport (HTTP or stdio). This bridge lets the local agent consume them
directly, in-process:

    - `list_tools()` returns each MCP tool as a neutral `ToolSpec`
      (name, description, JSON-Schema parameters).
    - `call_tool()` invokes a tool by name and returns its output as a string
      suitable for feeding back to the model.

No tool schemas or dispatch logic are duplicated here; everything is derived
from the FastMCP instance. To add or change a tool, edit `mcp_app.py` only.
"""

from __future__ import annotations

import asyncio
import json
import math
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from .llm import ToolSpec


def _json_safe(obj: Any) -> Any:
    """Strip values that are not valid JSON from a tool schema.

    Several tools use float('nan') as a "not supplied" sentinel default, which
    surfaces in the generated JSON Schema as `default: NaN`. NaN/Infinity are not
    JSON-compliant and break strict serializers, so we drop any such entry.
    Removing a `default: NaN` is harmless: the parameter stays optional and the
    real default is applied when the model omits it.
    """
    if isinstance(obj, dict):
        return {
            k: _json_safe(v)
            for k, v in obj.items()
            if not (isinstance(v, float) and not math.isfinite(v))
        }
    if isinstance(obj, list):
        return [
            _json_safe(v)
            for v in obj
            if not (isinstance(v, float) and not math.isfinite(v))
        ]
    return obj


def _stringify_result(result: Any) -> str:
    """Render a FastMCP call_tool result as a string for the model.

    FastMCP (mcp>=1.x) returns a (content_blocks, structured_dict) tuple.
    We prefer the text of the content blocks (pretty JSON for dict-returning
    tools, the raw string for str-returning tools), and fall back to the
    structured payload.
    """
    blocks: Any = result
    structured: Any = None
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], (list, tuple)):
        blocks, structured = result

    if isinstance(blocks, (list, tuple)):
        texts = [getattr(b, "text", None) for b in blocks]
        texts = [t for t in texts if t is not None]
        if texts:
            return "\n".join(texts)

    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)
    if isinstance(blocks, dict):
        return json.dumps(blocks, ensure_ascii=False)
    return json.dumps({"ok": True}, ensure_ascii=False)


class McpToolBridge:
    """Exposes a FastMCP app's tools to the synchronous agent loop."""

    def __init__(self, mcp: FastMCP) -> None:
        self._mcp = mcp
        # FastMCP's list_tools/call_tool are async; the REPL is synchronous,
        # so we drive them on a dedicated event loop owned by this bridge.
        self._loop = asyncio.new_event_loop()

    def list_tools(self) -> List[ToolSpec]:
        tools = self._loop.run_until_complete(self._mcp.list_tools())
        specs: List[ToolSpec] = []
        for t in tools:
            specs.append(
                ToolSpec(
                    name=t.name,
                    description=t.description or "",
                    parameters=_json_safe(t.inputSchema or {"type": "object", "properties": {}}),
                )
            )
        return specs

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        try:
            result = self._loop.run_until_complete(
                self._mcp.call_tool(name, arguments or {})
            )
        except Exception as exc:  # ToolError, validation errors, transport errors, ...
            return json.dumps(
                {"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False
            )
        return _stringify_result(result)

    def close(self) -> None:
        try:
            self._loop.close()
        except Exception:
            pass
