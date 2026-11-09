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
       system prompt and the mode's tools (model/client.py). An algorithm or a score
       that a later call replaced, and an outdated read_score answer, are sent as a
       short placeholder (without_replaced); the history itself, and the saved
       conversation, keep them whole
    4. runs the tools the model calls, here in this process (tools/inprocess.py),
       and sends their answers back, until the model answers without a tool
       call: after max_tool_rounds rounds of tools it has one more request to
       answer, as Claude Code has (--max-turns, chat/headless.py)

and reports each step as an event, as it happens:

    {"type": "mode", "mode": "algo"}                      the mode is set by a prefix
    {"type": "stage", "stage": "sent"}                    a request went to the model (each round)
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
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import httpx
from mcp.server.fastmcp import FastMCP

from ..config import Config
from ..model.client import ModelClient, Reply, ToolCall
from ..prompt.docs import DocLibrary
from ..prompt.modes import DEFAULT_MODE, TYPE_MODE, instance_skill, split_prefix, tools_for
from ..tools.inprocess import LocalTools
from ..tools.session import new_conversation, use_conversation

Event = Dict[str, Any]

# A reply that runs out of tokens having shown nothing (no text, no reasoning, no
# finished tool call) looped inside a tool call: it is asked again this many times.
LOOP_RETRIES = 1


class Conversation:
    """The history of one chat, its mode and the docs it has already read.

    instance_type: the type of the instance it is for (session.TYPES), which fixes the mode; None
    for a chat whose mode the /score and /algo prefixes choose."""

    def __init__(self, client: ModelClient, tools: LocalTools, skill: str,
                 docs: Optional[DocLibrary] = None, max_tool_rounds: int = 8, instance_type: Optional[str] = None) -> None:
        self.client = client
        self.tools = tools
        self.skill = skill  # the skill file, with its mode markers
        self.docs = docs
        self.max_tool_rounds = max_tool_rounds
        self.instance_type = instance_type
        self._specs = tools.specs()
        self.new()

    def new(self) -> None:
        """Start a new chat: no history, the default mode, no docs read yet."""
        self.mode = TYPE_MODE[self.instance_type] if self.instance_type else DEFAULT_MODE
        self.history: List[Dict[str, Any]] = []
        self.seen_docs: Set[str] = set()
        self.number = new_conversation()

    def cancel(self) -> None:
        """Stop the reply being written (from another thread, e.g. the chat page's Stop)."""
        self.client.cancel()

    def system_prompt(self) -> str:
        return instance_skill(self.skill, self.mode, self.instance_type)

    def mode_tools(self) -> List[Dict[str, Any]]:
        return tools_for(self._specs, self.mode)

    def send(self, text: str, max_tokens: Optional[int] = None) -> Iterator[Event]:
        """Send one user message and follow the model until it answers. Yields events."""
        use_conversation(self.number)
        mode, rest = split_prefix(text) if self.instance_type is None else (None, text)
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
        for _ in range(self.max_tool_rounds + 1):  # the rounds of tools, then the answer
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
        messages = [{"role": "system", "content": self.system_prompt()}] + without_replaced(self.history)
        tools = self.mode_tools()
        for attempt in range(1 + LOOP_RETRIES):
            started = time.time()
            reply: Optional[Reply] = None
            yield {"type": "stage", "stage": "sent"}  # the model now reads it: nothing comes until its first token
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


OLD_CODE = "(an earlier version of the file: a later send_algorithm replaced it)"
OLD_SCORE = "(an earlier score: a later write_score or clear_score replaced it)"
OLD_READ = "(an earlier answer: a later read_score of the same part replaced it)"
READ_DEFAULTS = {"voice": 0, "from_ms": -1.0, "to_ms": -1.0}


