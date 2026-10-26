"""
engine.py
---------
One conversation with the local model. Every local client drives it: the chat
page (web.py), the terminal (terminal.py) and eval (evaluate.py). For each
message from the user it:

    1. takes a /score or /algo prefix as the mode (prompt/modes.py), unless the
       conversation is with an instance, whose type fixes the mode
    2. appends the instrument docs the message names (prompt/docs.py)
    3. sends the conversation to the model, with the mode's part of the skill as
       system prompt and the mode's tools (model/client.py)
    4. runs the tools the model calls, here in this process (tools/inprocess.py),
       and sends their answers back, until the model answers without a tool
       call or max_tool_rounds is reached

and reports each step as an event, as it happens:

    {"type": "mode", "mode": "algo"}                      the mode is set by a prefix
    {"type": "docs", "added": ["strings/cello", ...]}     docs appended to the message
    {"type": "thinking", "text": ...}                     a piece of reasoning
    {"type": "text", "text": ...}                         a piece of the answer
    {"type": "calling", "name": ..., "chars": ...}        a tool call being written (llama-server only)
    {"type": "round", "finish": ..., "usage": {...}, "seconds": ...}   one reply of the model ended
    {"type": "retry", "reason": ...}                      a reply that looped is asked again
    {"type": "tool_call", "id": ..., "name": ..., "arguments": {...}}
    {"type": "tool_result", "id": ..., "name": ..., "result": ...}
    {"type": "done", "finish": "stop" | "length" | "rounds"}
    {"type": "error", "message": ...}

A client that stops reading at a tool_call (eval does) ends the turn before
that tool runs.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterator, List, Optional, Set

import httpx
from mcp.server.fastmcp import FastMCP

from ..config import Config
from ..model.client import ModelClient, Reply, ToolCall
from ..prompt.docs import DocLibrary
from ..prompt.modes import DEFAULT_MODE, KIND_MODE, KIND_NOTE, split_prefix, tools_for
from ..prompt.skill import skill_for
from ..tools.inprocess import LocalTools
from ..tools.session import new_conversation, use_conversation

Event = Dict[str, Any]

# A reply that runs out of tokens having shown nothing (no text, no reasoning, no
# finished tool call) looped inside a tool call: it is asked again this many times.
LOOP_RETRIES = 1


class Conversation:
    """The history of one chat, its mode and the docs it has already read.

    kind: the type of the instance it is for (session.KINDS), which fixes the mode; None
    for a chat whose mode the /score and /algo prefixes choose."""

    def __init__(self, client: ModelClient, tools: LocalTools, skill: str,
                 docs: Optional[DocLibrary] = None, max_tool_rounds: int = 8, kind: Optional[str] = None) -> None:
        self.client = client
        self.tools = tools
        self.skill = skill  # the skill file, with its mode markers
        self.docs = docs
        self.max_tool_rounds = max_tool_rounds
        self.kind = kind
        self._specs = tools.specs()
        self.new()

    def new(self) -> None:
        """Start a new chat: no history, the default mode, no docs read yet."""
        self.mode = KIND_MODE[self.kind] if self.kind else DEFAULT_MODE
        self.history: List[Dict[str, Any]] = []
        self.seen_docs: Set[str] = set()
        self.number = new_conversation()

    def cancel(self) -> None:
        """Stop the reply being written (from another thread, e.g. the chat page's Stop)."""
        self.client.cancel()

    def system_prompt(self) -> str:
        skill = skill_for(self.skill, self.mode)
        return f"{skill}\n{KIND_NOTE[self.kind]}\n" if self.kind else skill

    def mode_tools(self) -> List[Dict[str, Any]]:
        return tools_for(self._specs, self.mode)

    def send(self, text: str, max_tokens: Optional[int] = None) -> Iterator[Event]:
        """Send one user message and follow the model until it answers. Yields events."""
        use_conversation(self.number)
        mode, rest = split_prefix(text) if self.kind is None else (None, text)
        if mode:
            self.mode = mode
            yield {"type": "mode", "mode": mode}
            if rest == text:  # only the prefix: switch, ask nothing
                yield {"type": "done", "finish": "stop"}
                return
            text = rest
        if self.docs is not None:
            text, added = self.docs.augment_text(text, self.seen_docs)
            if added:
                yield {"type": "docs", "added": added}
        self.history.append({"role": "user", "content": text})

        seen_calls: Set[str] = set()
        for _ in range(self.max_tool_rounds):
            reply = yield from self._ask(max_tokens)
            if reply is None:
                return
            self.history.append(_assistant_message(reply))
            if reply.finish == "length" or not reply.tool_calls:
                yield {"type": "done", "finish": "length" if reply.finish == "length" else "stop"}
                return
            for call in reply.tool_calls:
                yield {"type": "tool_call", "id": call.id, "name": call.name, "arguments": call.arguments}
                result = self._run(call, seen_calls)
                self.history.append({"role": "tool", "tool_call_id": call.id, "content": result})
                yield {"type": "tool_result", "id": call.id, "name": call.name, "result": result}
        yield {"type": "done", "finish": "rounds"}

    def _ask(self, max_tokens: Optional[int]) -> Iterator[Event]:
        """One request to the model, streamed as events; returns its Reply (None after an error)."""
        messages = [{"role": "system", "content": self.system_prompt()}] + self.history
        tools = self.mode_tools()
        for attempt in range(1 + LOOP_RETRIES):
            started = time.time()
            reply: Optional[Reply] = None
            try:
                for kind, value in self.client.stream(messages, tools, max_tokens):
                    if kind == "reply":
                        reply = value
                    elif kind == "calling":
                        yield {"type": "calling", **value}
                    else:
                        yield {"type": kind, "text": value}
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                yield {"type": "error", "message": f"the model server: {exc}"}
                return None
            assert reply is not None
            yield {"type": "round", "finish": reply.finish, "usage": reply.usage,
                   "seconds": round(time.time() - started, 1)}
            looped = (reply.finish == "length" and not reply.text.strip() and not reply.thinking.strip()
                      and all(call.error for call in reply.tool_calls))
            if looped and attempt < LOOP_RETRIES:
                yield {"type": "retry", "reason": "the reply ran out of tokens inside a tool call; asking again"}
                continue
            return reply
        return None

    def _run(self, call: ToolCall, seen: Set[str]) -> str:
        if call.error:
            return f"ERROR: {call.error}. Nothing was run. Call {call.name} again with the whole arguments."
        signature = json.dumps([call.name, call.arguments], sort_keys=True, default=str)
        if signature in seen:
            return "You already made this exact call in this turn and have its result. Do not repeat it: answer now."
        seen.add(signature)
        return self.tools.call(call.name, call.arguments)


def _assistant_message(reply: Reply) -> Dict[str, Any]:
    message: Dict[str, Any] = {"role": "assistant", "content": reply.text}
    if reply.tool_calls:
        message["tool_calls"] = [{"id": c.id, "type": "function", "function": {
            "name": c.name, "arguments": "{}" if c.error else json.dumps(c.arguments, ensure_ascii=False)}}
            for c in reply.tool_calls]
    return message


def build_conversation(config: Config, client: ModelClient, app: FastMCP, kind: Optional[str] = None) -> Conversation:
    """A conversation set up from bachmcp.toml, using the tools of `app` (tools/registry.py);
    with `kind`, for an instance of that type."""
    return Conversation(client, LocalTools(app), config.skill_source(),
                        DocLibrary() if config.chat.docs else None, config.chat.max_tool_rounds, kind)


__all__ = ["Conversation", "build_conversation", "Event", "LOOP_RETRIES"]
