"""
agent.py
--------
Provider-agnostic tool-calling agent for Bach.

`Agent` owns the conversation and the tool loop. It is independent of which
LLM backend is used (that lives behind `LLMProvider`) and of how tools are
defined (that lives behind `McpToolBridge`, backed by the MCP server). The
same loop therefore drives any cloud or local model against the same tools.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List

from .llm import AssistantTurn, LLMProvider, ToolSpec
from .mcp_tools import McpToolBridge


def _log(msg: str) -> None:
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


@dataclass
class AgentConfig:
    system_prompt: str = ""
    max_tool_rounds: int = 10
    stateful: bool = True


class Agent:
    """Runs chat turns, executing any tool calls against the MCP tool bridge."""

    def __init__(
        self,
        provider: LLMProvider,
        tools: McpToolBridge,
        config: AgentConfig | None = None,
    ) -> None:
        self._provider = provider
        self._tools = tools
        self.config = config or AgentConfig()
        self._tool_specs: List[ToolSpec] = tools.list_tools()
        self._history: List[Dict[str, Any]] = []
        _log(f"[Agent] Ready — {len(self._tool_specs)} tools exposed")

    @property
    def tool_specs(self) -> List[ToolSpec]:
        return self._tool_specs

    def reset_history(self) -> None:
        self._history = []

    def chat(self, user_message: str) -> str:
        self._history.append({"role": "user", "content": user_message})

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.config.system_prompt}
        ]
        if self.config.stateful:
            messages += self._history
        else:
            messages.append(self._history[-1])

        reply = self._run_tool_loop(messages)
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def _run_tool_loop(self, messages: List[Dict[str, Any]]) -> str:
        last_content = ""
        for round_num in range(self.config.max_tool_rounds):
            _log(f"[Agent] LLM call #{round_num + 1}")
            turn: AssistantTurn = self._provider.chat(messages, self._tool_specs)
            last_content = turn.content or ""

            if not turn.tool_calls:
                _log(f"[Agent] Final reply ({len(last_content)} chars)")
                return last_content

            assistant_msg = {
                "role": "assistant",
                "content": last_content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in turn.tool_calls
                ],
            }
            messages.append(assistant_msg)
            if self.config.stateful:
                self._history.append(assistant_msg)

            for tc in turn.tool_calls:
                _log(f"[Agent] tool: {tc.name}({tc.arguments})")
                result = self._tools.call_tool(tc.name, tc.arguments)
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
                messages.append(tool_msg)
                if self.config.stateful:
                    self._history.append(tool_msg)

        _log("[Agent] WARNING: max tool rounds reached")
        return last_content or "[max tool rounds reached]"
