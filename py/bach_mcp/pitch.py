"""
pitch.py
--------
Exact pitch arithmetic for the model, in midicents (6000 = middle C, 100 = a
semitone). The model reasons about the music; whenever it needs a number it
calls one of these through the pitch tools (pitch_tools.py) and copies the
answer into the score.

Every function takes pitches as names ("Db4", "F#4", "E4-14") or midicents,
alone or in lists of any depth, and answers in midicents with the same shape.
The chord and scale library lives here and never enters the model's context:
it only sees the names it asks for.
"""

from __future__ import annotations

import json
import math
import re
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .translate import name_to_cents

Pitches = Union[float, List[Any]]


class PitchError(ValueError):
    """A request the pitch functions cannot answer; the message says what to fix."""


# ── Reading pitches ─────────────────────────────────────────────────────── #

_PITCH_HELP = 'a pitch is a name ("Db4", "F#5", "E4-14") or midicents (6100)'
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")


_SYMBOLS = re.compile("[♭♯𝄪𝄫♮]")


def _clean_name(text: str) -> str:
    """Flats are written b and sharps # (Db4, F#4): the symbols are refused, because a model that
    writes them drops them as often as not."""
    text = text.strip()
    if _SYMBOLS.search(text):
        plain = text.replace("♭", "b").replace("♯", "#").replace("𝄪", "##").replace("𝄫", "bb").replace("♮", "")
        raise PitchError(f"{text!r}: write flats as b and sharps as #, never the symbols: {plain!r}")
    return text[:1].upper() + text[1:] if text else text


def to_cents(value: Any, where: str = "") -> float:
    """Midicents of one pitch: a name or a number."""
    if isinstance(value, bool):
        raise PitchError(f"{where}{value!r} is not a pitch: {_PITCH_HELP}")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if _NUMBER.match(text):
            return float(text)
        cents = name_to_cents(_clean_name(text))
        if cents is not None:
            return cents
        hint = " (add the octave: C4 is middle C)" if re.fullmatch(r"[A-Ga-g](#|b|♭|♯)?", text) else ""
        raise PitchError(f"{where}{value!r} is not a pitch{hint}: {_PITCH_HELP}")
    raise PitchError(f"{where}{value!r} is not a pitch: {_PITCH_HELP}")


def read_pitches(value: Any) -> Pitches:
    """Pitches in any of the forms the model sends: a value, a list (of lists), a JSON
    list as text, or names separated by spaces or commas ("D4 F4 A4")."""
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                return read_pitches(json.loads(text))
            except json.JSONDecodeError:
                text = text.replace("[", " ").replace("]", " ")
        parts = [p for p in re.split(r"[\s,]+", text.strip().strip('"\'')) if p]
        if len(parts) > 1:
            return [to_cents(p.strip('"\'')) for p in parts]
        return to_cents(parts[0] if parts else text)
    if isinstance(value, (list, tuple)):
        return [read_pitches(v) for v in value]
    return to_cents(value)


def pitch_class(value: Any) -> float:
    """Pitch class in cents (0-1200) of a pitch; a name may leave out its octave ("D", "Eb")."""
    if isinstance(value, str):
        text = _clean_name(value)
        if re.fullmatch(r"[A-G](##|bb|#|b)?([+-]\d+(\.\d+)?)?", text):
            m = re.match(r"([A-G](?:##|bb|#|b)?)(.*)", text)
            value = f"{m.group(1)}4{m.group(2)}"
    return to_cents(value) % 1200


def _map(pitches: Pitches, fn) -> Pitches:
    if isinstance(pitches, list):
        return [_map(p, fn) for p in pitches]
    return fn(pitches)


def _flat(pitches: Pitches) -> List[float]:
    if isinstance(pitches, list):
        return [x for p in pitches for x in _flat(p)]
    return [pitches]


def tidy(pitches: Pitches) -> Any:
    """Midicents rounded to the hundredth of a cent, whole numbers without decimals."""
    def one(x: float) -> Union[int, float]:
        x = round(x, 2)
        return int(x) if x == int(x) else x
    return _map(pitches, one)


