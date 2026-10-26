"""
compress.py
-----------
bachjson-complete <-> the compressed form the model reads and writes. It exists
only to save the model's context; everywhere else scores are bachjson-complete
(bachjson-syntax-specification.md).

    compress(score)          complete -> compressed
    expand(short, base)      compressed -> complete; what the compressed form does not
                             show (slotinfo, commands, clefs, keys ...) comes from `base`

The compressed form:

    {
      "slots":   {"20": "dynamics", ...},          the names of the slots the score uses
      "markers": [[onset, "name"], ...],
      "voices":  [{"name": "Flute", "chords": [CHORD, ...]}, ...]
    }
    CHORD  [onset, NOTE, NOTE, ..., {"name": [...], "flag": 1}?]    the object only when needed
    NOTE   [pitch, dur, vel, {EXTRAS}?]                            the object only when needed
    EXTRAS slots by name (or number), a one-item slot as its item: {"dynamics": "p<"}
           "gliss": the pitch breakpoints, "art": articulations, "spelling", "graphic", "name", "flag"

A slot's name comes from the score's slotinfo; bach.roll's linked slots have
their usual names even without it: dynamics 20, lyrics 21, articulations 22,
notehead 23, annotation 24.

"gliss" is bach's breakpoints without the first point (always [0, 0, 0]): a
number when the note only slides to the end, linearly ([[1, 200, 0]] -> 200),
else [position, midicents] or [position, midicents, slope] points, the last at
position 1. A fourth number in a point is its velocity.

Nothing empty is written: no empty keys, arrays or objects, no flag 0. Numbers
keep at most two decimals, and a whole number has none (6000, not 6000.0).
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

DIGITS = 2

# Note fields and their short names in EXTRAS (breakpoints are "gliss", see below).
_NOTE_EXTRAS = (("articulations", "art"), ("spelling", "spelling"), ("graphic", "graphic"), ("name", "name"))

# bach.roll's linked slots, named even when the score has no slotinfo.
DEFAULT_SLOTS = {"20": "dynamics", "21": "lyrics", "22": "articulations", "23": "notehead", "24": "annotation"}
_LONG = {short: long for long, short in _NOTE_EXTRAS}


def number(x: Any, digits: int = DIGITS) -> Any:
    """A number with at most `digits` decimals, and none when it is whole; anything else as it is."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return x
    r = round(float(x), digits)
    return int(r) if r == int(r) else r


def numbers(x: Any) -> Any:
    """`number` applied all the way down a list."""
    return [numbers(v) for v in x] if isinstance(x, list) else number(x)


def _slot_names(header: Dict[str, Any]) -> Dict[str, str]:
    """Slot number -> its name: the one slotinfo gives it, else bach's usual one for linked slots."""
    out = dict(DEFAULT_SLOTS)
    for key, fields in (header.get("slotinfo") or {}).items():
        name = (fields or {}).get("name")
        if isinstance(name, list) and name and isinstance(name[0], str):
            out[str(key)] = name[0]
    return out


def _short_slot(items: List[Any]) -> Any:
    """A slot's items, a single plain item as itself."""
    items = numbers(items)
    return items[0] if len(items) == 1 and not isinstance(items[0], list) else items


def gliss(breakpoints: List[List[Any]]) -> Any:
    """bach's breakpoints -> "gliss": without the first point; a plain slide to the end as a number."""
    points = [numbers(p) for p in breakpoints if not (p and p[0] == 0)]
    if len(points) == 1 and len(points[0]) == 3 and points[0][0] == 1 and points[0][2] == 0:
        return points[0][1]
    return [p[:2] if len(p) == 3 and p[2] == 0 else p for p in points]


def breakpoints(g: Any) -> List[List[Any]]:
    """"gliss" -> bach's breakpoints, starting at [0, 0, 0] and ending at position 1."""
    if isinstance(g, (int, float)):
        return [[0, 0, 0], [1, g, 0]]
    points = [[p[0], p[1], p[2] if len(p) > 2 else 0] + list(p[3:]) for p in g]
    return [[0, 0, 0]] + points


def _note(n: Dict[str, Any], names: Dict[str, str], used: Dict[str, str]) -> List[Any]:
    out: List[Any] = [number(n.get("pitch")), number(n.get("dur")), n.get("vel")]
    extras: Dict[str, Any] = {}
    for key, value in (n.get("slots") or {}).items():
        if value in (None, []):
            continue
        label = names.get(str(key), str(key))
        used[str(key)] = label
        extras[label] = _short_slot(value)
    if n.get("breakpoints"):
        extras["gliss"] = gliss(n["breakpoints"])
    for long, short in _NOTE_EXTRAS:
        if n.get(long) not in (None, "", []):
            extras[short] = numbers(n[long])
    if n.get("flag"):
        extras["flag"] = n["flag"]
    if extras:
        out.append(extras)
    return out


def _chord(c: Dict[str, Any], names: Dict[str, str], used: Dict[str, str]) -> List[Any]:
    out: List[Any] = [number(c.get("onset"))]
    out += [_note(n, names, used) for n in c.get("notes") or []]
    extras = {}
    if c.get("name"):
        extras["name"] = c["name"]
    if c.get("flag"):
        extras["flag"] = c["flag"]
    if extras:
        out.append(extras)
    return out