def without_replaced(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The history as the local model reads it, without what a later call replaced. A
    conversation is one instance, so one file and one roll: an older version is never needed again.

        send_algorithm  the code of every call but the last, and the last that loaded (its answer
                        starts with OK), becomes OLD_CODE
        write_score     the score of every call before the last that replaced the roll ("OK. Score
                        written") or cleared it becomes OLD_SCORE; later add=true calls stay
        read_score      an answer becomes OLD_READ when a later call with the same arguments
                        answered the score again ("Unchanged ..." points back to it, so it stays)

    The history itself, and the saved conversation, keep everything. It depends only on the
    history, so a request changes the prefix the model server has cached only from the version
    just replaced on. Claude Code keeps its own history (chat/headless.py): this is the local path's."""
    return _old_reads(_old_scores(_old_code(history)))


def _calls(history: List[Dict[str, Any]], *names: str) -> List[Tuple[int, int, Dict[str, Any]]]:
    """(message index, call index, call) of every call of these tools, in order."""
    return [(i, k, call) for i, m in enumerate(history) if m.get("role") == "assistant"
            for k, call in enumerate(m.get("tool_calls") or []) if call["function"]["name"] in names]


def _answers(history: List[Dict[str, Any]]) -> Dict[str, str]:
    return {m.get("tool_call_id"): str(m.get("content", "")) for m in history if m.get("role") == "tool"}


def _arguments(call: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        arguments = json.loads(call["function"]["arguments"])
    except (json.JSONDecodeError, TypeError):
        return None
    return arguments if isinstance(arguments, dict) else None


def _replace_argument(out: List[Dict[str, Any]], i: int, k: int, key: str, value: str) -> bool:
    """out[i] with argument `key` of its call k set to value, as a copy; False if there was nothing to replace."""
    call = out[i]["tool_calls"][k]
    arguments = _arguments(call)
    if arguments is None or arguments.get(key) in (None, value):
        return False
    arguments[key] = value
    message = dict(out[i])
    message["tool_calls"] = [dict(c) for c in message["tool_calls"]]
    message["tool_calls"][k] = {**call, "function": {**call["function"], "arguments": json.dumps(arguments, ensure_ascii=False)}}
    out[i] = message
    return True


def _old_code(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    calls = _calls(history, "send_algorithm")
    if len(calls) < 2:
        return history
    answers = _answers(history)
    keep = {calls[-1][2]["id"]}
    loaded = [c["id"] for _, _, c in calls if answers.get(c["id"], "").startswith("OK")]
    if loaded:
        keep.add(loaded[-1])
    out = list(history)
    changed = [_replace_argument(out, i, k, "code", OLD_CODE) for i, k, call in calls if call["id"] not in keep]
    return out if any(changed) else history


def _old_scores(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    calls = _calls(history, "write_score", "clear_score")
    answers = _answers(history)
    replacing = [n for n, (_, _, call) in enumerate(calls)
                 if answers.get(call["id"], "").startswith(("OK. Score written", "Score cleared"))]
    if not replacing:
        return history
    out = list(history)
    changed = [_replace_argument(out, i, k, "score", OLD_SCORE) for i, k, call in calls[:replacing[-1]]
               if call["function"]["name"] == "write_score"]
    return out if any(changed) else history


def _old_reads(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    last: Dict[str, int] = {}  # the same arguments -> the index of the latest whole answer
    old: List[int] = []
    ids = {call["id"]: json.dumps({**READ_DEFAULTS, **(_arguments(call) or {})}, sort_keys=True)
           for _, _, call in _calls(history, "read_score")}
    for j, m in enumerate(history):
        same = ids.get(m.get("tool_call_id")) if m.get("role") == "tool" else None
        if same is None or str(m.get("content", "")).startswith(("Unchanged", "ERROR", OLD_READ)):
            continue
        if same in last:
            old.append(last[same])
        last[same] = j
    if not old:
        return history
    out = list(history)
    for j in old:
        out[j] = {**out[j], "content": OLD_READ}
    return out


def _assistant_message(reply: Reply) -> Dict[str, Any]:
    message: Dict[str, Any] = {"role": "assistant", "content": reply.text}
    if reply.tool_calls:
        message["tool_calls"] = [{"id": c.id, "type": "function", "function": {
            "name": c.name, "arguments": "{}" if c.error else json.dumps(c.arguments, ensure_ascii=False)}}
            for c in reply.tool_calls]
    return message


def build_conversation(config: Config, client: ModelClient, app: FastMCP, instance_type: Optional[str] = None) -> Conversation:
    """A conversation set up from bachmcp.toml, using the tools of `app` (tools/registry.py);
    with `instance_type`, for an instance of that type."""
    return Conversation(client, LocalTools(app), config.skill_source(),
                        DocLibrary() if config.chat.docs else None, config.chat.max_tool_rounds, instance_type)


__all__ = ["Conversation", "build_conversation", "Event", "LOOP_RETRIES"]