def ratio_cents(r: Union[float, Fraction]) -> float:
    return 1200 * math.log2(float(r))


# ── Transformations ─────────────────────────────────────────────────────── #

def transpose(pitches: Any, cents: Any) -> Pitches:
    """Move pitches by `cents`, or by the sum of a list of cents ([-1200, -500]: an octave and a fourth down)."""
    parts = _numbers(cents)
    if isinstance(parts, list):
        if not parts or any(isinstance(x, list) for x in parts):
            raise PitchError("cents: a number, or a flat list of numbers to add up, e.g. [-1200, -500]")
        shift = sum(_number(x, "cents") for x in parts)
    else:
        shift = _number(parts, "cents")
    return _map(read_pitches(pitches), lambda p: p + shift)


def reverse(pitches: Any) -> Pitches:
    p = read_pitches(pitches)
    return list(reversed(p)) if isinstance(p, list) else p


def mirror(pitches: Any, axis: Any = None) -> Pitches:
    p = read_pitches(pitches)
    centre = _flat(p)[0] if axis is None or axis == "" else to_cents(axis, "axis: ")
    return _map(p, lambda x: 2 * centre - x)


def p2mc(pitches: Any) -> Pitches:
    return read_pitches(pitches)


def mc2p(midicents: Any) -> Any:
    from .translate import cents_to_name
    return _map(read_pitches(midicents), cents_to_name)


_UNITS = ("ratio", "harmonic", "hz")


def get_midicents(values: Any, unit: str = "ratio", reference: Any = "C4") -> Pitches:
    """Midicents of ratios above `reference` ("5/4", 1.5), of harmonic numbers of the
    fundamental `reference` (1, 2, 3 ...), or of frequencies in Hz (A4 = 440)."""
    unit = str(unit).strip().lower()
    if unit not in _UNITS:
        raise PitchError(f'unit must be one of {", ".join(_UNITS)}, got {unit!r}')
    base = 6900.0 if unit == "hz" else to_cents(reference, "reference: ")

    def one(v: Any) -> float:
        r = _ratio(v)
        if r <= 0:
            raise PitchError(f"{v!r} must be greater than 0")
        if unit == "hz":
            return base + ratio_cents(r / 440)
        return base + ratio_cents(r)

    return _map(_numbers(values), one)


# ── Library ─────────────────────────────────────────────────────────────── #

def _semis(*steps: float) -> List[float]:
    return [s * 100 for s in steps]


def _ratios(*rs: str) -> List[float]:
    return [ratio_cents(Fraction(r)) for r in rs]


