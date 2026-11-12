"""
markers.py
----------
Markers with a role, read the way bach.quantize reads them (measureinfo "auto"):
what measures they make, and what in them bach would drop or misread without a
word. The rules come from bach's own code (mains/notation/quantize.c,
markers_to_measureinfo_and_rat_durations) and its help ("quantization from
markers"):

    timesig      opens a measure and sets the time signature from there on. It is a barline too.
    barline      opens a measure in the current time signature (4/4 before any timesig).
    division     a beat inside the measure. The first beat is the barline itself, so a measure
                 of n beats has n - 1 division markers. The beats share the measure equally in
                 notation, whatever their times: their times bend the tempo, beat by beat.
    subdivision  a unit inside a beat (the first is the beat itself). They count only when the
                 beats of a measure have different numbers of them (2+2+3/8); then the units
                 of the measure must divide the numerator. Their exact times do not matter.
    tempo        [value] or [figure, value]; it applies from the next measure, so it stands
                 before the barline it belongs to. bach.quantize uses it only with its
                 tempohandling set from markers; otherwise the tempo is the barlines' spacing.

    ordered(markers)   in time order, at one onset the tempo first, then what opens the measure
    check(markers)     (errors, warnings): what bach would misread, and what may not be meant
    measures(markers)  the measures the markers make
    report(markers)    the measures in a few lines, for the model: what its markers mean
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

ROLES = ("none", "tempo", "timesig", "barline", "division", "subdivision")
_ORDER = {"tempo": 0, "timesig": 1, "barline": 1, "division": 2, "subdivision": 3, "none": 4}
_FIGURES = {Fraction(1, 1): "whole", Fraction(1, 2): "half", Fraction(1, 4): "quarter", Fraction(1, 8): "eighth",
            Fraction(1, 16): "sixteenth", Fraction(3, 8): "dotted quarter", Fraction(3, 4): "dotted half",
            Fraction(3, 16): "dotted eighth"}
MAX_LINES = 12


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _num(x: float) -> Any:
    r = round(float(x), 2)
    return int(r) if r == int(r) else r


def ordered(markers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The markers in time order; at one onset the tempo, then timesig or barline, then the rest."""
    placed = sorted(enumerate(markers), key=lambda im: (im[1].get("onset", 0), _ORDER.get(im[1].get("role", "none"), 4), im[0]))
    return [m for _, m in placed]


def _timesig(content: Any) -> Optional[Tuple[List[int], int]]:
    """[3, 4] or [[2, 2, 3], 8] as (numerator parts, denominator); None if it is not a time signature."""
    if not isinstance(content, list) or len(content) != 2:
        return None
    num, den = content
    parts = num if isinstance(num, list) else [num]
    if not parts or not all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in parts):
        return None
    if not isinstance(den, int) or isinstance(den, bool) or den <= 0 or den & (den - 1):
        return None
    return parts, den


def _figure(x: Any) -> Optional[Fraction]:
    try:
        f = Fraction(x) if isinstance(x, str) else (Fraction(x) if isinstance(x, int) and not isinstance(x, bool) else None)
    except (ValueError, ZeroDivisionError):
        return None
    return f if f and f > 0 else None


def _ts_text(parts: List[int], den: int) -> str:
    return f"{'+'.join(map(str, parts))}/{den}"


