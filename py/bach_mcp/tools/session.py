"""
session.py
----------
What the tools are serving: which conversation, and which instance.

Conversation. read_score remembers its last answer, to say "unchanged" instead
of repeating 14,000 tokens. A chat that has not seen that answer must not get
"unchanged": every conversation has a number (new_conversation), and the one
being answered says so (use_conversation) before it calls a tool.

Instance. Every product carries the name of the instance it is for, and the
instance's type decides what the tools accept (a score instance writes notes, a
generator or a transformer an algorithm, a synth or an fx gen~ code, a process Python for offline audio). The tools never get a name from the
model: they ask target(), which the hub (chat/hub.py) answers, with the
instance of the prompt being answered, else the active one. A Claude written
to directly chooses the active one itself (instances(): instance_tools.py), and
its calls are always for the active one, also while another instance's prompt is
being answered: the app it reaches marks them (calling_directly, registry.py).

    Target(name, type, playground)
      .algorithms .scores .prompts .gen .processes      the playground's folders
      .algorithm_file .roll_file .gen_file .process_file
                                             <name>.js, <name>.json, <name>.genexpr, <name>.py in them
"""

from __future__ import annotations

import contextlib
import os
import threading
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, Optional, Protocol, Tuple

TYPES = ("generator", "transformer", "selector", "score", "synth", "fx", "buffer")

_lock = threading.Lock()
_number = 0
_current = 0


def new_conversation() -> int:
    """A number for a new conversation, which becomes the current one."""
    global _number, _current
    with _lock:
        _number += 1
        _current = _number
        return _number


def use_conversation(number: int) -> None:
    """The conversation the next tool calls are for."""
    global _current
    _current = number


def conversation() -> int:
    return _current


_caller = threading.local()


@contextlib.contextmanager
def calling_directly() -> Iterator[None]:
    """While a tool runs for a Claude written to directly (/mcp), on this thread: its instance
    is the active one, never the one whose prompt is being answered."""
    _caller.direct = True
    try:
        yield
    finally:
        _caller.direct = False


def direct() -> bool:
    """Whether the tool running on this thread was called by a Claude written to directly."""
    return getattr(_caller, "direct", False)


class NoTarget(Exception):
    """The tools cannot tell which instance they serve; the message says what to do."""


@dataclass(frozen=True)
class Target:
    name: str        # the instance, as the patch names it
    type: str        # one of TYPES
    playground: str  # the playground folder (absolute)

    @property
    def algorithms(self) -> str:
        return os.path.join(self.playground, "algorithms")

    @property
    def scores(self) -> str:
        return os.path.join(self.playground, "scores")

    @property
    def prompts(self) -> str:
        return os.path.join(self.playground, "prompts")

    @property
    def gen(self) -> str:
        return os.path.join(self.playground, "gen")

    @property
    def gen_file(self) -> str:
        return os.path.join(self.gen, f"{self.name}.genexpr")

    @property
    def processes(self) -> str:
        return os.path.join(self.playground, "processes")

    @property
    def process_file(self) -> str:
        return os.path.join(self.processes, f"{self.name}.py")

    @property
    def algorithm_file(self) -> str:
        return os.path.join(self.algorithms, f"{self.name}.js")

    @property
    def roll_file(self) -> str:
        return os.path.join(self.scores, f"{self.name}.json")


def _no_hub() -> Target:
    raise NoTarget("no instance: Bach has no playground or instances yet (the patch sends them)")


_provider: Callable[[], Target] = _no_hub


def serve_targets(provider: Optional[Callable[[], Target]]) -> None:
    """Who answers target(): a function that returns the Target or raises NoTarget (None: nobody)."""
    global _provider
    _provider = provider or _no_hub


def target() -> Target:
    """The instance the tools serve now. Raises NoTarget with what to do."""
    return _provider()


# The instances themselves, for a Claude written to directly: it has no prompt line, so it
# lists them and chooses the active one (instance_tools.py). The hub answers.

class Instances(Protocol):
    def ask_instances(self) -> bool: ...                      # asks Max; True if it answered
    def instance_map(self) -> Tuple[Dict[str, str], str]: ...  # (name -> type, the active one)
    def choose(self, name: str) -> str: ...                    # "" when done, else why not


_instances: Optional[Instances] = None


def serve_instances(manager: Optional[Instances]) -> None:
    """Who lists the instances and sets the active one (None: nobody)."""
    global _instances
    _instances = manager


def instances() -> Instances:
    """The hub's instances. Raises NoTarget when there is no hub (nothing from the patch)."""
    if _instances is None:
        raise NoTarget("no instances: Bach has no hub here (the patch's bachmcp.server is not running)")
    return _instances


__all__ = ["TYPES", "Target", "NoTarget", "serve_targets", "target", "Instances", "serve_instances",
           "instances", "new_conversation", "use_conversation", "conversation", "calling_directly", "direct"]