# Chords: cents above the root, in close position, root first.
CHORDS: Dict[str, List[float]] = {
    # triads
    "major": _semis(0, 4, 7), "minor": _semis(0, 3, 7), "diminished": _semis(0, 3, 6),
    "augmented": _semis(0, 4, 8), "sus2": _semis(0, 2, 7), "sus4": _semis(0, 5, 7),
    "power": _semis(0, 7), "major_b5": _semis(0, 4, 6), "major_minor": _semis(0, 3, 4, 7),
    # sixths
    "major6": _semis(0, 4, 7, 9), "minor6": _semis(0, 3, 7, 9),
    "major6_9": _semis(0, 4, 7, 9, 14), "minor6_9": _semis(0, 3, 7, 9, 14),
    # sevenths
    "major7": _semis(0, 4, 7, 11), "dominant7": _semis(0, 4, 7, 10), "minor7": _semis(0, 3, 7, 10),
    "minor_major7": _semis(0, 3, 7, 11), "half_diminished7": _semis(0, 3, 6, 10),
    "diminished7": _semis(0, 3, 6, 9), "diminished_major7": _semis(0, 3, 6, 11),
    "augmented7": _semis(0, 4, 8, 10), "augmented_major7": _semis(0, 4, 8, 11),
    "dominant7_sus4": _semis(0, 5, 7, 10), "dominant7_b5": _semis(0, 4, 6, 10),
    "major7_b5": _semis(0, 4, 6, 11),
    # added notes
    "add9": _semis(0, 4, 7, 14), "minor_add9": _semis(0, 3, 7, 14), "add11": _semis(0, 4, 7, 17),
    "add2": _semis(0, 2, 4, 7),
    # ninths
    "major9": _semis(0, 4, 7, 11, 14), "dominant9": _semis(0, 4, 7, 10, 14), "minor9": _semis(0, 3, 7, 10, 14),
    "minor_major9": _semis(0, 3, 7, 11, 14), "half_diminished9": _semis(0, 3, 6, 10, 14),
    "dominant7_b9": _semis(0, 4, 7, 10, 13), "dominant7_#9": _semis(0, 4, 7, 10, 15),
    "dominant9_sus4": _semis(0, 5, 7, 10, 14), "augmented9": _semis(0, 4, 8, 10, 14),
    "diminished9": _semis(0, 3, 6, 9, 14),
    # elevenths
    "dominant11": _semis(0, 4, 7, 10, 14, 17), "minor11": _semis(0, 3, 7, 10, 14, 17),
    "major7_#11": _semis(0, 4, 7, 11, 18), "dominant7_#11": _semis(0, 4, 7, 10, 18),
    "major9_#11": _semis(0, 4, 7, 11, 14, 18), "dominant9_#11": _semis(0, 4, 7, 10, 14, 18),
    # thirteenths and altered dominants
    "dominant13": _semis(0, 4, 7, 10, 14, 21), "minor13": _semis(0, 3, 7, 10, 14, 21),
    "major13": _semis(0, 4, 7, 11, 14, 21), "dominant13_#11": _semis(0, 4, 7, 10, 14, 18, 21),
    "dominant7_b13": _semis(0, 4, 7, 10, 20), "dominant7_b9_b13": _semis(0, 4, 7, 10, 13, 20),
    "dominant7_b9_#9": _semis(0, 4, 7, 10, 13, 15), "dominant13_b9": _semis(0, 4, 7, 10, 13, 21),
    "altered": _semis(0, 4, 10, 13, 15, 20),
    # stacked fourths and fifths
    "quartal3": _semis(0, 5, 10), "quartal4": _semis(0, 5, 10, 15), "quartal5": _semis(0, 5, 10, 15, 20),
    "quintal3": _semis(0, 7, 14), "quintal4": _semis(0, 7, 14, 21), "so_what": _semis(0, 5, 10, 15, 19),
    # clusters and sets
    "cluster3": _semis(0, 1, 2), "cluster4": _semis(0, 1, 2, 3), "cluster5": _semis(0, 1, 2, 3, 4),
    "whole_tone_cluster": _semis(0, 2, 4, 6), "quarter_tone_cluster": [0, 50, 100, 150],
    "viennese_trichord": _semis(0, 6, 11), "all_interval_tetrachord": _semis(0, 1, 4, 6),
    "all_interval_tetrachord2": _semis(0, 1, 3, 7),
    # chords with a name of their own
    "mystic": _semis(0, 6, 10, 16, 21, 26), "tristan": _semis(0, 6, 10, 15),
    "petrushka": _semis(0, 4, 7, 18, 22, 25), "elektra": _semis(0, 4, 7, 15, 19, 22),
    "dream": _semis(0, 5, 6, 7), "farben": _semis(0, 8, 11, 16, 21),
    # just intonation and other microtonal chords
    "just_major": _ratios("1", "5/4", "3/2"), "just_minor": _ratios("1", "6/5", "3/2"),
    "harmonic7": _ratios("1", "5/4", "3/2", "7/4"), "harmonic9": _ratios("1", "5/4", "3/2", "7/4", "9/4"),
    "harmonic11": _ratios("1", "5/4", "3/2", "7/4", "9/4", "11/4"),
    "utonal4": _ratios("1", "7/6", "7/5", "7/4"),
    "neutral": [0, 350, 700], "neutral7": [0, 350, 700, 1050],
}