def compress(score: Dict[str, Any]) -> Dict[str, Any]:
    """bachjson-complete -> the compressed form."""
    header = score.get("header") or {}
    names = _slot_names(header)
    used: Dict[str, str] = {}
    voicenames = header.get("voicenames") or []
    voices = []
    for i, v in enumerate(score.get("voices") or []):
        voice: Dict[str, Any] = {}
        vn = voicenames[i] if i < len(voicenames) else []
        if vn:
            voice["name"] = vn[0] if len(vn) == 1 else vn
        voice["chords"] = [_chord(c, names, used) for c in v.get("chords") or []]
        if v.get("flag"):
            voice["flag"] = v["flag"]
        voices.append(voice)
    out: Dict[str, Any] = {}
    named = {k: v for k, v in used.items() if v != k and DEFAULT_SLOTS.get(k) != v}
    if named:
        out["slots"] = dict(sorted(named.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0))
    markers = []
    for m in header.get("markers") or []:
        name = m.get("name") or []
        row = [number(m.get("onset")), name[0] if len(name) == 1 else name]
        if m.get("role", "none") != "none":
            row += [m["role"], m.get("content", [])]
        markers.append(row)
    if markers:
        out["markers"] = markers
    out["voices"] = voices
    return out


# ── Back to complete ─────────────────────────────────────────────────────── #

def _names_list(value: Any) -> List[Any]:
    if value in (None, "", []):
        return []
    return value if isinstance(value, list) else [value]


def _expand_note(row: List[Any], numbers_by_name: Dict[str, str]) -> Dict[str, Any]:
    n: Dict[str, Any] = {"pitch": row[0], "dur": row[1], "vel": row[2] if len(row) > 2 and not isinstance(row[2], dict) else 100}
    extras = next((x for x in row[2:] if isinstance(x, dict)), {})
    slots: Dict[str, Any] = {}
    for key, value in extras.items():
        if key == "gliss":
            n["breakpoints"] = breakpoints(value)
        elif key in _LONG:
            n[_LONG[key]] = value
        elif key == "flag":
            n["flag"] = value
        else:
            slots[numbers_by_name.get(key, key)] = value if isinstance(value, list) else [value]
    if slots:
        n["slots"] = slots
    n.setdefault("flag", 0)
    return n


def _expand_chord(row: List[Any], numbers_by_name: Dict[str, str]) -> Dict[str, Any]:
    c: Dict[str, Any] = {"onset": row[0], "notes": []}
    for item in row[1:]:
        if isinstance(item, list):
            c["notes"].append(_expand_note(item, numbers_by_name))
        elif isinstance(item, dict):
            if item.get("name"):
                c["name"] = _names_list(item["name"])
            if item.get("flag"):
                c["flag"] = item["flag"]
    c.setdefault("flag", 0)
    return c


def expand(short: Dict[str, Any], base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The compressed form -> bachjson-complete. The header comes from `base` (the score it was
    made from), with the voice names and markers the compressed form gives."""
    header = copy.deepcopy((base or {}).get("header") or {})
    numbers_by_name = {name: num for num, name in _slot_names(header).items()}
    numbers_by_name.update({name: str(num) for num, name in (short.get("slots") or {}).items()})
    voices = []
    voicenames = []
    for v in short.get("voices") or []:
        voices.append({"chords": [_expand_chord(c, numbers_by_name) for c in v.get("chords") or []],
                       "flag": v.get("flag", 0)})
        voicenames.append(_names_list(v.get("name")))
    if any(voicenames) or "voicenames" in header:
        header["voicenames"] = voicenames
    if "markers" in short:
        header["markers"] = []
        for m in short["markers"]:
            marker = {"onset": m[0], "name": _names_list(m[1] if len(m) > 1 else []), "role": m[2] if len(m) > 2 else "none"}
            if len(m) > 3 and m[3]:
                marker["content"] = m[3]
            header["markers"].append(marker)
    return {"header": header, "voices": voices}


def describe(score: Dict[str, Any]) -> str:
    """One line per voice of a complete score: what was written, for the model."""
    names = (score.get("header") or {}).get("voicenames") or []
    lines = []
    for i, v in enumerate(score.get("voices") or []):
        vn = names[i] if i < len(names) and names[i] else _names_list(v.get("name"))
        label = f"voice {i + 1}" + (f" ({' '.join(map(str, vn))})" if vn else "")
        chords = v.get("chords") or []
        notes = [n for c in chords for n in c.get("notes") or []]
        if not notes:
            lines.append(f"{label}: empty")
            continue
        pitches = [n["pitch"] for n in notes]
        end = max(c["onset"] + max(n["dur"] for n in c["notes"]) for c in chords if c.get("notes"))
        lines.append(f"{label}: {len(notes)} notes in {len(chords)} chords, {number(chords[0]['onset'])}-{number(end)} ms, "
                     f"pitch {number(min(pitches))}-{number(max(pitches))}")
    markers = (score.get("header") or {}).get("markers") or []
    if markers:
        lines.append("markers: " + " ".join(f"{' '.join(map(str, m.get('name') or []))}@{number(m.get('onset'))}" for m in markers))
    return "\n".join(lines)


def count_notes(score: Dict[str, Any]) -> int:
    return sum(len(c.get("notes") or []) for v in score.get("voices") or [] for c in v.get("chords") or [])


__all__ = ["compress", "expand", "describe", "count_notes", "number", "gliss", "breakpoints", "DIGITS", "DEFAULT_SLOTS"]
