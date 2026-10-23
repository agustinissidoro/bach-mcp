"""
compose.py
----------
Runs a short, restricted Python program that generates a score.

This is the algorithmic-composition path: the model states an idea as code
(a process, a rule, a transformation) and this module turns the run into the
same JSON score that `translate.normalize_score` accepts. The model never
writes out the notes one by one, and never computes pitches by hand — the
helpers below are the ground truth for scales, chords and transformations.

The program is restricted, not sandboxed against a determined attacker: no
imports, no attribute access to underscore names, a whitelisted set of
builtins, and a step limit. It is meant for a model running on the user's own
machine.
"""

from __future__ import annotations

import ast
import builtins
import math
import random
import re
import sys
from typing import Any, Callable, Dict, List, Optional

from .translate import ScoreError

_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NAME = re.compile(r"^([A-Ga-g])([#b]*)(-?\d+)$")


def pitch_to_cents(pitch: Any) -> float:
    """Pitch name ("C4" = middle C) or MIDI number -> midicents."""
    if isinstance(pitch, (int, float)) and not isinstance(pitch, bool):
        return float(pitch) * 100.0
    m = _NAME.match(str(pitch).strip())
    if not m:
        raise ScoreError(f"invalid pitch {pitch!r}: use a name like \"C4\" or a MIDI number like 60")
    letter, accs, octave = m.groups()
    return (int(octave) + 1) * 1200.0 + (_PC[letter.upper()] + accs.count("#") - accs.count("b")) * 100.0

MAX_STEPS = 5_000_000
MAX_EVENTS = 20000

MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "ionian": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10], "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11], "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11], "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9], "minor_pentatonic": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10], "whole_tone": [0, 2, 4, 6, 8, 10],
    "octatonic": [0, 2, 3, 5, 6, 8, 9, 11], "chromatic": list(range(12)),
}

CHORDS = {
    "maj": [0, 4, 7], "min": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    "sus2": [0, 2, 7], "sus4": [0, 5, 7],
    "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "7": [0, 4, 7, 10],
    "dim7": [0, 3, 6, 9], "m7b5": [0, 3, 6, 10], "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14], "9": [0, 4, 7, 10, 14],
}

HELP = (
    "note(pitch, dur=1, t=None, vel=None, voice=1, dyn=None, art=None, head=None, gliss=None), "
    "rest(dur, voice=1), voice(n, name, clef), now(voice=1), midi(name), "
    "scale(root, mode, n=8), chord(root, kind), transpose(ps, semitones), invert(ps, axis=None), "
    "retrograde(seq), rotate(seq, n), euclid(hits, steps), rnd (seeded random), "
    "sin cos pi floor ceil sqrt log exp gcd, and plain Python (loops, lists, functions)"
)


def midi(pitch: Any) -> float:
    """Pitch name or number -> MIDI number (60 = C4)."""
    value = pitch_to_cents(pitch) / 100.0
    return int(value) if value == int(value) else value


