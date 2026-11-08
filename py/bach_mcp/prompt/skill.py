"""
skill.py
--------
The skill: the text that tells the model how to compose with Bach. It is the
system prompt of the local model and the MCP instructions Claude reads.

The file marks its parts with lines of their own:
    <!-- algo -->    what follows is for /algo only
    <!-- score -->   for /score only
    <!-- both -->    for both (the default at the top of the file)
A mode gets its own part and the shared one (see modes.py); without a mode,
the whole file is used. The markers themselves never reach the model.

A second pair says how much the model says after it sends an algorithm,
chosen by [algo] verbose in bachmcp.toml (with_verbosity, applied first):
    <!-- verbose -->   what follows is kept when verbose = true
    <!-- quiet -->     kept when verbose = false
    <!-- /verbose -->  back to what is always kept
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

SKILL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BACH_SKILL.md")

_MARKER = re.compile(r"^<!--\s*(algo|score|both)\s*-->[ \t]*\n?", re.M)


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


def skill_for(text: str, mode: Optional[str] = None, verbose: bool = True) -> str:
    """The parts of a skill text for this mode (None: all of it), markers removed.
    Verbosity markers still in it are resolved with `verbose` (Config.skill_source
    resolves them first with [algo] verbose, so then there are none left)."""
    text = with_verbosity(text, verbose)
    out: List[str] = []
    current = "both"
    pos = 0
    for m in _MARKER.finditer(text):
        if current == "both" or mode is None or current == mode:
            out.append(text[pos:m.start()])
        current, pos = m.group(1), m.end()
    if current == "both" or mode is None or current == mode:
        out.append(text[pos:])
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip() + "\n"


def load_skill(mode: Optional[str] = None, raw: bool = False, path: str = SKILL_PATH,
               verbose: bool = True) -> str:
    """The skill for a mode ("score" or "algo"), all of it (None), or the file as it is (raw)."""
    text = read_skill(path)
    return text if raw else skill_for(text, mode, verbose)


__all__ = ["SKILL_PATH", "read_skill", "with_verbosity", "skill_for", "load_skill"]