CHORD_ALIASES: Dict[str, str] = {
    "maj": "major", "M": "major", "": "major", "m": "minor", "min": "minor", "-": "minor",
    "dim": "diminished", "°": "diminished", "o": "diminished", "aug": "augmented", "+": "augmented",
    "5": "power", "6": "major6", "m6": "minor6", "69": "major6_9", "6/9": "major6_9", "m69": "minor6_9",
    "maj7": "major7", "M7": "major7", "Δ": "major7", "Δ7": "major7", "7": "dominant7", "dom7": "dominant7",
    "m7": "minor7", "min7": "minor7", "-7": "minor7", "mmaj7": "minor_major7", "m(maj7)": "minor_major7",
    "mM7": "minor_major7", "hitchcock": "minor_major7",
    "m7b5": "half_diminished7", "ø": "half_diminished7", "ø7": "half_diminished7", "halfdiminished": "half_diminished7",
    "dim7": "diminished7", "°7": "diminished7", "o7": "diminished7", "aug7": "augmented7", "7#5": "augmented7",
    "+7": "augmented7", "maj7#5": "augmented_major7", "7sus4": "dominant7_sus4", "7sus": "dominant7_sus4",
    "7b5": "dominant7_b5", "maj9": "major9", "M9": "major9", "9": "dominant9", "m9": "minor9", "mmaj9": "minor_major9",
    "7b9": "dominant7_b9", "7#9": "dominant7_#9", "hendrix": "dominant7_#9", "9sus4": "dominant9_sus4",
    "11": "dominant11", "m11": "minor11", "maj7#11": "major7_#11", "lydian": "major7_#11", "7#11": "dominant7_#11",
    "maj9#11": "major9_#11", "9#11": "dominant9_#11", "13": "dominant13", "m13": "minor13", "maj13": "major13",
    "13#11": "dominant13_#11", "7b13": "dominant7_b13", "7b9b13": "dominant7_b9_b13", "7b9#9": "dominant7_b9_#9",
    "13b9": "dominant13_b9", "7alt": "altered", "alt": "altered", "madd9": "minor_add9",
    "prometheus": "mystic", "scriabin": "mystic", "quartal": "quartal4", "quintal": "quintal3",
    "cluster": "cluster3", "otonal": "harmonic7", "harmonic_seventh": "harmonic7",
    "utonal": "utonal4", "subharmonic": "utonal4",
}

