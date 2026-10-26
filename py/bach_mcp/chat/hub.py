"""
hub.py
------
The centre. Every message, whoever sends it (Max over UDP, the chat page over
HTTP, the terminal), is one line (bridge/protocol.py) handed to handle(); every
answer goes out from here, to Max and to every page. Nothing is kept anywhere
else: the page only shows what the hub says.

The hub holds the playground (tools/playground.py), the map of the instances
in the patch (name -> type), the active instance and one conversation per
instance. An instance's type fixes how the model works for it (chat/engine.py),
and the tools serve the instance whose prompt is being answered, else the
active one (tools/session.py).

Into the hub:

    set_playground <path>                     the folder for everything the model makes
    clear_instance_names_map                  empty the map
    add_instance_names_map <name> <type>      generator | transformer | selector | writer
    set_active_instance <name>
    <name> prompt <text>                      to that instance's conversation
    <name> stop                               stop its answer (or its turn in the queue)
    <name> new                                a new conversation (the old one stays in prompts/)

Out of the hub, to Max and to the page:

    set_playground <path>  clear_instance_names_map  add_instance_names_map <name> <type>
    set_active_instance <name>  <name> prompt <text>  <name> new     echoed
    <name> queued                             waits for another instance's answer
    <name> thinking                           the model started
    <name> tool <tool> <first line of what the tool answered>
    <name> answer <text>                      the whole answer, once
    <name> done <tokens> <ms>
    <name> stopped
    <name> error <message>
    mcp_info warning <text>                   something to fix (a bad path, an unknown type)

Only to the page (Max does not need them):

    state <state> <model> <message>           the model: starting, loading, ready, no_model ...
    <name> delta <text>                       a piece of the answer
    <name> reasoning <text>                   a piece of the reasoning
    <name> note <text>                        docs added, a reply asked again
    <name> tool_call <tool> <arguments as JSON>
    <name> tool_result <tool> <its answer>
    <name> history <JSON>                     a saved conversation, when a page connects

An echo never goes back to Max when Max sent it. Lines the hub does not know
(an instance's answers to the tools, such as `<name> algo_loaded`) are left to
the bridge, where the tools wait for them.

Prompts are answered one at a time, in the order they came: there is one model.
Each conversation is saved in the playground as prompts/<name>.jsonl, one
message per line, and read again when the instance is next prompted.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from ..bridge.protocol import Word, line, words
from ..tools.playground import prepare
from ..tools.session import KINDS, NoTarget, Target, serve_targets
from .engine import Conversation

SERVER_COMMANDS = ("set_playground", "clear_instance_names_map", "add_instance_names_map", "set_active_instance")
INSTANCE_COMMANDS = ("prompt", "stop", "new")
WEB_ONLY = ("state", "delta", "reasoning", "note", "tool_call", "tool_result", "history")
HISTORY_SHOWN = 400  # messages of a saved conversation sent to a page that connects


@dataclass
class Message:
    """One line going out, with its words; web_only lines never reach Max."""
    text: str
    words: List[str]
    web_only: bool = False


Client = Callable[[Message], None]
MakeConversation = Callable[[str], Conversation]  # a conversation for an instance of this type


class Hub:
    """Handles every line and sends every answer; answers prompts one at a time, on its own thread.

    bridge: the MaxBridge; status: Bach's state (utilities/status.py); make: builds a
    conversation for an instance type, or None when Bach has no local model (Claude's door).
    Creating the hub connects it: the bridge offers it every line from Max, and the tools
    ask it which instance they serve."""

    def __init__(self, bridge: Any, status: Any, make: Optional[MakeConversation] = None) -> None:
        self.bridge = bridge
        self.status = status
        self.make = make
        self.playground = ""
        self.instances: Dict[str, str] = {}
        self.active = ""
        self._conversations: Dict[str, Conversation] = {}
        self._clients: List[Client] = []
        self._lock = threading.RLock()
        self._queue: Deque[Tuple[str, str]] = deque()
        self._wake = threading.Condition(self._lock)
        self._answering = ""                 # the instance whose prompt is being answered
        self._turn: Optional[Target] = None  # its target, while the tools work for it
        self._stopping = threading.Event()
        self._running = True
        self._worker = threading.Thread(target=self._work, name="bach-hub", daemon=True)
        self._worker.start()
        bridge.on_line(lambda text: self.handle(text, "max"))
        serve_targets(self.target)
        status.on_change(lambda: self._send(*self._state(), web_only=True))

    # ── Clients ────────────────────────────────────────────────────────── #

    def subscribe(self, client: Client) -> Callable[[], None]:
        """Have every line going out handed to client (from any thread); returns how to stop."""
        with self._lock:
            self._clients.append(client)
        return lambda: self._unsubscribe(client)

    def _unsubscribe(self, client: Client) -> None:
        with self._lock:
            if client in self._clients:
                self._clients.remove(client)

    def _send(self, *said: Word, web_only: bool = False, to_max: bool = True) -> None:
        text = line(*said)
        if to_max and not web_only:
            self.bridge.send(text)
        message = Message(text, words(text), web_only)
        with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                client(message)
            except Exception:  # noqa: BLE001 — a client that went away is dropped
                self._unsubscribe(client)

    def _warn(self, text: str) -> None:
        self._send("mcp_info", "warning", text)

    def _state(self) -> List[Word]:
        return ["state", self.status.state, self.status.model, self.status.message]

    def snapshot(self) -> List[str]:
        """What a page that connects needs: the state, the playground, the map, the active
        instance, the saved conversations and what is being answered."""
        with self._lock:
            out = [line(*self._state())]
            if self.playground:
                out.append(line("set_playground", self.playground))
            out.append(line("clear_instance_names_map"))
            out += [line("add_instance_names_map", name, kind) for name, kind in self.instances.items()]
            if self.active:
                out.append(line("set_active_instance", self.active))
            for name in self.instances:
                saved = self._saved(name)
                if saved:
                    out.append(line(name, "history", json.dumps(saved[-HISTORY_SHOWN:], ensure_ascii=False)))
            if self._answering:
                out.append(line(self._answering, "thinking"))
            out += [line(name, "queued") for name, _ in self._queue]
        return out

    # ── Lines in ───────────────────────────────────────────────────────── #

    def handle(self, text: str, origin: str = "max") -> bool:
        """Act on one line from Max, the page ("web") or the terminal. False if it is not
        the hub's: the bridge then keeps it for the tools that wait for it."""
        said = words(text)
        if not said:
            return False
        echo = origin != "max"  # what Max sent goes back only to the pages
        head = said[0]
        if head == "set_playground":
            self._set_playground(" ".join(said[1:]), echo)
        elif head == "clear_instance_names_map":
            with self._lock:
                self.instances.clear()
            self._send("clear_instance_names_map", to_max=echo)
        elif head == "add_instance_names_map":
            self._add_instance(said[1:], echo)
        elif head == "set_active_instance":
            self._set_active(said[1] if len(said) > 1 else "", echo)
        elif len(said) >= 2 and said[1] in INSTANCE_COMMANDS:
            name, command = said[0], said[1]
            if command == "prompt":
                self._prompt(name, " ".join(said[2:]).strip(), echo)
            elif command == "stop":
                self._stop(name)
            else:
                self._new(name, echo)
        else:
            return False
        return True

    def _set_playground(self, path: str, echo: bool) -> None:
        try:
            root = prepare(path)
        except ValueError as exc:
            self._warn(f"playground: {exc}")
            return
        with self._lock:
            if root != self.playground:
                self._conversations.clear()  # theirs are saved in the other playground
            self.playground = root
        self._send("set_playground", root, to_max=echo)

    def _add_instance(self, args: List[str], echo: bool) -> None:
        if len(args) < 2:
            self._warn("add_instance_names_map needs a name and a type")
            return
        name, kind = args[0], args[1]
        if kind not in KINDS:
            self._warn(f"{name}: unknown type {kind} (one of {', '.join(KINDS)})")
            return
        with self._lock:
            if self.instances.get(name) not in (None, kind):
                self._conversations.pop(name, None)  # another type: another way of working
            self.instances[name] = kind
        self._send("add_instance_names_map", name, kind, to_max=echo)

    def _set_active(self, name: str, echo: bool) -> None:
        with self._lock:
            known = name in self.instances
            if known:
                self.active = name
        if known:
            self._send("set_active_instance", name, to_max=echo)
        else:
            self._warn(f"set_active_instance: no instance {name or '(no name)'} in the map")

    def _refusal(self, name: str) -> str:
        """Why a prompt to this instance cannot be answered now, or ""."""
        kind = self.instances.get(name)
        if kind is None:
            return f"no instance {name} in the map"
        if not self.playground:
            return "no playground: the patch sends set_playground <folder>"
        if kind == "selector":
            return "selector instances are not built yet"
        if self.make is None:
            return self.status.message or "no local model here: this Bach serves Claude through MCP"
        if not self.status.ready:
            return self.status.message or f"the model is not ready ({self.status.state})"
        return ""

    def _prompt(self, name: str, text: str, echo: bool) -> None:
        if not text:
            self._send(name, "error", "the prompt is empty")
            return
        with self._lock:
            refusal = self._refusal(name)
            if not refusal:
                waits = bool(self._answering or self._queue)
                self._queue.append((name, text))
        if refusal:
            self._send(name, "error", refusal)
            return
        self._send(name, "prompt", text, to_max=echo)
        if waits:
            self._send(name, "queued")
        with self._wake:
            self._wake.notify()

    def _stop(self, name: str) -> None:
        with self._lock:
            answering = self._answering == name
            waiting = [item for item in self._queue if item[0] == name]
            for item in waiting:
                self._queue.remove(item)
            conversation = self._conversations.get(name)
        if answering:
            self._stopping.set()
            if conversation is not None:
                conversation.cancel()
        elif waiting:
            self._send(name, "stopped")

    def _new(self, name: str, echo: bool) -> None:
        with self._lock:
            busy = self._answering == name or any(item[0] == name for item in self._queue)
            if not busy:
                self._conversations.pop(name, None)
                path = self._history_file(name)
        if busy:
            self._send(name, "error", "an answer is still being written: stop it first")
            return
        if path and os.path.exists(path):
            os.replace(path, path[:-len(".jsonl")] + time.strftime("-%Y%m%d-%H%M%S.jsonl"))
        self._send(name, "new", to_max=echo)

    # ── The tools' instance ────────────────────────────────────────────── #

    def target(self) -> Target:
        """The instance the tools serve: the one being answered, else the active one."""
        with self._lock:
            if self._turn is not None:
                return self._turn
            if not self.playground:
                raise NoTarget("no playground: the patch sends set_playground <folder>")
            if not self.active:
                raise NoTarget("no instance is active: select one (set_active_instance <name>)")
            kind = self.instances.get(self.active)
            if kind is None:
                raise NoTarget(f"no instance {self.active} in the map")
            return Target(self.active, kind, self.playground)

    # ── Answering ──────────────────────────────────────────────────────── #

    def close(self) -> None:
        with self._wake:
            self._running = False
            self._wake.notify_all()
        serve_targets(None)

    def _work(self) -> None:
        while True:
            with self._wake:
                while self._running and not self._queue:
                    self._wake.wait()
                if not self._running:
                    return
                name, text = self._queue.popleft()
                self._answering = name
                self._stopping.clear()
            try:
                self._answer(name, text)
            except Exception as exc:  # noqa: BLE001 — said, never lost; the next prompt goes on
                self._send(name, "error", f"{type(exc).__name__}: {exc}")
                self._send(name, "done", 0, 0)
            finally:
                with self._lock:
                    self._answering = ""
                    self._turn = None

    def _answer(self, name: str, text: str) -> None:
        with self._lock:
            refusal = self._refusal(name)  # the map or the model may have changed while it waited
            if not refusal:
                target = Target(name, self.instances[name], self.playground)
                conversation = self._conversation(target)
                self._turn = target
        if refusal:
            self._send(name, "error", refusal)
            return
        before = len(conversation.history)
        started, tokens, answer, finish = time.time(), 0, [], "stop"
        self._send(name, "thinking")
        events = conversation.send(text)
        try:
            for event in events:
                if self._stopping.is_set():
                    break
                kind = event["type"]
                if kind == "text":
                    answer.append(event["text"])
                    self._send(name, "delta", event["text"], web_only=True)
                elif kind == "thinking":
                    self._send(name, "reasoning", event["text"], web_only=True)
                elif kind == "tool_call":
                    self._send(name, "tool_call", event["name"],
                               json.dumps(event["arguments"], ensure_ascii=False), web_only=True)
                elif kind == "tool_result":
                    self._send(name, "tool_result", event["name"], event["result"], web_only=True)
                    self._send(name, "tool", event["name"], (event["result"].splitlines() or [""])[0])
                elif kind == "round":
                    tokens += (event.get("usage") or {}).get("completion_tokens", 0)
                elif kind == "docs":
                    self._send(name, "note", f"instrument docs: {', '.join(event['added'])}", web_only=True)
                elif kind == "retry":
                    self._send(name, "note", event["reason"], web_only=True)
                elif kind == "error":
                    self._send(name, "error", event["message"])
                elif kind == "done":
                    finish = event["finish"]
        finally:
            events.close()
            self._save(conversation, target, before, text)
        if self._stopping.is_set():
            self._send(name, "stopped")
            return
        if finish == "length":
            self._send(name, "error", "the answer reached the reply limit ([generation] max_tokens)")
        elif finish == "rounds":
            self._send(name, "error", "stopped after [chat] max_tool_rounds tool calls")
        if "".join(answer).strip():
            self._send(name, "answer", "".join(answer).strip())
        self._send(name, "done", tokens, int((time.time() - started) * 1000))

    # ── Conversations, kept in the playground ──────────────────────────── #

    def _history_file(self, name: str) -> str:
        return os.path.join(self.playground, "prompts", f"{name}.jsonl") if self.playground else ""

    def _saved(self, name: str) -> List[Dict[str, Any]]:
        """The saved messages of an instance's conversation (each user message with its "prompt")."""
        path = self._history_file(name)
        if not path or not os.path.exists(path):
            return []
        out = []
        with open(path, encoding="utf-8") as f:
            for row in f:
                try:
                    out.append(json.loads(row))
                except json.JSONDecodeError:
                    continue  # a line cut by a crash: the rest is still the conversation
        return out

    def _conversation(self, target: Target) -> Conversation:
        """The instance's conversation: in memory, else the saved one, else a new one."""
        conversation = self._conversations.get(target.name)
        if conversation is None:
            assert self.make is not None
            conversation = self.make(target.kind)
            conversation.history = [{k: v for k, v in m.items() if k != "prompt"} for m in self._saved(target.name)]
            self._conversations[target.name] = conversation
        return conversation

    def _save(self, conversation: Conversation, target: Target, before: int, prompt: str) -> None:
        """Add the messages of this turn to prompts/<name>.jsonl; the user's message keeps
        the prompt as it was typed (the model also got the docs added to it)."""
        added = conversation.history[before:]
        if not added or not target.playground:
            return
        rows = [dict(added[0], prompt=prompt) if added[0].get("role") == "user" else added[0], *added[1:]]
        os.makedirs(target.prompts, exist_ok=True)
        with open(os.path.join(target.prompts, f"{target.name}.jsonl"), "a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


__all__ = ["Hub", "Message", "SERVER_COMMANDS", "INSTANCE_COMMANDS", "WEB_ONLY"]
