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
active one (tools/session.py). A Claude written to directly lists the instances
and chooses the active one with two tools (tools/instance_tools.py); its calls
are always for the active one, also while another prompt is being answered.

An instance cannot be named like a line's first word (RESERVED): its lines would
be read as that command.

Into the hub:

    set_playground <path>                     the folder for everything the model makes
    set_profile [<name>]                      the skill's profile: skills/profiles/<name>.json
                                              (no name: none)
    set_skills [<name> ...]                   skills added after the profile's: skills/<name>.md
                                              (none: none). Each builds skills/.compiled.md
                                              (prompt/skills.py) and answers `server skills ...`
    get_skills                                build it again from the files and answer the same
    <name> set_profile [<name>]               the same for one instance: it reads only what it
    <name> set_skills [<name> ...]            chose (its own profile and skills), not the shared
    <name> get_skills                         ones; none of either: back to the shared ones.
                                              Answers `<name> skills ...`
    clear_instance_names_map                  empty the map
    add_instance_names_map <name> <type>      generator | transformer | selector | score | synth | fx; an instance
                                              that changes type starts a new conversation, as with `new`
    set_active_instance <name> [<type>]       with the type, the instance joins the map if new
    instances <name> <type> ...               Max's answer to `server get_instances`: the whole map
    <name> prompt <text>                      to that instance's conversation
    <name> stop                               stop its answer (or its turn in the queue)
    <name> new                                a new conversation (the old one stays in prompts/)
    <name> remove                             forget everything the hub holds for it: its answer
                                              (stopped) and prompts waiting, its conversation, its
                                              own profile and skills. Files stay: its prompts/<name>.jsonl
                                              is read again if it is prompted later

Out of the hub, to Max and to the page:

    set_playground <path>  clear_instance_names_map  add_instance_names_map <name> <type>
    set_active_instance <name>  <name> prompt <text>  <name> new     echoed
    <name> queued                             waits for another instance's answer
    <name> tool <tool> <first line of what the tool answered>
    <name> answer <text>                      the whole answer, once
    <name> done <tokens> <ms>
    <name> stopped
    <name> error <message>
    server warning <text>                   something to fix (a bad path, an unknown type)
    server skills <skill> ...               after set_profile, set_skills, get_skills: the files of the
    server skills length <tokens>           skill new conversations read, and its estimated tokens
                                            (no files and 0: the built-in skill, nothing chosen; after a
                                            warning, the last skill that was built)
    <name> skills <skill> ...               the same for one instance, after its own set_profile,
    <name> skills length <tokens>           set_skills, get_skills: what it reads, its own or shared

Only to Max, when a tool asks (get_instances, set_active_instance):

    server get_instances                    Max answers `instances <name> <type> ...`