# Scales: cents above the root, within one period (normally the octave).
SCALES: Dict[str, List[float]] = {
    # diatonic modes
    "major": _semis(0, 2, 4, 5, 7, 9, 11), "dorian": _semis(0, 2, 3, 5, 7, 9, 10),
    "phrygian": _semis(0, 1, 3, 5, 7, 8, 10), "lydian": _semis(0, 2, 4, 6, 7, 9, 11),
    "mixolydian": _semis(0, 2, 4, 5, 7, 9, 10), "minor": _semis(0, 2, 3, 5, 7, 8, 10),
    "locrian": _semis(0, 1, 3, 5, 6, 8, 10),
    # harmonic minor and its modes
    "harmonic_minor": _semis(0, 2, 3, 5, 7, 8, 11), "locrian_nat6": _semis(0, 1, 3, 5, 6, 9, 10),
    "ionian_#5": _semis(0, 2, 4, 5, 8, 9, 11), "dorian_#4": _semis(0, 2, 3, 6, 7, 9, 10),
    "phrygian_dominant": _semis(0, 1, 4, 5, 7, 8, 10), "lydian_#2": _semis(0, 3, 4, 6, 7, 9, 11),
    "ultralocrian": _semis(0, 1, 3, 4, 6, 8, 9),
    # melodic minor and its modes
    "melodic_minor": _semis(0, 2, 3, 5, 7, 9, 11), "dorian_b2": _semis(0, 1, 3, 5, 7, 9, 10),
    "lydian_augmented": _semis(0, 2, 4, 6, 8, 9, 11), "lydian_dominant": _semis(0, 2, 4, 6, 7, 9, 10),
    "mixolydian_b6": _semis(0, 2, 4, 5, 7, 8, 10), "locrian_nat2": _semis(0, 2, 3, 5, 6, 8, 10),
    "altered": _semis(0, 1, 3, 4, 6, 8, 10),
    # other heptatonic
    "harmonic_major": _semis(0, 2, 4, 5, 7, 8, 11), "double_harmonic": _semis(0, 1, 4, 5, 7, 8, 11),
    "hungarian_minor": _semis(0, 2, 3, 6, 7, 8, 11), "hungarian_major": _semis(0, 3, 4, 6, 7, 9, 10),
    "neapolitan_major": _semis(0, 1, 3, 5, 7, 9, 11), "neapolitan_minor": _semis(0, 1, 3, 5, 7, 8, 11),
    "enigmatic": _semis(0, 1, 4, 6, 8, 10, 11), "persian": _semis(0, 1, 4, 5, 6, 8, 11),
    "spanish_8": _semis(0, 1, 3, 4, 5, 6, 8, 10),
    # pentatonic and hexatonic
    "major_pentatonic": _semis(0, 2, 4, 7, 9), "minor_pentatonic": _semis(0, 3, 5, 7, 10),
    "egyptian": _semis(0, 2, 5, 7, 10), "hirajoshi": _semis(0, 2, 3, 7, 8), "in_sen": _semis(0, 1, 5, 7, 10),
    "iwato": _semis(0, 1, 5, 6, 10), "kumoi": _semis(0, 2, 3, 7, 9), "yo": _semis(0, 2, 5, 7, 9),
    "blues": _semis(0, 3, 5, 6, 7, 10), "major_blues": _semis(0, 2, 3, 4, 7, 9),
    "prometheus": _semis(0, 2, 4, 6, 9, 10),
    # bebop
    "bebop_dominant": _semis(0, 2, 4, 5, 7, 9, 10, 11), "bebop_major": _semis(0, 2, 4, 5, 7, 8, 9, 11),
    "bebop_minor": _semis(0, 2, 3, 4, 5, 7, 9, 10),
    # symmetric
    "chromatic": _semis(*range(12)), "whole_tone": _semis(0, 2, 4, 6, 8, 10),
    "octatonic_hw": _semis(0, 1, 3, 4, 6, 7, 9, 10), "octatonic_wh": _semis(0, 2, 3, 5, 6, 8, 9, 11),
    "augmented": _semis(0, 3, 4, 7, 8, 11), "tritone": _semis(0, 1, 4, 6, 7, 10),
    "messiaen3": _semis(0, 2, 3, 4, 6, 7, 8, 10, 11), "messiaen4": _semis(0, 1, 2, 5, 6, 7, 8, 11),
    "messiaen5": _semis(0, 1, 5, 6, 7, 11), "messiaen6": _semis(0, 2, 4, 5, 6, 8, 10, 11),
    "messiaen7": _semis(0, 1, 2, 3, 5, 6, 7, 8, 9, 11),
    # maqamat (50 = a quarter-tone)
    "rast": [0, 200, 350, 500, 700, 900, 1050], "bayati": [0, 150, 300, 500, 700, 800, 1000],
    "saba": [0, 150, 300, 400, 700, 800, 1000], "hijaz": [0, 100, 400, 500, 700, 800, 1000],
    "nahawand": _semis(0, 2, 3, 5, 7, 8, 11), "kurd": _semis(0, 1, 3, 5, 7, 8, 10),
    # tunings
    "quarter_tone": [x * 50 for x in range(24)],
    "just_major": _ratios("1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"),
    "just_minor": _ratios("1", "9/8", "6/5", "4/3", "3/2", "8/5", "9/5"),
    "pythagorean": _ratios("1", "9/8", "81/64", "4/3", "3/2", "27/16", "243/128"),
    "harmonic_series": _ratios(*(f"{n}/8" for n in range(8, 16))),
    "slendro": [x * 240 for x in range(5)],
}