def measures(markers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The measures the role markers make, in order: {start, end (None: nothing closes it), ts: (parts, den),
    beats, units: subdivisions counted beat by beat, irregular}. Markers before the first measure are not in any."""
    out: List[Dict[str, Any]] = []
    ts: Tuple[List[int], int] = ([4], 4)
    current: Optional[Dict[str, Any]] = None
    for m in ordered(markers):
        role = m.get("role", "none")
        if role in ("timesig", "barline"):
            if current is not None:
                current["end"] = m["onset"]
            if role == "timesig":
                ts = _timesig(m.get("content")) or ts
            current = {"start": m["onset"], "end": None, "ts": ts, "beats": [m["onset"]], "units": [1]}
            out.append(current)
        elif current is not None and role == "division":
            current["beats"].append(m["onset"])
            current["units"].append(1)
        elif current is not None and role == "subdivision":
            current["units"][-1] += 1
    for bar in out:
        bar["irregular"] = len(set(bar["units"])) > 1
    return out


def _bar_text(bar: Dict[str, Any]) -> str:
    """One measure in words: its time signature as bach will write it, its length, its tempo."""
    parts, den = bar["ts"]
    total = sum(parts)
    whole = Fraction(total, den)
    beats = len(bar["beats"])
    shown = _ts_text(parts, den)
    if bar["irregular"]:
        units = sum(bar["units"])
        if total % units == 0:
            shown = _ts_text([u * (total // units) for u in bar["units"]], den)
    text = shown
    if bar["end"] is None:
        return text + ", open (no barline after it)"
    length = bar["end"] - bar["start"]
    figure = whole / beats if beats > 1 and not bar["irregular"] else Fraction(1, den)
    if length > 0:
        bpm = 60000.0 * float(whole / figure) / length  # how many of that figure fit in a minute
        name = _FIGURES.get(figure, f"{figure} note")
        text += f", {_num(length)} ms ({name} = {_num(bpm)})"
    if beats > 1:
        text += f", {beats} beats"
    return text


def report(markers: List[Dict[str, Any]]) -> str:
    """What the role markers mean to bach.quantize, in a few lines; '' when there are none with a role."""
    bars = measures(markers)
    if not bars:
        return ""
    lines: List[str] = []
    first = bars[0]["start"]
    closing = bars.pop()["start"] if len(bars) > 1 and len(bars[-1]["beats"]) == 1 else None  # the last barline only closes
    early = [m for m in markers if m.get("role") in ("division", "subdivision") and m.get("onset", 0) < first]
    start = 0
    while start < len(bars):
        text = _bar_text(bars[start])
        end = start
        while end + 1 < len(bars) and _bar_text(bars[end + 1]) == text:
            end += 1
        label = f"measure {start + 1}" if end == start else f"measures {start + 1}-{end + 1}"
        each = " each" if end > start and bars[start]["end"] is not None else ""
        lines.append(f"  {label}, from {_num(bars[start]['start'])} ms: {text}{each}")
        start = end + 1
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES - 1] + [f"  ... {len(lines) - MAX_LINES + 1} more groups of measures"]
    head = f"Measures, as bach.quantize will read the markers ({len(bars)}):"
    if first > 0:
        head += f" what comes before {_num(first)} ms is a pickup."
    tempi = [m for m in markers if m.get("role") == "tempo"]
    tail = []
    if closing is not None:
        tail.append(f"  the barline at {_num(closing)} ms closes measure {len(bars)}; for music after it, bach repeats the measures given.")
    if tempi:
        tail.append(f"  {len(tempi)} tempo marker(s): used only when bach.quantize has tempohandling set from markers.")
    if early:
        tail.append(f"  {len(early)} division/subdivision marker(s) before the first measure are ignored.")
    return "\n".join([head] + lines + tail)


def check(markers: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """(errors, warnings) for markers already known to be well-formed objects (onset, role).
    An error is something bach would drop or misread; a warning, something that may not be meant."""
    errors: List[str] = []
    warnings: List[str] = []
    seq = ordered(markers)
    openers: Dict[Any, str] = {}
    for m in seq:
        role, onset, content = m.get("role", "none"), m.get("onset"), m.get("content")
        at = f"{role} at {_num(onset)} ms"
        if role == "timesig":
            if _timesig(content) is None:
                errors.append(f'{at}: its content is the time signature, [numerator, denominator] with a denominator '
                              f'1, 2, 4, 8, 16 ..., e.g. [3, 4] or [[2, 2, 3], 8]; got {content!r}')
        elif role == "tempo":
            ok = isinstance(content, list) and len(content) in (1, 2) and _is_number(content[-1]) and content[-1] > 0 \
                and (len(content) == 1 or _figure(content[0]) is not None)
            if not ok:
                errors.append(f'{at}: its content is [figure, value], e.g. ["1/4", 60]; got {content!r}')
        elif role in ("barline", "division", "subdivision") and content not in (None, []):
            errors.append(f"{at}: a {role} has no content; leave it out")
        if role in ("timesig", "barline"):
            if onset in openers:
                both = {openers[onset], role}
                errors.append(f"{' and '.join(sorted(both))} at {_num(onset)} ms: " + (
                    "a timesig is already the barline of its measure; keep only the timesig" if len(both) == 2
                    else f"two {role} markers at the same time; keep one"))
            openers[onset] = role
    for m in seq:
        if m.get("role") == "division" and m.get("onset") in openers:
            errors.append(f"division at {_num(m['onset'])} ms: the first beat of a measure is its barline; "
                          "a division there counts as one beat more")
    bars = measures(markers)
    for i, bar in enumerate(bars, 1):
        parts, den = bar["ts"]
        total, beats = sum(parts), len(bar["beats"])
        where = f"measure {i} (from {_num(bar['start'])} ms, {_ts_text(parts, den)})"
        if bar["end"] is not None and bar["end"] <= bar["start"]:
            continue
        if bar["irregular"]:
            units = sum(bar["units"])
            if total % units:
                errors.append(f"{where}: its beats hold {'+'.join(map(str, bar['units']))} = {units} units, which does "
                              f"not divide the numerator {total}; bach would drop the subdivisions or change the time signature")
        elif beats > 1:
            figure = Fraction(total, den) / beats
            if figure.denominator & (figure.denominator - 1) or figure.numerator not in (1, 3):
                warnings.append(f"{where}: {beats} beats ({beats - 1} division markers) make each beat {figure} of a "
                                "whole note, which is not a note value; a measure of n beats has n - 1 division markers")
        if len(parts) > 1 and not bar["irregular"] and bar["end"] is not None:
            warnings.append(f"{where}: the groups {'+'.join(map(str, parts))} need a division at each group and a "
                            "subdivision at each unit inside it; without them bach beats the measure evenly")
    if bars and bars[-1]["end"] is None and len(bars) > 0:
        last = bars[-1]
        if len(bars) == 1:
            warnings.append(f"only one barline or timesig (at {_num(last['start'])} ms): a measure needs the next "
                            "barline to have a length, so bach cannot tell the tempo")
    if not bars and any(m.get("role") in ("division", "subdivision") for m in markers):
        errors.append("division or subdivision markers without any barline or timesig: there is no measure to divide")
    # keep the list short and without repeats
    def short(items: List[str]) -> List[str]:
        seen: List[str] = []
        for item in items:
            if item not in seen:
                seen.append(item)
        return seen[:6] + ([f"... and {len(seen) - 6} more of the same kind"] if len(seen) > 6 else [])
    return short(errors), short(warnings)


__all__ = ["ROLES", "ordered", "check", "measures", "report"]