To Max (and the pages), what happens to a prompt, whoever sent it; a stage is said
once, when it changes:

    server prompt <name> received             Bach has it
    server prompt <name> queued <n>           <n> prompts are answered before it
    server prompt <name> starting             its turn: the model is being set up (Claude Code starts)
    server prompt <name> sent                 the model has the prompt (and, later, each tool's answer)
    server prompt <name> thinking             it reasons
    server prompt <name> writing              it writes the answer
    server prompt <name> calling <tool>       it writes a tool call
    server prompt <name> running <tool>       the tool runs, here in Bach
    server prompt <name> done <tokens> <ms>
    server prompt <name> skills_size <tokens> at each prompt: the estimated tokens of the skill its
                                              conversation reads (the compiled file, else the built-in skill)
    server prompt <name> stopped
    server prompt <name> error <message>

Only to Max, after each answer:

    server answer <name> <text>
    server answer tokens <tokens>
    server answer time <ms>

Only to the page (Max does not need them):

    state <state> <model> <message>           the model: starting, loading, ready, no_model ...
    <name> thinking                           its turn started (Max gets server prompt <name> ... instead)
    <name> delta <text>                       a piece of the answer
    <name> reasoning <text>                   a piece of the reasoning
    <name> note <text>                        docs added, a reply asked again
    <name> tool_call <tool> <arguments as JSON>
    <name> tool_result <tool> <its answer>
    <name> history <JSON>                     its saved conversation (maybe []): when a page connects,
                                              with each instance in a map, and for every instance
                                              when the playground changes; not while it is answered

An echo never goes back to Max when Max sent it. Lines the hub does not know
(an instance's answers to the tools, such as `<name> algo_loaded`) are left to
the bridge, where the tools wait for them.

The skill: an instance reads its own choice (<name> set_profile / set_skills) if it
has one, else the shared one (set_profile / set_skills), else the skill bachmcp.toml
names (make builds it so). Each new conversation builds its skill again from the
files (so an edited skill file counts from the next one); if that fails, it keeps
the last one built. Before each prompt the hub checks what the instance reads: if
its profile or skills changed since its conversation began (its own or the shared
ones), the conversation is dropped, its file deleted, and a new one begins
(`<name> new` is said).

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
from ..prompt.skill import with_gen, with_verbosity
from ..prompt.skills import SkillError, build, estimate_tokens, remove_compiled
from ..tools.playground import prepare
from ..tools.session import TYPES, NoTarget, Target, direct, serve_instances, serve_targets
from .engine import Conversation

INSTANCE_COMMANDS = ("prompt", "stop", "new", "remove", "set_profile", "set_skills", "get_skills")
# First words that are not an instance: the hub's own commands, Max's requests (bridge/max.py),
# the lines for the server object and the page's state line.
RESERVED = ("set_playground", "set_profile", "set_skills", "get_skills", "clear_instance_names_map", "add_instance_names_map", "set_active_instance",
            "instances", "server", "bach", "state")
HISTORY_SHOWN = 400  # messages of a saved conversation sent to a page that connects
INSTANCES_WAIT = 1.5  # seconds a tool waits for Max to answer server get_instances


@dataclass
class Message:
    """One line going out, with its words; web_only lines never reach Max."""
    text: str
    words: List[str]
    web_only: bool = False


Client = Callable[[Message], None]
MakeConversation = Callable[[str], Conversation]  # a conversation for an instance of this type
Selection = Tuple[str, str, Tuple[str, ...]]  # whose choice ("" shared, or the instance), profile, skills


class Hub:
    """Handles every line and sends every answer; answers prompts one at a time, on its own thread.

    bridge: the MaxBridge; status: Bach's state (utilities/status.py); make: builds a
    conversation for an instance type (the local model's, or Claude Code's: chat/headless.py),
    or None when the host itself is the model (an MCP host that started Bach over stdio).
    Creating the hub connects it: the bridge offers it every line from Max, and the tools
    ask it which instance they serve."""

    def __init__(self, bridge: Any, status: Any, make: Optional[MakeConversation] = None,
                 verbose: bool = True) -> None:
        self.bridge = bridge
        self.status = status
        self.make = make
        self.verbose = verbose  # [algo] verbose: the wording of the skill the playground's files build
        self.playground = ""
        self.profile = ""  # the shared choice of skills
        self.skills: List[str] = []
        self.own: Dict[str, Tuple[str, List[str]]] = {}  # an instance's own choice: (profile, skills)
        self._built: Dict[str, Tuple[str, List[str], int]] = {}  # "" (shared) or an instance -> the last
                                                                 # skill built: (text, files, tokens)
        self._began_with: Dict[str, Selection] = {}  # what each conversation in memory began with
        self.instances: Dict[str, str] = {}
        self.active = ""
        self._conversations: Dict[str, Conversation] = {}
        self._clients: List[Client] = []
        self._lock = threading.RLock()
        self._queue: Deque[Tuple[str, str]] = deque()
        self._wake = threading.Condition(self._lock)
        self._answering = ""                 # the instance whose prompt is being answered
        self._said: List[Word] = []          # the stage of its answer last said to Max
        self._turn: Optional[Target] = None  # its target, while the tools work for it
        self._stopping = threading.Event()
        self._map_answered = threading.Event()  # Max answered `server get_instances`
        self._running = True
        self._worker = threading.Thread(target=self._work, name="bach-hub", daemon=True)
        self._worker.start()
        bridge.on_line(lambda text: self.handle(text, "max"))
        serve_targets(self.target)
        serve_instances(self)
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
        self._send("server", "warning", text)

    def _state(self) -> List[Word]:
        return ["state", self.status.state, self.status.model, self.status.message]

    def snapshot(self) -> List[str]:
        """What a page that connects needs: the state, the playground, the map, the active
        instance, the saved conversations and what is being answered."""
        with self._lock:
            out = [line(*self._state())]
            if self.playground:
                out.append(line("set_playground", self.playground))
            if self.profile:
                out.append(line("set_profile", self.profile))
            if self.skills:
                out.append(line("set_skills", *self.skills))
            for name, (profile, skills) in self.own.items():
                if profile:
                    out.append(line(name, "set_profile", profile))
                if skills:
                    out.append(line(name, "set_skills", *skills))
            out.append(line("clear_instance_names_map"))
            out += [line("add_instance_names_map", name, instance_type) for name, instance_type in self.instances.items()]
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
        elif head == "set_profile":
            self._choose_skills("", " ".join(said[1:]).strip(), None, echo)
        elif head == "set_skills":
            self._choose_skills("", None, said[1:], echo)
        elif head == "get_skills":
            self._build_skill("")
            self._report_skills("")
        elif head == "clear_instance_names_map":
            with self._lock:
                self.instances.clear()
            self._send("clear_instance_names_map", to_max=echo)
        elif head == "add_instance_names_map":
            self._add_instance(said[1:], echo)
        elif head == "set_active_instance":
            self._set_active(said[1] if len(said) > 1 else "", said[2] if len(said) > 2 else "", echo)
        elif head == "instances":
            self._replace_map(said[1:])
        elif len(said) >= 2 and said[1] in INSTANCE_COMMANDS:
            name, command = said[0], said[1]
            if command == "prompt":
                self._prompt(name, " ".join(said[2:]).strip(), echo)
            elif command == "set_profile":
                self._choose_skills(name, " ".join(said[2:]).strip(), None, echo)
            elif command == "set_skills":
                self._choose_skills(name, None, said[2:], echo)
            elif command == "get_skills":
                self._build_skill(name)
                self._report_skills(name)
            elif command == "stop":
                self._stop(name)
            elif command == "remove":
                self._remove(name, echo)
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
            moved = root != self.playground
            if moved:
                self._conversations.clear()  # theirs are saved in the other playground
                self._began_with.clear()
            self.playground = root
            names = list(self.instances)
        self._send("set_playground", root, to_max=echo)
        if moved:
            self._histories(names)
            if self.profile or self.skills:
                self._build_skill("")
                self._report_skills("")
            for name in list(self.own):
                self._build_skill(name)
                self._report_skills(name)

    # ── The skill (prompt/skills.py) ───────────────────────────────────── #

    def _selection(self, name: str) -> Selection:
        """What an instance reads ("": the shared choice): (whose, profile, skills). whose is the
        instance itself when it has its own choice, else "" (the shared one, maybe nothing)."""
        if name and name in self.own:
            profile, skills = self.own[name]
            return name, profile, tuple(skills)
        return "", self.profile, tuple(self.skills)

    def _choose_skills(self, name: str, profile: Optional[str], skills: Optional[List[str]], echo: bool) -> None:
        """set_profile (skills None) or set_skills (profile None), shared (name "") or for one
        instance; then the skill is built and what it reads is said."""
        with self._lock:
            if name:
                old_profile, old_skills = self.own.get(name, ("", []))
                chosen = (old_profile if profile is None else profile, old_skills if skills is None else list(skills))
                if chosen[0] or chosen[1]:
                    self.own[name] = chosen
                else:
                    self.own.pop(name, None)
                    self._built.pop(name, None)
            else:
                if profile is not None:
                    self.profile = profile
                if skills is not None:
                    self.skills = list(skills)
                chosen = self.profile, list(self.skills)
            playground = self.playground
        head = [name] if name else []
        if profile is not None:
            self._send(*head, "set_profile", *([profile] if profile else []), to_max=echo)
        else:
            self._send(*head, "set_skills", *chosen[1], to_max=echo)
        if name and not (chosen[0] or chosen[1]) and playground:
            remove_compiled(playground, name)
        if not playground:
            self._warn("skills: no playground yet; the skill is built when set_playground comes")
        elif not chosen[0] and not chosen[1] and not name:
            with self._lock:
                self._built.pop("", None)
            self._warn("skills: no profile and no skills chosen; new conversations read the built-in skill")
        else:
            self._build_skill(name)
        self._report_skills(name)

    def _report_skills(self, name: str) -> None:
        """<server|name> skills <files> / ... skills length <tokens>: what new conversations read."""
        with self._lock:
            whose = self._selection(name)[0]
            _, files, tokens = self._built.get(whose, ("", [], 0))
        head = name or "server"
        self._send(head, "skills", *files)
        self._send(head, "skills", "length", tokens)

    def _build_skill(self, name: str, warn: bool = True) -> str:
        """Build what the instance (or, with "", every instance without its own choice) reads,
        write its compiled file and keep it; "" if nothing is chosen. On failure, a warning
        and the last one built. warn: also the warnings of a build that worked (a skill chosen
        twice, no core)."""
        with self._lock:
            playground = self.playground
            whose, profile, skills = self._selection(name)
            last = self._built.get(whose, ("", [], 0))[0]
        if not playground or not (profile or skills):
            return ""
        try:
            compiled = build(playground, profile, list(skills), whose)
        except (SkillError, OSError) as exc:
            self._warn(f"skills{' of ' + whose if whose else ''}: {exc}"
                       + ("; new conversations keep the last skill built" if last else ""))
            return last
        if warn:
            for warning in compiled.warnings:
                self._warn(f"skills{' of ' + whose if whose else ''}: {warning}")
        text = with_gen(with_verbosity(compiled.text, self.verbose), self.verbose)
        with self._lock:
            self._built[whose] = (text, [file for file, _ in compiled.used], compiled.tokens)
        return text

    def _skill_changed(self, name: str) -> bool:
        """Before a prompt: if what the instance reads changed since its conversation began, the
        conversation goes, its file is deleted and the next one begins clean. Call with the lock held."""
        began = self._began_with.get(name)
        if began is None or began[1:] == self._selection(name)[1:]:  # the same profile and skills, whoever chose them
            return False
        self._conversations.pop(name, None)
        self._began_with.pop(name, None)
        path = self._history_file(name)
        if path and os.path.exists(path):
            os.remove(path)
        return True

    def _add_instance(self, args: List[str], echo: bool) -> None:
        if len(args) < 2:
            self._warn("add_instance_names_map needs a name and a type")
            return
        name, instance_type = args[0], args[1]
        if instance_type not in TYPES:
            self._warn(f"{name}: unknown type {instance_type} (one of {', '.join(TYPES)})")
            return
        if name in RESERVED:
            self._warn(f"an instance cannot be named {name}: rename it")
            return
        with self._lock:
            if self.instances.get(name) not in (None, instance_type):
                self._start_over(name)
            self.instances[name] = instance_type
            first = not self.active  # so that Claude's tools always have an instance
            if first:
                self.active = name
        self._send("add_instance_names_map", name, instance_type, to_max=echo)
        self._histories([name])
        if first:
            self._send("set_active_instance", name, to_max=echo)

    def _set_active(self, name: str, instance_type: str, echo: bool) -> None:
        """The active instance. With its type (Max sends it), a name not yet in the map joins
        it: Max may say so before it sends the map again."""
        if instance_type:
            if instance_type not in TYPES:
                self._warn(f"{name}: unknown type {instance_type} (one of {', '.join(TYPES)})")
                return
            if name in RESERVED:
                self._warn(f"an instance cannot be named {name}: rename it")
                return
            with self._lock:
                joins = self.instances.get(name) != instance_type
                if joins:
                    if name in self.instances:
                        self._start_over(name)
                    self.instances[name] = instance_type
            if joins:
                self._send("add_instance_names_map", name, instance_type, to_max=echo)
                self._histories([name])
        with self._lock:
            known = name in self.instances
            if known:
                self.active = name
        if known:
            self._send("set_active_instance", name, to_max=echo)
        else:
            self._warn(f"set_active_instance: no instance {name or '(no name)'} in the map")

    def _replace_map(self, args: List[str]) -> None:
        """Max's whole map (`instances <name> <type> ...`): it replaces the hub's, and the pages
        get it as usual. An active instance no longer there gives way to the first."""
        pairs = [(args[i], args[i + 1]) for i in range(0, len(args) - 1, 2)]
        bad = [f"{name} {instance_type}" for name, instance_type in pairs if instance_type not in TYPES]
        if len(args) % 2 or bad:
            self._warn(f"instances: expected <name> <type> pairs, got {' '.join(args)}")
        for name in [name for name, _ in pairs if name in RESERVED]:
            self._warn(f"an instance cannot be named {name}: rename it")
        pairs = [pair for pair in pairs if pair[0] not in RESERVED]
        with self._lock:
            fresh = {name: instance_type for name, instance_type in pairs if instance_type in TYPES}
            for name, instance_type in self.instances.items():
                if fresh.get(name) not in (None, instance_type):
                    self._start_over(name)
                elif name not in fresh:
                    self._conversations.pop(name, None)  # gone from the patch: its file stays for its return
            self.instances = fresh
            moved = self.active not in fresh
            if moved:
                self.active = next(iter(fresh), "")
            active = self.active
        self._send("clear_instance_names_map", to_max=False)
        for name, instance_type in fresh.items():
            self._send("add_instance_names_map", name, instance_type, to_max=False)
        self._histories(list(fresh))
        if moved and active:
            self._send("set_active_instance", active, to_max=False)
        self._map_answered.set()

    # ── The instances, for Claude's tools (tools/instance_tools.py) ──────── #

    def ask_instances(self, timeout: float = INSTANCES_WAIT) -> bool:
        """Ask Max for its map (server get_instances); True if it answered in time."""
        self._map_answered.clear()
        if not self.bridge.send(line("server", "get_instances")):
            return False
        return self._map_answered.wait(timeout)

    def instance_map(self) -> Tuple[Dict[str, str], str]:
        with self._lock:
            return dict(self.instances), self.active

    def choose(self, name: str) -> str:
        """Make name the active instance, telling Max and the pages; "" if done, else why not."""
        with self._lock:
            known = name in self.instances
        if not known:
            return f"no instance {name or '(no name)'} in the patch"
        self._set_active(name, "", echo=True)
        return ""

    def _refusal(self, name: str) -> str:
        """Why a prompt to this instance cannot be answered now, or ""."""
        instance_type = self.instances.get(name)
        if instance_type is None:
            return f"no instance {name} in the map"
        if not self.playground:
            return "no playground: the patch sends set_playground <folder>"
        if self.make is None:
            return self.status.message or "no local model here: this Bach serves Claude through MCP"
        if not self.status.ready:
            return self.status.message or f"the model is not ready ({self.status.state})"
        return ""

    def _report(self, name: str, *said: Word) -> None:
        """server prompt <name> <stage> [detail]: what happens to the prompt, for Max."""
        self._send("server", "prompt", name, *said)

    def _stage(self, name: str, *said: Word) -> None:
        """A stage of the answer, said only when it changes."""
        if list(said) != self._said:
            self._said = list(said)
            self._report(name, *said)

    def _prompt(self, name: str, text: str, echo: bool) -> None:
        self._report(name, "received")
        if not text:
            self._send(name, "error", "the prompt is empty")
            self._report(name, "error", "the prompt is empty")
            return
        with self._lock:
            refusal = self._refusal(name)
            if not refusal:
                ahead = len(self._queue) + (1 if self._answering else 0)
                self._queue.append((name, text))
        if refusal:
            self._send(name, "error", refusal)
            self._report(name, "error", refusal)
            return
        self._send(name, "prompt", text, to_max=echo)
        if ahead:
            self._send(name, "queued")
            self._report(name, "queued", ahead)
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
            self._report(name, "stopped")

    def _new(self, name: str, echo: bool) -> None:
        with self._lock:
            busy = self._busy(name)
            if not busy:
                self._start_over(name)
        if busy:
            self._send(name, "error", "an answer is still being written: stop it first")
            return
        self._send(name, "new", to_max=echo)

    def _remove(self, name: str, echo: bool) -> None:
        """Forget the instance's conversation and its own choice of skills, in memory only."""
        self._stop(name)  # its answer, or its prompts waiting
        with self._lock:
            self._conversations.pop(name, None)
            self._began_with.pop(name, None)
            self.own.pop(name, None)
            self._built.pop(name, None)
        self._send(name, "remove", to_max=echo)
        self._send(name, "history", "[]", web_only=True)

    def _busy(self, name: str) -> bool:
        """Being answered, or waiting for its turn. Call with the lock held."""
        return self._answering == name or any(item[0] == name for item in self._queue)

    def _start_over(self, name: str) -> None:
        """The instance's next prompt starts a new conversation: the one in memory goes, and its
        file is kept beside it with the time (prompts/<name>-<date>-<time>.jsonl). Also when the
        instance changes type: a score instance's scores are no use to a generator, and Claude Code must
        not resume a session made with the other type's skill. While the instance is answered
        or waiting, only the conversation in memory goes: the answer still saves into its file.
        Call with the lock held."""
        self._conversations.pop(name, None)
        self._began_with.pop(name, None)
        path = self._history_file(name)
        if path and os.path.exists(path) and not self._busy(name):
            os.replace(path, path[:-len(".jsonl")] + time.strftime("-%Y%m%d-%H%M%S.jsonl"))

    # ── The tools' instance ────────────────────────────────────────────── #

    def target(self) -> Target:
        """The instance the tools serve: the one being answered, else the active one. A Claude
        written to directly (session.direct) always gets the active one: the prompt being
        answered is another conversation's."""
        with self._lock:
            if self._turn is not None and not direct():
                return self._turn
            if not self.playground:
                raise NoTarget("no playground: the patch sends set_playground <folder>")
            if not self.active:
                raise NoTarget("no instance is active: select one (set_active_instance <name>)")
            instance_type = self.instances.get(self.active)
            if instance_type is None:
                raise NoTarget(f"the active instance {self.active} is not in the map: choose one (set_active_instance <name>)")
            return Target(self.active, instance_type, self.playground)

    # ── Answering ──────────────────────────────────────────────────────── #

    def close(self) -> None:
        with self._wake:
            self._running = False
            self._wake.notify_all()
            conversation = self._conversations.get(self._answering)
        if conversation is not None:
            conversation.cancel()
        serve_targets(None)
        serve_instances(None)

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
                self._report(name, "error", f"{type(exc).__name__}: {exc}")
            finally:
                with self._lock:
                    self._answering = ""
                    self._turn = None

    def _answer(self, name: str, text: str) -> None:
        with self._lock:
            refusal = self._refusal(name)  # the map or the model may have changed while it waited
            if not refusal:
                fresh = self._skill_changed(name)
                target = Target(name, self.instances[name], self.playground)
                conversation = self._conversation(target)
                self._turn = target
        if not refusal and fresh:
            self._send(name, "new")
            self._send(name, "history", "[]", web_only=True)
        if refusal:
            self._send(name, "error", refusal)
            self._report(name, "error", refusal)
            return
        before = len(conversation.history)
        started, tokens, answer, finish = time.time(), 0, [], "stop"
        self._said = []
        self._send(name, "thinking", web_only=True)  # the page's busy sign; Max hears the stages
        self._stage(name, "starting")
        self._report(name, "skills_size", estimate_tokens(conversation.skill))
        events = conversation.send(text)
        try:
            for event in events:
                if self._stopping.is_set():
                    break
                kind = event["type"]
                if kind == "stage":
                    self._stage(name, event["stage"], *event.get("detail", []))
                elif kind == "text":
                    answer.append(event["text"])
                    self._stage(name, "writing")
                    self._send(name, "delta", event["text"], web_only=True)
                elif kind == "thinking":
                    self._stage(name, "thinking")
                    self._send(name, "reasoning", event["text"], web_only=True)
                elif kind == "calling":
                    self._stage(name, "calling", event["name"])
                elif kind == "tool_call":
                    self._stage(name, "running", event["name"])
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
                    self._report(name, "error", event["message"])
                elif kind == "done":
                    finish = event["finish"]
        finally:
            events.close()
            self._save(conversation, target, before, text)
        if self._stopping.is_set():
            self._send(name, "stopped")
            self._report(name, "stopped")
            return
        cut = {"length": "the answer reached the reply limit ([generation] max_tokens)",
               "rounds": "stopped: more rounds of tools than [chat] max_tool_rounds"}.get(finish)
        if cut:
            self._send(name, "error", cut)
            self._report(name, "error", cut)
        whole, ms = "".join(answer).strip(), int((time.time() - started) * 1000)
        if whole:
            self._send(name, "answer", whole)
        self._send(name, "done", tokens, ms)
        self._report(name, "done", tokens, ms)
        self.bridge.send(line("server", "answer", name, whole))
        self.bridge.send(line("server", "answer", "tokens", tokens))
        self.bridge.send(line("server", "answer", "time", ms))

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

    def _histories(self, names: List[str]) -> None:
        """Send the pages each named instance's saved conversation, from the playground as it
        is now; an empty one clears the page's. An instance being answered, or waiting, is left
        alone: the page is drawing that answer."""
        with self._lock:
            busy = {self._answering, *(name for name, _ in self._queue)}
            shown = [(name, self._saved(name)[-HISTORY_SHOWN:]) for name in names if name not in busy]
        for name, saved in shown:
            self._send(name, "history", json.dumps(saved, ensure_ascii=False), web_only=True)

    def _conversation(self, target: Target) -> Conversation:
        """The instance's conversation: in memory, else the saved one, else a new one."""
        conversation = self._conversations.get(target.name)
        if conversation is None:
            assert self.make is not None
            conversation = self.make(target.type)
            skill = self._build_skill(target.name, warn=False)
            if skill:
                conversation.skill = skill  # read by instance_skill at each request (engine, headless)
            self._began_with[target.name] = self._selection(target.name)
            saved = self._saved(target.name)
            conversation.history = [{k: v for k, v in m.items() if k not in ("prompt", "session")} for m in saved]
            conversation.session = next((m["session"] for m in reversed(saved) if m.get("session")), "")  # Claude Code's
            if getattr(conversation, "docs", None) is not None:  # the docs it already has are not added again
                conversation.seen_docs = conversation.docs.seen_in(
                    m.get("prompt", "") for m in saved if m.get("role") == "user")
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


__all__ = ["Hub", "Message", "INSTANCE_COMMANDS", "RESERVED"]