# Scales whose period is not the octave.
PERIODS: Dict[str, float] = {"bohlen_pierce": ratio_cents(3)}
SCALES["bohlen_pierce"] = [n * ratio_cents(3) / 13 for n in range(13)]

SCALE_ALIASES: Dict[str, str] = {
    "ionian": "major", "aeolian": "minor", "natural_minor": "minor", "ajam": "major",
    "mixolydian_b9_b13": "phrygian_dominant", "freygish": "phrygian_dominant", "spanish": "phrygian_dominant",
    "ukrainian_dorian": "dorian_#4", "romanian_minor": "dorian_#4", "lydian_#9": "lydian_#2",
    "jazz_minor": "melodic_minor", "acoustic": "lydian_dominant", "overtone": "lydian_dominant",
    "lydian_b7": "lydian_dominant", "super_locrian": "altered", "diminished_whole_tone": "altered",
    "half_diminished": "locrian_nat2", "aeolian_b5": "locrian_nat2", "byzantine": "double_harmonic",
    "arabic": "double_harmonic", "gypsy": "hungarian_minor", "pentatonic": "major_pentatonic",
    "whole": "whole_tone", "wholetone": "whole_tone", "diminished": "octatonic_wh", "octatonic": "octatonic_hw",
    "half_whole": "octatonic_hw", "whole_half": "octatonic_wh", "hexatonic": "augmented",
    "messiaen1": "whole_tone", "messiaen2": "octatonic_hw", "suspended_pentatonic": "egyptian",
    "maqam_rast": "rast", "maqam_bayati": "bayati", "maqam_saba": "saba", "maqam_hijaz": "hijaz",
    "maqam_nahawand": "nahawand", "maqam_kurd": "kurd", "24tet": "quarter_tone", "bp": "bohlen_pierce",
}

_EDO = re.compile(r"^(?:edo|tet)(\d+)$|^(\d+)(?:edo|tet)$")


def _key(name: str) -> str:
    return re.sub(r"[\s\-]+", "_", str(name).strip().lower())


def _lookup(name: Any, table: Dict[str, List[float]], aliases: Dict[str, str], what: str) -> Tuple[str, List[float]]:
    """A library entry by its name or an alias, ignoring case, spaces, - and _ (except for
    symbols where case matters, such as M7 and m7)."""
    raw = str(name).strip()
    if raw in aliases:
        return aliases[raw], table[aliases[raw]]
    squeeze = lambda k: _key(k).replace("_", "")  # noqa: E731
    key = squeeze(raw)
    names = {squeeze(k): k for k in table}
    names.update({squeeze(k): v for k, v in aliases.items() if squeeze(k) not in names})
    if key in names:
        return names[key], table[names[key]]
    m = _EDO.match(key) if what == "scale" else None
    if m and 1 <= int(m.group(1) or m.group(2)) <= 1200:
        n = int(m.group(1) or m.group(2))
        return f"edo{n}", [i * 1200 / n for i in range(n)]
    close = [k for k in table if key and key[:3] in squeeze(k)]
    hint = f" Close: {', '.join(close[:8])}." if close else ""
    raise PitchError(f'unknown {what} {raw!r}.{hint} Call with {what}="list" for every name.')


def chord_names() -> str:
    return ", ".join(CHORDS)


def scale_names() -> str:
    return ", ".join(SCALES) + ", edoN (N equal steps per octave: edo19, edo31 ...)"


def get_chord(root: Any, chord: str, inversion: int = 0) -> Pitches:
    """The chord built on `root` (or on each root of a list), in close position from the root;
    `inversion` n moves its n lowest notes up an octave."""
    _, steps = _lookup(chord, CHORDS, CHORD_ALIASES, "chord")
    n = int(_number(inversion, "inversion"))
    if n < 0:
        raise PitchError("inversion must be 0 or more (1 = first inversion)")

    def build(r: Any) -> List[float]:
        if isinstance(r, list):
            raise PitchError("root: one pitch, or a flat list of pitches")
        notes = [r + s for s in steps]
        for _ in range(n):
            notes = sorted(notes[1:] + [notes[0] + 1200])
        return notes

    roots = read_pitches(root)
    return [build(r) for r in roots] if isinstance(roots, list) else build(roots)


