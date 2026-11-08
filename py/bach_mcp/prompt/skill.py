"""
skill.py
--------
The skill: the text that tells the model how to compose with Bach. It is the
system prompt of the local model and the MCP instructions Claude reads.

The file marks its parts with lines of their own:
    <!-- algo -->    what follows is for /algo only
    <!-- score -->   for /score only
    <!-- both -->    for both (the default at the top of the file)
    <!-- transformer selector -->   for these types of instance only (MODE_KINDS)
A mode gets its own part and the shared one (see modes.py), and an instance
only what its type reads: a generator never reads how a transformer works. A
chat in a mode with no instance (a /algo prefix) gets every type's part; without
a mode, the whole file is used. The markers themselves never reach the model.

A second pair says how much the model says after it sends an algorithm,
chosen by [algo] verbose in bachmcp.toml (with_verbosity, applied first):
    <!-- verbose -->   what follows is kept when verbose = true
    <!-- quiet -->     kept when verbose = false
    <!-- /verbose -->  back to what is always kept
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Set

SKILL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BACH_SKILL.md")

# The types of instance (tools/session.py KINDS) that work in each mode.
MODE_KINDS = {"algo": ("generator", "transformer", "selector"), "score": ("writer",)}
_KINDS = [kind for kinds in MODE_KINDS.values() for kind in kinds]
_WORD = "|".join(["both", *MODE_KINDS, *_KINDS])
_MARKER = re.compile(rf"^<!--\s*((?:{_WORD})(?:\s+(?:{_WORD}))*)\s*-->[ \t]*\n?", re.M)


def read_skill(path: str = SKILL_PATH) -> str:
    """The skill file as it is, with its mode markers."""
    with open(path, encoding="utf-8") as f:
        return f.read()


_VERBOSITY = re.compile(r"^<!--\s*(verbose|quiet|/verbose)\s*-->[ \t]*\n?", re.M)


def with_verbosity(text: str, verbose: bool) -> str:
    """The text with only the verbose (or only the quiet) wording, those markers removed."""
    out: List[str] = []
    current, pos = "", 0
    keep = "verbose" if verbose else "quiet"
    for m in _VERBOSITY.finditer(text):
        if current in ("", keep):
            out.append(text[pos:m.start()])
        current = "" if m.group(1) == "/verbose" else m.group(1)
        pos = m.end()
    if current in ("", keep):
        out.append(text[pos:])
    return "".join(out)


def _readers(marker: str) -> Set[str]:
    """The types of instance a marker's part is for."""
    out: Set[str] = set()
    for word in marker.split():
        out |= set(_KINDS) if word == "both" else set(MODE_KINDS.get(word, (word,)))
    return out


def skill_for(text: str, mode: Optional[str] = None, verbose: bool = True, kind: Optional[str] = None) -> str:
    """The parts of a skill text for this mode and type of instance (None: every type of the
    mode; no mode: all of it), markers removed. Verbosity markers still in it are resolved with
    `verbose` (Config.skill_source resolves them first with [algo] verbose, so then there are none left)."""
    text = with_verbosity(text, verbose)
    wanted = {kind} if kind else set(MODE_KINDS[mode]) if mode else set(_KINDS)
    out: List[str] = []
    readers, pos = set(_KINDS), 0
    for m in _MARKER.finditer(text):
        if readers & wanted:
            out.append(text[pos:m.start()])
        readers, pos = _readers(m.group(1)), m.end()
    if readers & wanted:
        out.append(text[pos:])
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip() + "\n"


def load_skill(mode: Optional[str] = None, raw: bool = False, path: str = SKILL_PATH,
               verbose: bool = True) -> str:
    """The skill for a mode ("score" or "algo"), all of it (None), or the file as it is (raw)."""
    text = read_skill(path)
    return text if raw else skill_for(text, mode, verbose)


__all__ = ["SKILL_PATH", "MODE_KINDS", "read_skill", "with_verbosity", "skill_for", "load_skill"]