def scale(root: Any = "C4", mode: str = "major", n: int = 8) -> List[float]:
    """n ascending notes of a scale starting at root, as MIDI numbers."""
    steps = MODES.get(str(mode).lower().replace(" ", "_"))
    if steps is None:
        raise ScoreError(f"unknown mode {mode!r}. Available: {' '.join(MODES)}")
    base = midi(root)
    return [base + steps[i % len(steps)] + 12 * (i // len(steps)) for i in range(int(n))]


def chord(root: Any = "C4", kind: str = "maj") -> List[float]:
    """Notes of a chord built on root, as MIDI numbers."""
    key = str(kind).lower().replace("major", "maj").replace("minor", "min")
    key = {"m": "min", "m7": "min7", "": "maj", "dom7": "7", "m9": "min9"}.get(key, key)
    steps = CHORDS.get(key)
    if steps is None:
        raise ScoreError(f"unknown chord {kind!r}. Available: {' '.join(CHORDS)}")
    base = midi(root)
    return [base + s for s in steps]


def transpose(pitches: Any, semitones: float) -> Any:
    if isinstance(pitches, (list, tuple)):
        return [transpose(p, semitones) for p in pitches]
    return midi(pitches) + semitones


def invert(pitches: List[Any], axis: Any = None) -> List[float]:
    """Mirror pitches around axis (default: the first pitch)."""
    values = [midi(p) for p in pitches]
    pivot = midi(axis) if axis is not None else values[0]
    return [2 * pivot - v for v in values]


def retrograde(seq: Any) -> List[Any]:
    return list(seq)[::-1]


def rotate(seq: Any, n: int = 1) -> List[Any]:
    items = list(seq)
    if not items:
        return items
    n %= len(items)
    return items[n:] + items[:n]


def euclid(hits: int, steps: int) -> List[int]:
    """Euclidean rhythm: `hits` onsets spread as evenly as possible over `steps` (1 = onset)."""
    hits, steps = int(hits), int(steps)
    if steps <= 0:
        return []
    hits = max(0, min(hits, steps))
    return [1 if (i * hits) % steps < hits else 0 for i in range(steps)]


class _StepLimit(BaseException):
    pass


_SAFE_BUILTINS: Dict[str, Any] = {
    name: getattr(builtins, name)
    for name in (
        "range", "len", "enumerate", "zip", "min", "max", "sum", "abs", "round", "int",
        "float", "str", "bool", "list", "dict", "tuple", "set", "sorted", "reversed",
        "map", "filter", "any", "all", "divmod", "pow", "isinstance",
    )
}

_FORBIDDEN_NODES = (
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.ClassDef, ast.Try,
    ast.With, ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await,
    ast.Yield, ast.YieldFrom, ast.Delete,
)


def _check(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ScoreError(
                f"line {node.lineno}: import is not available. Everything you need is "
                f"already defined: {HELP}"
            )
        if isinstance(node, _FORBIDDEN_NODES):
            raise ScoreError(f"line {getattr(node, 'lineno', '?')}: {type(node).__name__} is not allowed here")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ScoreError(f"line {node.lineno}: attribute {node.attr!r} is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ScoreError(f"line {node.lineno}: name {node.id!r} is not allowed")


def run_program(code: str, bpm: float = 60.0, seed: int = 0) -> Dict[str, Any]:
    """Execute a composition program and return a JSON score for normalize_score().

    Raises ScoreError with a line number and a fixable message on any failure.
    """
    code = (code or "").strip()
    if not code:
        raise ScoreError("code is empty")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise ScoreError(f"syntax error on line {exc.lineno}: {exc.msg}") from None
    _check(tree)

    events: Dict[int, List[Dict[str, Any]]] = {}
    meta: Dict[int, Dict[str, Any]] = {}
    cursors: Dict[int, float] = {}
    printed: List[str] = []
    count = [0]

    def _voice_index(v: Any) -> int:
        if isinstance(v, bool) or not isinstance(v, int) or v < 1 or v > 64:
            raise ScoreError(f"voice must be an integer 1..64, got {v!r}")
        return v

    def note(pitch: Any, dur: float = 1, t: Optional[float] = None, vel: Optional[float] = None,
             voice: int = 1, dyn: Optional[str] = None, art: Any = None, head: Optional[str] = None,
             gliss: Any = None) -> None:
        vi = _voice_index(voice)
        start = cursors.get(vi, 0.0) if t is None else t
        event: Dict[str, Any] = {"pitch": pitch, "dur": dur, "t": start}
        for key, value in (("vel", vel), ("dyn", dyn), ("art", art), ("head", head), ("gliss", gliss)):
            if value is not None:
                event[key] = value
        events.setdefault(vi, []).append(event)
        if isinstance(start, (int, float)) and isinstance(dur, (int, float)):
            cursors[vi] = start + dur
        count[0] += 1
        if count[0] > MAX_EVENTS:
            raise ScoreError(f"more than {MAX_EVENTS} notes generated")

    def rest(dur: float = 1, voice: int = 1) -> None:
        vi = _voice_index(voice)
        cursors[vi] = cursors.get(vi, 0.0) + dur

    def voice(n: int, name: Optional[str] = None, clef: Optional[str] = None) -> None:
        entry = meta.setdefault(_voice_index(n), {})
        if name:
            entry["name"] = name
        if clef:
            entry["clef"] = clef

    def now(voice: int = 1) -> float:
        return cursors.get(_voice_index(voice), 0.0)

    def _print(*args: Any) -> None:
        if len(printed) < 20:
            printed.append(" ".join(str(a) for a in args)[:200])

    env: Dict[str, Any] = {
        "__builtins__": dict(_SAFE_BUILTINS, print=_print),
        "note": note, "rest": rest, "voice": voice, "now": now,
        "midi": midi, "scale": scale, "chord": chord, "transpose": transpose,
        "invert": invert, "retrograde": retrograde, "rotate": rotate, "euclid": euclid,
        "rnd": random.Random(seed), "bpm": bpm,
        "sin": math.sin, "cos": math.cos, "pi": math.pi, "floor": math.floor,
        "ceil": math.ceil, "sqrt": math.sqrt, "log": math.log, "exp": math.exp, "gcd": math.gcd,
    }

    steps = [0]

    def tracer(frame: Any, event: str, arg: Any) -> Optional[Callable[..., Any]]:
        if frame.f_code.co_filename != "<compose>":
            return None
        # Count opcodes, not lines: `while True: pass` on one line emits no line events.
        frame.f_trace_opcodes = True
        if event == "opcode":
            steps[0] += 1
            if steps[0] > MAX_STEPS:
                raise _StepLimit()
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        exec(compile(tree, "<compose>", "exec"), env)  # noqa: S102 — restricted above
    except _StepLimit:
        raise ScoreError("program ran too long (infinite loop?). Make it terminate.") from None
    except ScoreError as exc:
        raise ScoreError(f"{_line_of(exc)}{exc}") from None
    except RecursionError:
        raise ScoreError("program recursed too deeply") from None
    except NameError as exc:
        raise ScoreError(f"{_line_of(exc)}{exc}. Available: {HELP}") from None
    except Exception as exc:  # noqa: BLE001 — every failure goes back to the model as text
        raise ScoreError(f"{_line_of(exc)}{type(exc).__name__}: {exc}") from None
    finally:
        sys.settrace(previous)

    if not events:
        raise ScoreError("the program finished but never called note(...), so the score is empty")

    voices = []
    for vi in range(1, max(max(events), max(meta, default=1)) + 1):
        entry: Dict[str, Any] = dict(meta.get(vi, {}))
        entry["notes"] = events.get(vi, [])
        voices.append(entry)
    return {"bpm": bpm, "voices": voices, "printed": printed}


def _line_of(exc: BaseException) -> str:
    """Prefix naming the line of the model's program where exc surfaced."""
    tb = exc.__traceback__
    line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == "<compose>":
            line = tb.tb_lineno
        tb = tb.tb_next
    return f"line {line}: " if line else ""
