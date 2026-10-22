"""
pitch_tools.py
--------------
The pitch functions of pitch.py as MCP tools, for /score mode: the model does
the musical reasoning and asks these for every number.

All of them answer the same way, so that the answer can be copied as it is:
one JSON value in midicents, in the shape of the input (a list stays a list,
a list of chords stays a list of chords), whole numbers without decimals, and
nothing else. mc2p answers names the same way. A mistake answers
"ERROR: ...", saying what to fix.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict

from mcp.server.fastmcp import FastMCP

from . import pitch
from .modes import PITCH_TOOLS
from .pitch import PitchError, tidy

Pitches = Any  # names, numbers, lists of any depth or text: pitch.read_pitches reads them all


def answer(value: Any) -> str:
    """The one form every pitch tool answers in."""
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def _run(fn: Callable[..., Any], *args: Any, names: bool = False) -> str:
    try:
        result = fn(*args)
    except PitchError as exc:
        return f"ERROR: {str(exc).rstrip('.')}. Fix this and call the tool again."
    return answer(result if names else tidy(result))


def p2mc(pitches: Pitches) -> str:
    """Pitch names to midicents, for every pitch you know by name. One name or a list, nested as you
    like. Flats b, sharps #; a microtone adds cents: "E4-14". C4 = middle C = 6000.
    Example: p2mc(["Db4", "F4", "Ab4"]) -> [6100, 6500, 6800]"""
    return _run(pitch.p2mc, pitches)


def mc2p(midicents: Pitches) -> str:
    """Midicents to names, to say what pitches are.
    Example: mc2p([6100, 6386.31]) -> ["C#4", "E4-13.69"]"""
    return _run(pitch.mc2p, midicents, names=True)


def get_midicents(values: Pitches, unit: str = "ratio", reference: Any = "C4") -> str:
    """Exact midicents of tuned pitches. unit "ratio": ratios ("5/4", 1.5) above `reference`;
    "harmonic": harmonic numbers of the fundamental `reference`; "hz": frequencies.
    Example: get_midicents([1, 2, 3, 4, 5], "harmonic", "C2") -> [3600, 4800, 5501.96, 6000, 6386.31]"""
    return _run(pitch.get_midicents, values, unit, reference)


def transpose(pitches: Pitches, cents: Any) -> str:
    """Move pitches by `cents` (negative = down). A compound interval as its parts, which the tool adds:
    an octave and a fourth down is [-1200, -500].
    Example: transpose([6200, 6500, 6900], [-1200, -500]) -> [4500, 4800, 5200]"""
    return _run(pitch.transpose, pitches, cents)


def reverse(pitches: Pitches) -> str:
    """Retrograde: the list in reverse order (a list of chords: the chords, not their notes).
    Example: reverse([6000, 6400, 6700, 7100]) -> [7100, 6700, 6400, 6000]"""
    return _run(pitch.reverse, pitches)


def mirror(pitches: Pitches, axis: Any = "") -> str:
    """Inversion around `axis` (a pitch; without it, the first pitch).
    Example: mirror([6000, 6400, 6700], 6000) -> [6000, 5600, 5300]"""
    return _run(pitch.mirror, pitches, axis)


def force_scale(pitches: Pitches, scale: Any, root: Any = "C") -> str:
    """Every pitch to the nearest note of a scale (a tie: the lower). scale: a get_scale name with its
    `root`, or the scale's own pitches ("C D E G A").
    Example: force_scale([6100, 6300, 6600], "major", "C") -> [6000, 6200, 6500]"""
    return _run(pitch.force_scale, pitches, scale, root)


def get_chord(root: Pitches, chord: str, inversion: int = 0) -> str:
    """A chord in close position from `root` up (a list of roots: the chord on each); `inversion` n
    moves its n lowest notes an octave up. chord: a name ("dominant7", "half_diminished7", "quartal4",
    "harmonic7" ...) or a symbol ("m7", "maj7", "7b9"); "list" gives every name.
    Example: get_chord("Db4", "major") -> [6100, 6500, 6800]"""
    if str(chord).strip().lower() == "list":
        return pitch.chord_names()
    return _run(pitch.get_chord, root, chord, inversion)


def get_scale(root: Any, scale: str, octaves: int = 1, direction: str = "up") -> str:
    """A scale from `root` up `octaves` octaves to the root above; direction "up", "down" or "updown".
    scale: a mode, "harmonic_minor", "whole_tone", "octatonic_hw", "blues", a maqam ("rast"), a tuning
    ("just_major", "edo19") ...; "list" gives every name.
    Example: get_scale("D4", "dorian") -> [6200, 6400, 6500, 6700, 6900, 7100, 7200, 7400]"""
    if str(scale).strip().lower() == "list":
        return pitch.scale_names()
    return _run(pitch.get_scale, root, scale, octaves, direction)


FUNCTIONS: Dict[str, Callable[..., str]] = {fn.__name__: fn for fn in
                                            (p2mc, mc2p, get_midicents, transpose, reverse, mirror, force_scale,
                                             get_chord, get_scale)}


def call_pitch_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Run a pitch tool by name, as the MCP server would (used by the evaluation)."""
    try:
        return FUNCTIONS[name](**arguments)
    except TypeError as exc:
        return f"ERROR: {exc}. Fix this and call the tool again."


def register_pitch_tools(mcp: FastMCP) -> None:
    for fn in FUNCTIONS.values():
        mcp.tool()(fn)


__all__ = ["PITCH_TOOLS", "register_pitch_tools", "call_pitch_tool", "answer"]
