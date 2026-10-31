"""
reader.py
---------
What read_score shows the model of a bachjson-complete score. The complete
score is lossless and long; the model needs the music, and only as much of it
as its context can afford. So the answer has two parts:

    an overview     one line per voice, always about the whole score: its number,
                    name, clef/key when the score has them, notes, time span,
                    pitch range, muted/hidden; then the total length and markers.
                    It costs a few lines and tells the model what exists, so it can
                    ask for the right window instead of reading everything.
    the music       the compressed form (compress.py), the same one write_score
                    takes, for the voices and window asked. Every voice keeps its
                    number ("voice": n), so a filtered or sparse answer stays
                    unambiguous; empty voices are left out (the overview names them).

When the music does not fit `budget` characters, it is cut at one time for all
voices together (never voice 1 whole and the rest missing): the latest onset T
such that every chord before T fits. The answer then says where it stopped and
how to go on (from_ms=T), so a long score is read as consecutive windows.

What is never shown: the header beyond the above (slotinfo, commands, voice
spacing, groups ...). write_score keeps it from the roll, so the model never
needs it.
"""

from __future__ import annotations

import json
from bisect import bisect_left
from typing import Any, Dict, List, Optional, Tuple

from .compress import compress, number

DEFAULT_BUDGET = 24000  # characters of music, ~8K tokens: room left to think in a 64K context

_FLAGS = ((1, "locked"), (2, "muted"), (4, "solo"))


def _dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def _label(names: Any) -> str:
    if names in (None, "", []):
        return ""
    return " ".join(map(str, names)) if isinstance(names, list) else str(names)


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
    end = max(c.get("onset", 0) + max(n.get("dur", 0) for n in c["notes"]) for c in chords)
    facts = [f"{len(notes)} notes in {len(chords)} chords",
             f"{number(chords[0].get('onset', 0))}-{number(end)} ms",
             f"pitch {number(min(pitches))}-{number(max(pitches))}"] + facts
    return f"{head}: {', '.join(facts)}"


def overview(score: Dict[str, Any]) -> str:
    """A few lines about the whole score, whatever window is shown."""
    header = score.get("header") or {}
    voices = score.get("voices") or []
    lines = [_voice_line(i, v, header) for i, v in enumerate(voices)]
    ends = [c.get("onset", 0) + max((n.get("dur", 0) for n in c.get("notes") or []), default=0)
            for v in voices for c in v.get("chords") or []]
    total = sum(len(c.get("notes") or []) for v in voices for c in v.get("chords") or [])
    lines.append(f"{len(voices)} voice(s), {total} notes, {number(max(ends, default=0))} ms long.")
    markers = header.get("markers") or []
    if markers:
        shown = [f"{_label(m.get('name')) or m.get('role', '?')}@{number(m.get('onset'))}" for m in markers[:40]]
        more = f" (+{len(markers) - 40} more)" if len(markers) > 40 else ""
        lines.append("markers: " + " ".join(shown) + more)
    return "\n".join(lines)


def _window(short: Dict[str, Any], voice: int, from_ms: float, to_ms: float) -> Dict[str, Any]:
    """The compressed score cut to the voice and window asked, every voice numbered."""
    def inside(onset: Any) -> bool:
        return onset >= from_ms and (to_ms < 0 or onset < to_ms)

    voices = []
    for i, v in enumerate(short.get("voices") or []):
        if voice > 0 and i + 1 != voice:
            continue
        chords = [c for c in v.get("chords") or [] if inside(c[0])]
        if chords:
            voices.append({"voice": i + 1, **{k: x for k, x in v.items() if k != "chords"}, "chords": chords})
    out: Dict[str, Any] = {}
    if "slots" in short:
        out["slots"] = short["slots"]
    markers = [m for m in short.get("markers") or [] if inside(m[0])]
    if markers:
        out["markers"] = markers
    out["voices"] = voices
    return out


def _until(music: Dict[str, Any], cut: float) -> Dict[str, Any]:
    out = dict(music)
    out["voices"] = [dict(v, chords=[c for c in v["chords"] if c[0] < cut]) for v in music["voices"]]
    out["voices"] = [v for v in out["voices"] if v["chords"]]
    if "markers" in music:
        out["markers"] = [m for m in music["markers"] if m[0] < cut]
    return out


def _fit(music: Dict[str, Any], budget: int) -> Tuple[Dict[str, Any], Optional[float]]:
    """The music whole, or up to the latest time that fits `budget` (and that time)."""
    if len(_dumps(music)) <= budget:
        return music, None
    onsets = sorted({c[0] for v in music["voices"] for c in v["chords"]})
    # Find the largest k such that everything before onsets[k] fits; at least the first onset is shown.
    lo, hi = 1, len(onsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(_dumps(_until(music, onsets[mid]))) <= budget:
            lo = mid
        else:
            hi = mid - 1
    cut = onsets[lo] if lo < len(onsets) else None
    if cut is None:
        return music, None
    return _until(music, cut), cut


def read_view(score: Dict[str, Any], voice: int = 0, from_ms: float = -1.0, to_ms: float = -1.0,
              budget: int = DEFAULT_BUDGET) -> str:
    """The answer to read_score: the overview, then the music asked, cut to fit `budget`."""
    music = _window(compress(score), voice, from_ms, to_ms)
    if not music["voices"]:
        what = f"voice {voice}" if voice > 0 else "the score"
        where = "" if from_ms < 0 and to_ms < 0 else " in this window"
        return f"{overview(score)}\nNo notes in {what}{where}."
    shown, cut = _fit(music, budget)
    text = f"{overview(score)}\n{_dumps(shown)}"
    if cut is not None:
        start = number(max(from_ms, 0))
        text += (f"\n(cut to fit: shown {start}-{number(cut)} ms of the window. "
                 f"Read on with from_ms={number(cut)}, or narrow with voice.)")
    return text


__all__ = ["read_view", "overview", "DEFAULT_BUDGET"]