_DIRECTIONS = ("up", "down", "updown")


def get_scale(root: Any, scale: str, octaves: Any = 1, direction: str = "up") -> List[float]:
    """The scale from `root` up through `octaves` periods, ending on the root `octaves` periods
    higher; `direction` orders those notes: up, down (top to root) or updown (up, then back)."""
    name, steps = _lookup(scale, SCALES, SCALE_ALIASES, "scale")
    period = PERIODS.get(name, 1200.0)
    count = _number(octaves, "octaves")
    if count <= 0 or count != int(count):
        raise PitchError("octaves must be a whole number, 1 or more")
    direction = str(direction).strip().lower()
    if direction not in _DIRECTIONS:
        raise PitchError(f'direction must be one of {", ".join(_DIRECTIONS)}, got {direction!r}')
    r = to_cents(read_pitches(root) if not isinstance(root, list) else root[0], "root: ")
    notes = [r + o * period + s for o in range(int(count)) for s in steps] + [r + count * period]
    if direction == "down":
        return notes[::-1]
    if direction == "updown":
        return notes + notes[-2::-1]
    return notes


def scale_classes(scale: Any, root: Any = "C") -> Tuple[List[float], float]:
    """The pitch classes of a library scale on `root`, or of a list of pitches; and the period."""
    if isinstance(scale, str):
        try:
            name, steps = _lookup(scale, SCALES, SCALE_ALIASES, "scale")
        except PitchError as unknown:
            try:  # pitches, with or without octave: "C E G", "D4 F4 A4"
                return sorted({pitch_class(p) for p in re.split(r"[\s,\[\]\"']+", scale) if p}), 1200.0
            except PitchError:
                raise unknown from None
        else:
            period = PERIODS.get(name, 1200.0)
            base = pitch_class(root)
            return sorted({(base + s) % period for s in steps}), period
    classes = sorted({p % 1200 for p in _flat(read_pitches(scale))})
    if not classes:
        raise PitchError("scale: a scale name, or the pitches of the scale")
    return classes, 1200.0


def force_scale(pitches: Any, scale: Any, root: Any = "C") -> Pitches:
    """Every pitch moved to the nearest pitch of the scale; on a tie, the lower one."""
    classes, period = scale_classes(scale, root)

    def snap(p: float) -> float:
        base = math.floor(p / period) * period
        candidates = [base + o * period + c for o in (-1, 0, 1) for c in classes]
        return min(candidates, key=lambda c: (round(abs(c - p), 6), c))

    return _map(read_pitches(pitches), snap)


# ── Helpers ─────────────────────────────────────────────────────────────── #

def _number(value: Any, what: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise PitchError(f"{what} must be a number, got {value!r}") from None


def _ratio(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        return float(Fraction(str(value).strip()))
    except (ValueError, ZeroDivisionError):
        raise PitchError(f"{value!r} is not a number or a ratio such as \"5/4\"") from None


def _numbers(values: Any) -> Any:
    if isinstance(values, str):
        text = values.strip()
        if text.startswith("["):
            try:
                return _numbers(json.loads(text))
            except json.JSONDecodeError:
                pass
        parts = [p for p in re.split(r"[\s,\[\]]+", text) if p]
        return parts if len(parts) != 1 else parts[0]
    if isinstance(values, (list, tuple)):
        return [_numbers(v) for v in values]
    return values


__all__ = ["PitchError", "read_pitches", "tidy", "transpose", "reverse", "mirror", "p2mc", "mc2p",
           "get_midicents", "get_chord", "get_scale", "force_scale", "chord_names", "scale_names",
           "CHORDS", "SCALES"]
