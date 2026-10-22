"""
session.py
----------
Which conversation the chat is in. The model keeps nothing between chats (the web
chat sends the whole history every time), but the tools do: read_score remembers
its last answer. The gateway calls new_conversation() when a chat starts, and the
tools forget what belongs to the one before.
"""

from __future__ import annotations

import threading
from typing import Any, List

_lock = threading.Lock()
_number = 0


def new_conversation() -> int:
    global _number
    with _lock:
        _number += 1
        return _number


def conversation() -> int:
    return _number


def starts_conversation(messages: Any) -> bool:
    """A request is the first of a conversation when the model has not answered yet."""
    if not isinstance(messages, list) or not messages:
        return False
    roles: List[str] = [m.get("role", "") for m in messages if isinstance(m, dict)]
    return bool(roles) and roles[-1] == "user" and not any(r in ("assistant", "tool") for r in roles)


__all__ = ["new_conversation", "conversation", "starts_conversation"]
