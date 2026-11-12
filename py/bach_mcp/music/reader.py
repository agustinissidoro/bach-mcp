"""
reader.py
---------
What the model is shown of a bachjson-complete score. The model reads and writes
the same syntax every other part uses (bachjson-syntax-specification.md): there
is no second form. Only what carries no information is left out of a reading.

read_score's answer has two parts:

    an overview     one line per voice, always about the whole score: its number,
                    name, clef/key when the score has them, notes, time span,
                    pitch range, muted/hidden; then the total length and markers.
                    It costs a few lines and tells the model what exists, so it can
                    ask for the right window instead of reading everything.
    the music       the score itself, {"header": ..., "voices": [...]}, for the
                    voices and window asked (lean, below).

lean(score) is the score with:

    header      only clefs, keys, voicenames and markers, and of slotinfo the name
                and type of the slots the notes shown use. The rest (commands, voice
                spacing, groups, the other slots ...) is never needed to write
                music, and write_score keeps it from the roll.
    defaults    no "flag": 0, no empty lists or objects.
    numbers     at most two decimals, a whole number without ".0".

Every voice stays in its place in "voices", so a voice is always found by its
position: one that is not shown (another voice was asked, or it has nothing in
the window) is {"chords": []}, and the line before the music says what is shown.

When the music does not fit `budget` characters, it is cut at one time for all
voices together (never voice 1 whole and the rest missing): the latest onset T
such that every chord before T fits. The answer then says where it stopped and
how to go on (from_ms=T), so a long score is read as consecutive windows.

describe(score) is the few lines a tool answers after writing.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_BUDGET = 36000  # characters of music, about 18K tokens (2 characters a token): room left to think in a 64K context
DIGITS = 2

# The header elements the model reads; slotinfo is added for the slots in use.
HEADER_SHOWN = ("clefs", "keys", "voicenames", "markers")
SLOT_FIELDS_SHOWN = ("name", "type")

_FLAGS = ((1, "locked"), (2, "muted"), (4, "solo"))


def number(x: Any, digits: int = DIGITS) -> Any:
    """A number with at most `digits` decimals, and none when it is whole; anything else as it is."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return x
    r = round(float(x), digits)
    return int(r) if r == int(r) else r


def _dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def _label(names: Any) -> str:
    if names in (None, "", []):
        return ""
    return " ".join(map(str, names)) if isinstance(names, list) else str(names)


def _end(chord: Dict[str, Any]) -> float:
    return chord.get("onset", 0) + max((n.get("dur", 0) for n in chord.get("notes") or []), default=0)


def count_notes(score: Dict[str, Any]) -> int:
    return sum(len(c.get("notes") or []) for v in score.get("voices") or [] for c in v.get("chords") or [])


# ── Lean ─────────────────────────────────────────────────────────────────── #

def _lean(x: Any) -> Any:
    """Numbers shortened, and inside objects no "flag": 0 and nothing empty."""
    if isinstance(x, list):
        return [_lean(v) for v in x]
    if isinstance(x, dict):
        out = {}
        for key, value in x.items():
            if (key == "flag" and not value) or value in (None, "", [], {}):
                continue
            out[key] = _lean(value)
        return out
    return number(x)


def _slots_used(voices: List[Dict[str, Any]]) -> List[str]:
    used = {str(k) for v in voices for c in v.get("chords") or [] for n in c.get("notes") or []
            for k, items in (n.get("slots") or {}).items() if items not in (None, [])}
    return sorted(used, key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0, k))


def lean(score: Dict[str, Any]) -> Dict[str, Any]:
    """The score as the model reads it: the same syntax, without what says nothing (see above)."""
    full = score.get("header") or {}
    voices = score.get("voices") or []
    header: Dict[str, Any] = {}
    for key in HEADER_SHOWN:
        value = full.get(key)
        if value in (None, [], {}):
            continue
        if key == "markers":  # a marker keeps its name even when empty: it is part of what a marker is
            header[key] = [{k: number(v) if k == "onset" else _lean(v) for k, v in m.items()
                            if not (k == "content" and v in (None, []))} for m in value]
        else:
            header[key] = _lean(value) if key != "voicenames" else value  # an unnamed voice stays [] in its place
    slotinfo = full.get("slotinfo") or {}
    shown = {k: {f: slotinfo[k][f] for f in SLOT_FIELDS_SHOWN if slotinfo[k].get(f)}
             for k in _slots_used(voices) if isinstance(slotinfo.get(k), dict)}
    if shown:
        header["slotinfo"] = shown
    out: Dict[str, Any] = {}
    if header:
        out["header"] = header
    out["voices"] = [{**_lean({k: v for k, v in voice.items() if k != "chords"}),
                      "chords": _lean(voice.get("chords") or [])} for voice in voices]
    return out


# ── The overview ─────────────────────────────────────────────────────────── #

def _voice_line(i: int, voice: Dict[str, Any], header: Dict[str, Any]) -> str:
    def per_voice(key: str) -> Any:
        values = header.get(key) or []
        return values[i] if i < len(values) else None

    name = _label(per_voice("voicenames"))
    head = f"voice {i + 1}" + (f" ({name})" if name else "")
    facts = []
    if per_voice("clefs"):
        facts.append(f"clef {per_voice('clefs')}")
    if per_voice("keys") and per_voice("keys") != "CM":
        facts.append(f"key {per_voice('keys')}")
    flag = voice.get("flag") or 0
    facts += [word for bit, word in _FLAGS if flag & bit]
    if per_voice("hidevoices"):
        facts.append("hidden")
    chords = [c for c in voice.get("chords") or [] if c.get("notes")]
    if not chords:
        return f"{head}: empty" + (f", {', '.join(facts)}" if facts else "")
    notes = [n for c in chords for n in c["notes"]]
    pitches = [n.get("pitch", 0) for n in notes]
    end = max(_end(c) for c in chords)
    facts = [f"{len(notes)} notes in {len(chords)} chords",
             f"{number(chords[0].get('onset', 0))}-{number(end)} ms",
             f"pitch {number(min(pitches))}-{number(max(pitches))}"] + facts
    return f"{head}: {', '.join(facts)}"


