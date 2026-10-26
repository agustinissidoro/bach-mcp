"""
modes.py
--------
Two modes, chosen by the user with a prefix at the start of a message:

    /score   the model writes the notes, as JSON (write_score)        default
    /algo    the model writes the algorithm that generates them (send_algorithm)

A mode lasts until the other prefix appears. Each mode gets only its own part
of the skill (skill.py) and only its own tools, so the model reads less and
nothing that does not apply. A message that is only a prefix switches the
mode without asking the model anything.

The local chat applies the mode to every request (chat/engine.py). Claude gets
the whole skill and every tool, and the modes as two prompts (claude.py).

A conversation with an instance of the patch has no prefixes: the instance's
type fixes the mode (KIND_MODE), and a line added to the skill says which kind
of answer this instance takes (KIND_NOTE).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ..tools.algo_tools import ALGO_TOOLS
from ..tools.pitch_tools import PITCH_TOOLS
from ..tools.score_tools import SCORE_TOOLS

MODES = ("score", "algo")
DEFAULT_MODE = "score"

MODE_TOOLS = {
    "score": SCORE_TOOLS + PITCH_TOOLS,  # the notes, with exact pitch arithmetic
    "algo": ALGO_TOOLS,
}

KIND_MODE = {
    "generator": "algo",
    "transformer": "algo",
    "selector": "algo",
    "writer": "score",
}

KIND_NOTE = {
    "generator": "You are writing for a generator: it makes music from nothing. Write a producer, "
                 "`function produce(p) { ... }`, and send it with send_algorithm.",
    "transformer": "You are writing for a transformer: it changes the score already in its roll. Write "
                   "`function transform(source, p) { ... }` and send it with send_algorithm.",
    "selector": "You are writing for a selector: it selects notes of the score already in its roll.",
    "writer": "You are writing for a writer: write the notes themselves with write_score.",
}

_PREFIX = re.compile(r"^\s*/(algo|score)\b[ \t]*\n?", re.I)


def split_prefix(text: str) -> Tuple[Optional[str], str]:
    """'/algo a canon' -> ('algo', 'a canon'); text without a prefix -> (None, text).
    A message that is only the prefix keeps its text: ('algo', '/algo')."""
    m = _PREFIX.match(text or "")
    if not m:
        return None, text
    rest = text[m.end():]
    return m.group(1).lower(), rest if rest.strip() else text


def tools_for(tools: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    """The tools of this mode, from tools in the OpenAI format."""
    return [t for t in tools if t["function"]["name"] in MODE_TOOLS[mode]]


__all__ = ["MODES", "DEFAULT_MODE", "MODE_TOOLS", "KIND_MODE", "KIND_NOTE", "split_prefix", "tools_for"]
