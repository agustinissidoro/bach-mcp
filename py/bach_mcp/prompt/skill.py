"""
skill.py
--------
The skill: the text that tells the model how to compose with Bach. It is the
system prompt of the local model and the MCP instructions Claude reads.

The file marks its parts with lines of their own, which open and close:
    <!-- score --> ... <!-- /score -->        for /score only (bachmcp.score)
    <!-- algo --> ... <!-- /algo -->          for /algo only (bachmcp.algorithm, any type)
    <!-- transformer selector --> ... <!-- /transformer selector -->
                                              for these types of instance only (MODE_TYPES)
    <!-- gen --> ... <!-- /gen -->            for sound only (a synth or an fx instance: GenExpr
                                              for gen~), with <!-- synth --> and <!-- fx --> inside
What is outside every part is for everyone. A closing marker goes back to what
was on before its part: a part may sit inside another (a transformer part inside
an algo part closes back to algo). A part opened inside another is for its own
words only, not for what the two share. A closing marker closes the last part
opened, whatever words it repeats; one with nothing open is ignored. An older
style is still read: a marker that is never closed lasts until the next one, and
<!-- both --> closes every part.
A mode gets its own part and the shared one (see modes.py), and an instance
only what its type reads: a generator never reads how a transformer works. A
chat in a mode with no instance (a /algo prefix) gets every type's part; without
a mode, the whole file is used. The markers themselves never reach the model.

A second pair says how much the model says after it sends an algorithm,
chosen by [algo] verbose in bachmcp.toml (with_verbosity, applied first):
    <!-- verbose -->   what follows is kept when verbose = true
    <!-- quiet -->     kept when verbose = false
    <!-- /verbose -->  back to what is always kept

The symbolic skill (BACH_SKILL.md: the score and its algorithms) and the sound skill
(GEN_SKILL.md: gen~) are two files. Each is whole inside its own parts, so an instance
never reads the other's. A skill text with no part for gen gets the built-in sound skill
after it (with_gen): a synth always has something to read, whatever was chosen for the score.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Set

SKILL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BACH_SKILL.md")
GEN_SKILL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GEN_SKILL.md")
# An extra skill, chosen from the playground (skills.py): markers with a role, for bach.quantize.
QUANTIZER_SKILL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "QUANTIZER_SKILL.md")

# The types of instance (tools/session.py TYPES) that work in each mode.
MODE_TYPES = {"algo": ("generator", "transformer", "selector"), "score": ("score",), "gen": ("synth", "fx")}
_TYPES = [instance_type for types in MODE_TYPES.values() for instance_type in types]
_WORD = "|".join(["both", *MODE_TYPES, *_TYPES])
_MARKER = re.compile(rf"^<!--\s*(/?)\s*((?:{_WORD})(?:\s+(?:{_WORD}))*)\s*-->[ \t]*\n?", re.M)


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
        out |= set(_TYPES) if word == "both" else set(MODE_TYPES.get(word, (word,)))
    return out


def skill_for(text: str, mode: Optional[str] = None, verbose: bool = True, instance_type: Optional[str] = None) -> str:
    """The parts of a skill text for this mode and type of instance (None: every type of the
    mode; no mode: all of it), markers removed. Verbosity markers still in it are resolved with
    `verbose` (Config.skill_source resolves them first with [algo] verbose, so then there are none left)."""
    text = with_verbosity(text, verbose)
    wanted = {instance_type} if instance_type else set(MODE_TYPES[mode]) if mode else set(_TYPES)
    out: List[str] = []
    opened: List[Set[str]] = []  # the parts open, innermost last
    pos = 0
    for m in _MARKER.finditer(text):
        if (opened[-1] if opened else set(_TYPES)) & wanted:
            out.append(text[pos:m.start()])
        closing, marker = m.group(1), m.group(2)
        if closing:
            if opened:
                opened.pop()
        elif marker.split() == ["both"]:
            opened.clear()
        else:
            opened.append(_readers(marker))
        pos = m.end()
    if (opened[-1] if opened else set(_TYPES)) & wanted:
        out.append(text[pos:])
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip() + "\n"


def closed(text: str) -> str:
    """The text with every part it leaves open closed at its end (the markers it would
    need: <!-- /score -->, <!-- /verbose --> ...), so that what follows is for everyone."""
    opened: List[str] = []
    for m in _MARKER.finditer(text):
        closing, marker = m.group(1), m.group(2)
        if closing:
            if opened:
                opened.pop()
        elif marker.split() == ["both"]:
            opened.clear()
        else:
            opened.append(marker)
    verbosity = [m.group(1) for m in _VERBOSITY.finditer(text)]
    tail = ["<!-- /verbose -->"] if verbosity and verbosity[-1] != "/verbose" else []
    tail += [f"<!-- /{marker} -->" for marker in reversed(opened)]
    return text.rstrip("\n") + "\n" + "".join(t + "\n" for t in tail)


def with_gen(text: str, verbose: bool = True) -> str:
    """The text, and after it the built-in sound skill (GEN_SKILL.md, in the wording `verbose`
    chooses) when the text has no part for gen: a synth or an fx then reads that one."""
    gen = set(MODE_TYPES["gen"])
    if any(not m.group(1) and _readers(m.group(2)) & gen and m.group(2).split() != ["both"] for m in _MARKER.finditer(text)):
        return text
    return closed(text) + "\n" + with_verbosity(read_skill(GEN_SKILL_PATH), verbose)


def load_skill(mode: Optional[str] = None, raw: bool = False, path: str = SKILL_PATH,
               verbose: bool = True) -> str:
    """The skill for a mode ("score" or "algo"), all of it (None), or the file as it is (raw)."""
    text = read_skill(path)
    return text if raw else skill_for(text, mode, verbose)


__all__ = ["SKILL_PATH", "GEN_SKILL_PATH", "QUANTIZER_SKILL_PATH", "MODE_TYPES", "read_skill", "with_verbosity", "skill_for", "closed",
           "with_gen", "load_skill"]