def _markers_line(markers: List[Dict[str, Any]]) -> str:
    shown = [f"{_label(m.get('name')) or m.get('role', '?')}@{number(m.get('onset'))}" for m in markers[:40]]
    more = f" (+{len(markers) - 40} more)" if len(markers) > 40 else ""
    return "markers: " + " ".join(shown) + more


def overview(score: Dict[str, Any]) -> str:
    """A few lines about the whole score, whatever window is shown."""
    header = score.get("header") or {}
    voices = score.get("voices") or []
    lines = [_voice_line(i, v, header) for i, v in enumerate(voices)]
    ends = [_end(c) for v in voices for c in v.get("chords") or []]
    lines.append(f"{len(voices)} voice(s), {count_notes(score)} notes, {number(max(ends, default=0))} ms long.")
    markers = header.get("markers") or []
    if markers:
        lines.append(_markers_line(markers))
    return "\n".join(lines)


def describe(score: Dict[str, Any]) -> str:
    """One line per voice of a score, and its markers: what was written, for the model."""
    header = score.get("header") or {}
    names = header.get("voicenames") or []
    lines = []
    for i, v in enumerate(score.get("voices") or []):
        vn = _label(names[i]) if i < len(names) else ""
        label = f"voice {i + 1}" + (f" ({vn})" if vn else "")
        chords = [c for c in v.get("chords") or [] if c.get("notes")]
        notes = [n for c in chords for n in c["notes"]]
        if not notes:
            lines.append(f"{label}: empty")
            continue
        pitches = [n["pitch"] for n in notes]
        lines.append(f"{label}: {len(notes)} notes in {len(chords)} chords, {number(chords[0]['onset'])}-"
                     f"{number(max(_end(c) for c in chords))} ms, pitch {number(min(pitches))}-{number(max(pitches))}")
    if header.get("markers"):
        lines.append(_markers_line(header["markers"]))
    return "\n".join(lines)


# ── The window ───────────────────────────────────────────────────────────── #

def _window(score: Dict[str, Any], voice: int, from_ms: float, to_ms: float) -> Dict[str, Any]:
    """The score with only the chords and markers of the voice and window asked; every voice in its place."""
    def inside(onset: Any) -> bool:
        return onset >= from_ms and (to_ms < 0 or onset < to_ms)

    out = dict(score)
    out["voices"] = [dict(v, chords=[c for c in v.get("chords") or []
                                     if (voice <= 0 or i + 1 == voice) and inside(c.get("onset", 0))])
                     for i, v in enumerate(score.get("voices") or [])]
    header = dict(score.get("header") or {})
    if header.get("markers"):
        header["markers"] = [m for m in header["markers"] if inside(m.get("onset", 0))]
    out["header"] = header
    return out


def _until(score: Dict[str, Any], cut: float) -> Dict[str, Any]:
    return _window(score, 0, float("-inf"), cut)


def _fit(score: Dict[str, Any], budget: int) -> Tuple[Dict[str, Any], Optional[float]]:
    """The music whole, or up to the latest time that fits `budget` (and that time)."""
    if len(_dumps(lean(score))) <= budget:
        return score, None
    onsets = sorted({c.get("onset", 0) for v in score["voices"] for c in v["chords"]})
    if len(onsets) < 2:
        return score, None
    # The largest k such that everything before onsets[k] fits; at least the first onset is shown.
    lo, hi = 1, len(onsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(_dumps(lean(_until(score, onsets[mid])))) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return _until(score, onsets[lo]), onsets[lo]


def read_view(score: Dict[str, Any], voice: int = 0, from_ms: float = -1.0, to_ms: float = -1.0,
              budget: int = DEFAULT_BUDGET) -> str:
    """The answer to read_score: the overview, what is shown, then the music asked, cut to fit `budget`."""
    music = _window(score, voice, from_ms, to_ms)
    what = f"voice {voice}" if voice > 0 else "the score"
    windowed = from_ms >= 0 or to_ms >= 0
    if not any(v["chords"] for v in music["voices"]):
        return f"{overview(score)}\nNo notes in {what}{' in this window' if windowed else ''}."
    shown, cut = _fit(music, budget)
    start = number(max(from_ms, 0))
    lines = [overview(score)]
    if voice > 0 or windowed or cut is not None:
        end = number(cut) if cut is not None else (number(to_ms) if to_ms >= 0 else "the end")
        only = f"only voice {voice}" if voice > 0 else "all voices"
        lines.append(f"Shown: {only}, {start} ms to {end}. A voice with no chords here is only not shown.")
    lines.append(_dumps(lean(shown)))
    if cut is not None:
        lines.append(f"(cut to fit: shown {start}-{number(cut)} ms of the window. "
                     f"Read on with from_ms={number(cut)}, or narrow with voice.)")
    return "\n".join(lines)


__all__ = ["read_view", "overview", "describe", "lean", "count_notes", "number", "DEFAULT_BUDGET", "DIGITS"]
