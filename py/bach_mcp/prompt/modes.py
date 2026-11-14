"""
modes.py
--------
Two modes, chosen by the user with a prefix at the start of a message:

    /score   the model writes the notes, as JSON (write_score)        default
    /algo    the model writes the algorithm that generates them (send_algorithm)
    /gen     the model writes sound: GenExpr code for gen~ (send_gen), for a synth or an fx
    /buffer  the model writes offline audio processing in Python (send_buffer_process), run by the hub
             on the samples of a bachmcp.shmbuffer~ (no skill of its own yet: the tool says how)

A mode lasts until the other prefix appears. Each mode gets only its own part
of the skill (skill.py) and only its own tools (read_score is in both), so the model reads less and
nothing that does not apply. A message that is only a prefix switches the
mode without asking the model anything.

The local chat applies the mode to every request (chat/engine.py). Claude gets
the whole skill and every tool, and the modes as two prompts (claude.py).

A conversation with an instance of the patch has no prefixes: the instance's
type fixes the mode (TYPE_MODE), it reads only the parts of the skill for its
type (skill.py), and a line added to the skill says which answer this
instance takes (TYPE_NOTE).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ..tools.algo_tools import ALGO_TOOLS
from ..tools.gen_tools import GEN_TOOLS
from ..tools.pitch_tools import PITCH_TOOLS
from ..tools.buffer_process_tools import BUFFER_PROCESS_TOOLS
from ..tools.score_tools import SCORE_TOOLS
from .skill import MODE_TYPES, skill_for

MODES = ("score", "algo", "gen", "buffer")
DEFAULT_MODE = "score"

MODE_TOOLS = {
    "score": SCORE_TOOLS + PITCH_TOOLS,  # the notes, with exact pitch arithmetic
    "algo": ALGO_TOOLS + ("read_score",),  # the algorithm, and a look at the score in the roll
    "gen": GEN_TOOLS,  # sound: the gen~ code alone, nothing of the score
    "buffer": BUFFER_PROCESS_TOOLS,  # offline audio: the Python file alone
}

TYPE_MODE = {instance_type: mode for mode, types in MODE_TYPES.items() for instance_type in types}  # generator -> algo ...

TYPE_NOTE = {
    "generator": "You are writing for a generator: it makes music from nothing. Write "
                 "`function produce(p) { ... }` and send it with send_algorithm.",
    "transformer": "You are writing for a transformer: it changes the score already in its roll. Write "
                   "`function transform(source, p) { ... }` and send it with send_algorithm.",
    "selector": "You are writing for a selector: it selects notes of the score already in its roll. Write "
                "`function select(source, p) { ... }` returning the notes it picks, and send it with send_algorithm.",
    "score": "You are writing for a score instance: write the notes themselves with write_score.",
    "synth": "You are writing for a synth: it makes sound from nothing. Write the GenExpr code of its gen~ "
             "and send it with send_gen.",
    "fx": "You are writing for an fx: it processes the sound that comes into its inlets. Write the GenExpr "
          "code of its gen~ and send it with send_gen.",
    "buffer": "You are writing for a buffer instance: it processes, offline, the sound in its memory in Max. "
               "Write a Python file that defines `process(x, sr, p)` and send it with send_buffer_process.",
}

_PREFIX = re.compile(r"^\s*/(algo|score|gen|buffer)\b[ \t]*\n?", re.I)


def split_prefix(text: str) -> Tuple[Optional[str], str]:
    """'/algo a canon' -> ('algo', 'a canon'); text without a prefix -> (None, text).
    A message that is only the prefix keeps its text: ('algo', '/algo')."""
    m = _PREFIX.match(text or "")
    if not m:
        return None, text
    rest = text[m.end():]
    return m.group(1).lower(), rest if rest.strip() else text


def instance_skill(skill: str, mode: str, instance_type: Optional[str] = None) -> str:
    """The system prompt for one conversation: the skill's part for this mode and, for an
    instance, the line on what it takes. The one place it is made: the local model
    (chat/engine.py) and the Claude Code Bach starts (chat/headless.py) read the same text."""
    text = skill_for(skill, mode, instance_type=instance_type)
    return f"{text}\n{TYPE_NOTE[instance_type]}\n" if instance_type else text


def tools_for(tools: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    """The tools of this mode, from tools in the OpenAI format."""
    return [t for t in tools if t["function"]["name"] in MODE_TOOLS[mode]]


__all__ = ["MODES", "DEFAULT_MODE", "MODE_TOOLS", "TYPE_MODE", "TYPE_NOTE", "instance_skill", "split_prefix", "tools_for"]
