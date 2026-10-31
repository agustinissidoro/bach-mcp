"""
session.py
----------
What the tools are serving: which conversation, and which instance.

Conversation. read_score remembers its last answer, to say "unchanged" instead
of repeating 14,000 tokens. A chat that has not seen that answer must not get
"unchanged": every conversation has a number (new_conversation), and the one
being answered says so (use_conversation) before it calls a tool.

Instance. Every product carries the name of the instance it is for, and the
instance's type decides what the tools accept (a writer writes notes, a
generator or a transformer an algorithm). The tools never get a name from the
model: they ask target(), which the hub (chat/hub.py) answers, with the
instance of the prompt being answered, else the active one.

    Target(name, kind, playground)
      .algorithms .scores .prompts           the playground's folders
      .algorithm_file .roll_file             <name>.js, <name>.json in them
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Callable, Optional

KINDS = ("generator", "transformer", "selector", "writer")

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


class NoTarget(Exception):
    """The tools cannot tell which instance they serve; the message says what to do."""


@dataclass(frozen=True)
class Target:
    name: str        # the instance, as the patch names it
    kind: str        # one of KINDS
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


__all__ = ["KINDS", "Target", "NoTarget", "serve_targets", "target",
           "new_conversation", "use_conversation", "conversation"]
