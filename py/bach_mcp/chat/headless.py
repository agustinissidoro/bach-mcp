"""
headless.py
-----------
One conversation with Claude, run behind the hub: bachmcp.server claude answers
an instance's prompts through Claude Code, on the user's own Claude account (no
API key). It has the same face as engine.py's Conversation (send, cancel,
history), so the hub treats both alike.

Each message starts one `claude -p`, which reads the instance's part of the
skill, and has only that part's tools, over MCP from this same Bach. The hub
says which instance the tools serve while it answers (tools/session.py). The
next message resumes the same Claude session: its id is kept with the assistant's
messages in prompts/<name>.jsonl.

Claude Code's lines (--output-format stream-json) become engine.py's events. With
--include-partial-messages it also says when it sends a request (system status
requesting) and when each block starts, before the block is whole: those become
stage events, so Max hears "sent", "thinking", "writing", "calling <tool>" as they happen.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, Iterator, List, Optional, Set

from ..claude import login_command
from ..config import REPO_ROOT, Config
from ..prompt.docs import DocLibrary
from ..prompt.modes import KIND_MODE, KIND_NOTE, MODE_TOOLS
from ..prompt.skill import skill_for
from ..tools.session import new_conversation, use_conversation
from .engine import Event

SERVER = "bach"  # its name in the MCP configuration given to Claude Code: mcp__bach__<tool>
PREFIX = f"mcp__{SERVER}__"
NO_SESSION = "No conversation found"


class ClaudeConversation:
    """The history of one instance's chat with Claude Code. command: the `claude` program, or None."""

    def __init__(self, command: Optional[str], config: Config, kind: str) -> None:
        self.command = command
        self.url = config.mcp_url
        self.skill = config.skill_source()
        self.docs = DocLibrary() if config.chat.docs else None
        self.max_tool_rounds = config.chat.max_tool_rounds
        self.kind = kind
        self.mode = KIND_MODE[kind]
        self.history: List[Dict[str, Any]] = []
        self.seen_docs: Set[str] = set()
        self.session = ""  # Claude Code's session: the hub restores it from the saved conversation
        self.number = new_conversation()
        self._process: Optional[subprocess.Popen] = None

    def cancel(self) -> None:
        """Stop the answer being written (from another thread)."""
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def system_prompt(self) -> str:
        return f"{skill_for(self.skill, self.mode)}\n{KIND_NOTE[self.kind]}\n"

    def command_line(self) -> List[str]:
        config = {"mcpServers": {SERVER: {"type": "http", "url": self.url}}}
        line = [self.command or "claude", "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
                "--mcp-config", json.dumps(config), "--strict-mcp-config", "--setting-sources", "",
                "--tools", "", "--allowedTools", *[PREFIX + tool for tool in MODE_TOOLS[self.mode]],
                "--append-system-prompt", self.system_prompt(),
                "--max-turns", str(self.max_tool_rounds + 1)]
        return line + ["--resume", self.session] if self.session else line

    def send(self, text: str, max_tokens: Optional[int] = None) -> Iterator[Event]:
        """Send one user message and follow Claude until it answers. Yields events."""
        use_conversation(self.number)
        if self.docs is not None:
            text, added = self.docs.augment_text(text, self.seen_docs)
            if added:
                yield {"type": "docs", "added": added}
        self.history.append({"role": "user", "content": text})
        if not self.command:
            yield {"type": "error", "message": "Claude Code is not on this computer: install it, or write in Claude Desktop"}
            yield {"type": "done", "finish": "stop"}
            return
        answer: List[str] = []
        try:
            again = yield from self._run(text, answer)
            if again:  # the saved session is gone (Claude Code cleans up old ones): a new one
                self.session = ""
                yield from self._run(text, answer)
        finally:
            self.cancel()
            self.history.append({"role": "assistant", "content": "".join(answer), "session": self.session})

    def _run(self, text: str, answer: List[str]) -> Iterator[Event]:
        """One `claude -p`. Returns True if it could not find the session it was told to resume."""
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}  # also when Bach itself runs inside Claude Code
        try:
            process = subprocess.Popen(self.command_line(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, cwd=REPO_ROOT, env=env)
        except OSError as exc:
            yield {"type": "error", "message": f"Claude Code did not start: {exc}"}
            yield {"type": "done", "finish": "stop"}
            return False
        self._process = process
        process.stdin.write(text)
        process.stdin.close()
        names: Dict[str, str] = {}
        ended, other = False, []
        for raw in process.stdout:
            try:
                said = json.loads(raw)
            except json.JSONDecodeError:
                other.append(raw.strip())  # its error output
                continue
            ended = ended or said.get("type") == "result"
            for event in _events(said, names, answer, self):
                yield event
        process.wait()
        if ended or process.returncode < 0:  # negative: stopped by cancel()
            return False
        words = " ".join(line for line in other if line)
        if self.session and NO_SESSION in words:
            return True
        yield {"type": "error", "message": f"Claude Code stopped: {words[-300:] or f'exit code {process.returncode}'}"}
        yield {"type": "done", "finish": "stop"}
        return False


def _events(said: Dict[str, Any], names: Dict[str, str], answer: List[str], chat: ClaudeConversation) -> Iterator[Event]:
    """The events of one line of Claude Code's stream."""
    kind = said.get("type")
    if said.get("session_id"):
        chat.session = said["session_id"]
    if kind == "system" and said.get("subtype") == "status" and said.get("status") == "requesting":
        yield {"type": "stage", "stage": "sent"}
    elif kind == "stream_event":
        block = (said.get("event") or {}).get("content_block") or {}
        if said["event"].get("type") == "content_block_start":
            if block.get("type") == "thinking":
                yield {"type": "stage", "stage": "thinking"}
            elif block.get("type") == "text":
                yield {"type": "stage", "stage": "writing"}
            elif block.get("type") == "tool_use":
                yield {"type": "stage", "stage": "calling", "detail": [block.get("name", "").removeprefix(PREFIX)]}
    elif kind == "assistant":
        if said.get("error"):  # Claude Code's own message (not logged in ...): the result line reports it
            return
        for block in said["message"].get("content") or []:
            if block.get("type") == "text":
                answer.append(block["text"])
                yield {"type": "text", "text": block["text"]}
            elif block.get("type") == "thinking":
                yield {"type": "thinking", "text": block.get("thinking", "")}
            elif block.get("type") == "tool_use":
                name = block["name"].removeprefix(PREFIX)
                names[block["id"]] = name
                yield {"type": "tool_call", "id": block["id"], "name": name, "arguments": block.get("input") or {}}
    elif kind == "user":
        content = said["message"].get("content")
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_result":
                id_ = block.get("tool_use_id", "")
                yield {"type": "tool_result", "id": id_, "name": names.get(id_, ""), "result": _text(block.get("content"))}
    elif kind == "result":
        yield {"type": "round", "finish": "stop", "usage": {"completion_tokens": (said.get("usage") or {}).get("output_tokens", 0)}}
        if said.get("subtype") == "error_max_turns":
            yield {"type": "done", "finish": "rounds"}
            return
        if said.get("is_error"):
            yield {"type": "error", "message": _why(str(said.get("result") or said.get("subtype")), chat.command)}
        yield {"type": "done", "finish": "stop"}


def _why(message: str, command: Optional[str]) -> str:
    if "authenticate" in message or "log in" in message.lower() or "/login" in message:
        return f"Claude Code is not logged in. In a terminal, run: {login_command(command or 'claude')}"
    return message


def _text(content: Any) -> str:
    """A tool result: a text, or a list of blocks; Claude Code shows a tool's text as {"result": text}."""
    if isinstance(content, list):
        content = "\n".join(block.get("text", "") for block in content if isinstance(block, dict))
    text = str(content or "")
    try:
        wrapped = json.loads(text)
    except ValueError:
        return text
    if isinstance(wrapped, dict) and list(wrapped) == ["result"] and isinstance(wrapped["result"], str):
        return wrapped["result"]
    return text


__all__ = ["ClaudeConversation"]
