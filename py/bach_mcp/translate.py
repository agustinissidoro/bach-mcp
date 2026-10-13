"""
translate.py
------------
Deterministic JSON <-> bach.roll llll translation. No LLM, no I/O.

The JSON score is bach.roll's gathered syntax with named fields: the same
hierarchy and the same units. Nothing is converted.

    bach.roll (gathered syntax)                JSON score
    ----------------------------------------   ------------------------------------------
    roll HEADER VOICE VOICE ...                {"voices": [VOICE, ...], "markers": [...]}
    header [clefs ..] [voicenames ..]          VOICE "clef", "name"
    header [markers [onset_ms name] ..]        "markers": [{"onset": ms, "name": "A"}]
    VOICE  [CHORD CHORD ... flag]              {"name": .., "chords": [CHORD, ...]}
    CHORD  [onset_ms NOTE NOTE ... flag]       {"onset": ms, "notes": [NOTE, ...]}
    NOTE   [cents dur_ms velocity ... flag]    {"pitch": midicents, "dur": ms, "vel": 1-127}
      [breakpoints [x cents slope] ..]           NOTE  "gliss"
      [slots [23 ..]]  notehead                  NOTE  "head"
      [slots [22 ..]]  articulations             CHORD "art"
      [slots [20 ..]]  dynamics                  CHORD "dyn"
      [slots [24 ..]]  annotation                CHORD "text"
      [slots [21 ..]]  lyrics                    CHORD "lyric"

Units, always:
    onset, dur   milliseconds
    pitch        midicents (6000 = middle C, 100 = one semitone)
    gliss        midicents relative to the note's pitch
    vel          1-127

The chord owns the onset and what is marked once for the whole chord
(articulation, dynamic, annotation, lyric). The note owns what sounds: pitch,
duration, velocity, glissando, notehead. A note has no onset of its own.

bach stores every slot on a note. The four chord-level ones are written on the
first note of the chord and read back from whichever note carries them.

Not mapped, on purpose (ignored when reading, left untouched when writing):
keys, midichannels, stafflines, numparts, loop, groups, commands, slotinfo,
custom articulation/notehead definitions, note and chord names, lock/mute/solo
flags, breakpoint velocities, the legacy [graphic] spec, slots 1-19 and 25-30.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_VELOCITY = 80
MAX_NOTES = 20000
MAX_CENTS = 12700

CLEFS = [
    "G", "F", "FG", "FGG", "FFG", "FFGG", "G8va", "G15ma", "G8vb", "G15mb",
    "F8va", "F15ma", "F8vb", "F15mb", "Soprano", "Mezzo", "Alto", "Tenor",
    "Barytone", "Percussion", "None",
]
_CLEF_ALIASES = {"treble": "G", "bass": "F", "piano": "FG", "grand": "FG", "baritone": "Barytone"}

# Velocity implied by a dynamic marking when a note gives no explicit "vel".
DYNAMIC_VELOCITY = {
    "ppppp": 8, "pppp": 15, "ppp": 25, "pp": 40, "p": 55, "mp": 70,
    "mf": 85, "f": 100, "ff": 112, "fff": 120, "ffff": 127, "fffff": 127,
    "sfz": 115, "sffz": 120, "sf": 110, "fz": 110, "rf": 105, "rfz": 105, "o": 1,
}

# (JSON name, bach name, other spellings accepted on input or found in a dump)
_ARTICULATION_TABLE = (
    ("staccato", "staccato", "stacc"),
    ("staccatissimo", "staccatissimo", "staccmo"),
    ("accent", "accent", "acc"),
    ("tenuto", "portato", "port por ten"),
    ("marcato", "martellato", "mart"),
    ("fermata", "fermata", "ferm corona"),
    ("trill", "trill", "tr"),
    ("trill#", "trill#", "tr#"),
    ("trillb", "trillb", "trb"),
    ("trillx", "trillx", "trx"),
    ("trillbb", "trillbb", "trbb"),
    ("tremolo", "tremolo3", "trem trem3"),
    ("tremolo2", "tremolo2", "trem2"),
    ("tremolo1", "tremolo1", "trem1"),
    ("upbow", "upbowing", "ubow"),
    ("downbow", "downbowing", "dbow"),
    ("harmonic", "harmonic", "harm"),
    ("gruppetto", "gruppetto", "grupp turn"),
    ("mordent", "upmordent", "umord mord"),
    ("downmordent", "downmordent", "dmord"),
    ("doublemordent", "doublemordent", "mmord"),
    ("lefthandpizzicato", "lefthandpizzicato", "lhpizz lhpiz"),
    ("accentstaccato", "accentstaccato", "accstacc staccatoaccent staccacc"),
    ("accenttenuto", "accentportato", "accport portatoaccent portacc poracc accpor"),
    ("tenutostaccato", "portatostaccato", "portstacc staccatoportato staccport porstacc staccpor"),
    ("marcatostaccato", "martellatostaccato", "martstacc staccatomartellato staccmart"),
)
ARTICULATIONS: Dict[str, str] = {}       # any accepted spelling -> bach name
_ARTICULATION_NAMES: Dict[str, str] = {}  # any bach spelling -> JSON name
for _json, _bach, _others in _ARTICULATION_TABLE:
    for _key in (_json, _bach, *_others.split()):
        ARTICULATIONS[_key] = _bach
        _ARTICULATION_NAMES[_key] = _json

NOTEHEADS = [
    "default", "doublewhole", "whole", "white", "black", "diamond", "cross", "plus",
    "none", "accent", "blacksquare", "whitesquare", "square", "blacktriangle",
    "whitetriangle", "triangle", "blackrhombus", "whiterhombus", "rhombus",
]
_NOTEHEAD_ALIASES = {
    "normal": "default", "half": "white", "quarter": "black", "x": "cross",
    "diam": "diamond", "harmonic": "diamond", "invisible": "none", "hidden": "none",
    "blacksq": "blacksquare", "bsquare": "blacksquare",
    "whitesq": "whitesquare", "wsquare": "whitesquare",
    "blacktri": "blacktriangle", "btri": "blacktriangle", "btriangle": "blacktriangle",
    "whitetri": "whitetriangle", "wtri": "whitetriangle", "wtriangle": "whitetriangle",
    "blackrh": "blackrhombus", "brhombus": "blackrhombus",
    "whiterh": "whiterhombus", "wrhombus": "whiterhombus",
}

# Slots that every new bach.roll links to notation by default.
SLOT_DYNAMICS, SLOT_LYRICS, SLOT_ARTICULATIONS, SLOT_NOTEHEAD, SLOT_ANNOTATION = 20, 21, 22, 23, 24
_SLOT_NAMES = {
    "dynamics": SLOT_DYNAMICS, "lyrics": SLOT_LYRICS, "articulations": SLOT_ARTICULATIONS,
    "notehead": SLOT_NOTEHEAD, "noteheads": SLOT_NOTEHEAD, "annotation": SLOT_ANNOTATION,
}

# Forgiving key aliases: small models drift between these spellings.
_CHORD_ALIASES = {
    "t": "onset", "time": "onset", "start": "onset", "onset_ms": "onset",
    "dynamic": "dyn", "dynamics": "dyn",
    "articulation": "art", "articulations": "art",
    "annotation": "text", "lyrics": "lyric",
}
_NOTE_ALIASES = {
    "cents": "pitch", "midicents": "pitch",
    "duration": "dur", "length": "dur", "duration_ms": "dur",
    "velocity": "vel",
    "glissando": "gliss", "breakpoints": "gliss",
    "notehead": "head",
}
_CHORD_KEYS = ("onset", "notes", "dyn", "art", "text", "lyric")
_NOTE_KEYS = ("pitch", "dur", "vel", "gliss", "head")


class ScoreError(ValueError):
    """A problem in the model's JSON, phrased so the model can fix it in one go."""


def _fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


def _tidy(x: float, digits: int = 3) -> Any:
    x = round(float(x), digits)
    return int(x) if x == int(x) else x


# ── JSON -> canonical score ──────────────────────────────────────────────── #

def _num(value: Any, what: str, where: str, minimum: Optional[float] = None) -> float:
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            pass
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoreError(f"{where}: \"{what}\" must be a number, got {value!r}")
    if minimum is not None and value < minimum:
        raise ScoreError(f"{where}: \"{what}\" must be >= {_fmt(minimum)}, got {value}")
    return float(value)


def _pitch(value: Any, where: str) -> float:
    try:
        cents = _num(value, "pitch", where)
    except ScoreError:
        raise ScoreError(
            f"{where}: invalid pitch {value!r}. Pitch is a number in midicents: "
            "6000 = middle C, 100 = one semitone"
        ) from None
    if 0 <= cents <= 127:
        raise ScoreError(
            f"{where}: pitch {_fmt(cents)} looks like a MIDI note number. Pitch is in midicents: "
            f"6000 = middle C, 100 = one semitone (MIDI {_fmt(cents)} is {_fmt(cents * 100)})"
        )
    if not 0 <= cents <= MAX_CENTS:
        raise ScoreError(f"{where}: pitch {_fmt(cents)} is out of range (midicents, 0-{MAX_CENTS}; 6000 = middle C)")
    return round(cents, 3)


# bach's plain dynamics syntax: markings, hairpins (< > << >> = _), the empty mark |,
# free words ("cresc", "sub."), positions 0..1 and breakpoint anchors (@1).
_DYN_HAIRPINS = ("<", ">", "<<", ">>", "=", "_")
_DYN_TOKEN = re.compile(r"<<|>>|[<>=_|]|@-?\d+|\d*\.\d+|\d+|[A-Za-z][A-Za-z.]*")
_DYN_WORD = re.compile(r"[A-Za-z][A-Za-z.]*|\|")


def _dynamic(value: Any, where: str) -> str:
    s = " ".join(str(value).split())
    if not s or _DYN_TOKEN.sub("", s).strip():
        raise ScoreError(
            f"{where}: invalid dynamic {value!r}. Use pp p mp mf f ff sfz, "
            "optionally followed by < (crescendo) or > (diminuendo), e.g. \"p<\""
        )
    return s


def dynamic_velocity(dyn: str) -> Optional[int]:
    """Velocity implied by the first marking of a dynamic, or None if it has none."""
    m = re.search(r"[A-Za-z]+", dyn)
    mark = m.group(0).lower() if m else ""
    if mark in DYNAMIC_VELOCITY:
        return DYNAMIC_VELOCITY[mark]
    if mark.startswith("sf"):
        return DYNAMIC_VELOCITY["sf"]
    lead = re.match(r"f+|p+", mark)  # "fp", "ffmp": the attack counts
    if lead and re.fullmatch(r"[fpm]+", mark):
        run = lead.group(0)
        return DYNAMIC_VELOCITY.get(run, 127 if run[0] == "f" else 8)
    return None


def _articulations(value: Any, where: str) -> List[str]:
    items = value if isinstance(value, (list, tuple)) else str(value).replace(",", " ").split()
    out = []
    for item in items:
        key = str(item).strip().lower()
        if key not in ARTICULATIONS:
            allowed = ("staccato staccatissimo accent tenuto marcato fermata trill tremolo "
                       "upbow downbow harmonic mordent gruppetto")
            raise ScoreError(f"{where}: unknown articulation {item!r}. Allowed: {allowed}")
        if ARTICULATIONS[key] not in out:
            out.append(ARTICULATIONS[key])
    return out


def _gliss(value: Any, where: str) -> List[Tuple[float, float, float]]:
    """Normalise gliss to bach breakpoints [(x, delta_cents, slope)] ending at x=1.

    A bare number is the interval reached at the end of the note, in midicents.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [(1.0, float(value), 0.0)]
    if isinstance(value, (list, tuple)) and value:
        points = []
        for p in value:
            if not (isinstance(p, (list, tuple)) and len(p) in (2, 3)):
                break
            slope = _num(p[2], "gliss slope", where) if len(p) == 3 else 0.0
            points.append((_num(p[0], "gliss position", where, 0.0),
                           _num(p[1], "gliss midicents", where),
                           max(-1.0, min(1.0, slope))))
        else:
            points.sort()
            if points[-1][0] != 1.0:
                raise ScoreError(f"{where}: the last gliss point must be at position 1 (the end of the note)")
            return [p for p in points if p[0] > 0]
    raise ScoreError(
        f"{where}: \"gliss\" must be a number of midicents (e.g. 200 or -1200) or a list of "
        "[position 0..1, midicents] points ending at position 1"
    )


def _clean_name(name: Any) -> str:
    return re.sub(r"[^\w#.+-]+", "_", str(name).strip()).strip("_")


def _clean_text(value: Any) -> str:
    """Free text for a text slot: drop what would break an llll or a Max message."""
    return " ".join(re.sub(r"[^\w .+\-#!?'/:%&*=<>~^]", " ", str(value)).split())


# Usual clef per instrument, matched on the voice name when no clef is given.
_INSTRUMENT_CLEFS = (
    ("FG", ("piano", "harp", "celesta", "organ", "harpsichord", "marimba", "accordion", "keyboard")),
    ("Alto", ("viola",)),
    ("F", ("cello", "violoncello", "bass", "bassoon", "trombone", "tuba", "timpani", "baritone")),
    ("Percussion", ("percussion", "drum", "cymbal", "woodblock")),
    ("G", ("violin", "flute", "piccolo", "oboe", "clarinet", "trumpet", "horn", "soprano",
           "alto", "vibraphone", "glockenspiel", "xylophone", "guitar")),
)


def clef_for_name(name: str) -> str:
    """Return the usual clef for an instrument name, or "" if the name is not recognised."""
    key = name.lower()
    for clef, words in _INSTRUMENT_CLEFS:
        if any(w in key for w in words):
            return clef
    return ""


def auto_clef(cents: List[float]) -> str:
    """Pick a clef from the pitch content so the model does not have to."""
    if not cents:
        return "G"
    lo, hi = min(cents), max(cents)
    if lo < 4800 and hi > 7200:
        return "FG"
    return "G" if sorted(cents)[len(cents) // 2] >= 5700 else "F"


def _keys(raw: Dict[str, Any], aliases: Dict[str, str], allowed: Tuple[str, ...],
          elsewhere: Tuple[str, ...], where: str, kind: str) -> Dict[str, Any]:
    """Apply key aliases and reject keys that do not belong at this level."""
    item = {aliases.get(k, k): v for k, v in raw.items()}
    for key in item:
        if key in allowed:
            continue
        if key in elsewhere:
            owner = "note" if kind == "chord" else "chord"
            place = "inside \"notes\"" if kind == "chord" else "next to \"onset\""
            raise ScoreError(f"{where}: \"{key}\" belongs to the {owner}, not to the {kind}. Put it {place}")
        raise ScoreError(f"{where}: unknown key \"{key}\". A {kind} has: {', '.join(allowed)}")
    return item


def _note(raw: Any, where: str) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ScoreError(f"{where}: must be an object like {{\"pitch\": 6000, \"dur\": 500}}")
    n = _keys(raw, _NOTE_ALIASES, _NOTE_KEYS, _CHORD_KEYS + tuple(_CHORD_ALIASES), where, "note")
    if n.get("pitch") is None:
        raise ScoreError(f"{where}: \"pitch\" is required, in midicents (6000 = middle C)")
    if n.get("dur") is None:
        raise ScoreError(f"{where}: \"dur\" is required: the duration in milliseconds")
    note: Dict[str, Any] = {"pitch": _pitch(n["pitch"], where)}
    note["dur"] = _num(n["dur"], "dur", where)
    if note["dur"] <= 0:
        raise ScoreError(f"{where}: \"dur\" must be > 0 (milliseconds), got {_fmt(note['dur'])}")
    # None = filled from the prevailing dynamic once the chords are in time order.
    note["vel"] = None if n.get("vel") is None else int(min(127, max(1, round(_num(n["vel"], "vel", where)))))
    if n.get("gliss") not in (None, 0, []):
        note["gliss"] = _gliss(n["gliss"], where)
    if n.get("head"):
        head = str(n["head"]).strip().lower()
        head = _NOTEHEAD_ALIASES.get(head, head)
        if head not in NOTEHEADS:
            raise ScoreError(f"{where}: unknown notehead {n['head']!r}. Allowed: {' '.join(NOTEHEADS)}")
        if head != "default":
            note["head"] = head
    return note


def _chord(raw: Any, where: str) -> Dict[str, Any]:
    example = "{\"onset\": 0, \"notes\": [{\"pitch\": 6000, \"dur\": 500}]}"
    if not isinstance(raw, dict):
        raise ScoreError(f"{where}: must be an object like {example}")
    c = _keys(raw, _CHORD_ALIASES, _CHORD_KEYS, _NOTE_KEYS + tuple(_NOTE_ALIASES), where, "chord")
    if c.get("onset") is None:
        raise ScoreError(f"{where}: \"onset\" is required: when the chord starts, in milliseconds")
    chord: Dict[str, Any] = {"onset": _num(c["onset"], "onset", where, 0.0)}
    if c.get("dyn"):
        chord["dyn"] = _dynamic(c["dyn"], where)
    if c.get("art"):
        chord["art"] = _articulations(c["art"], where)
    for key in ("text", "lyric"):
        if c.get(key) and _clean_text(c[key]):
            chord[key] = _clean_text(c[key])
    notes = c.get("notes")
    if not isinstance(notes, list) or not notes:
        raise ScoreError(f"{where}: \"notes\" must be a non-empty list, like {example}")
    chord["notes"] = [_note(n, f"{where}, note {ni}") for ni, n in enumerate(notes, start=1)]
    return chord


def normalize_score(score: Any) -> Dict[str, Any]:
    """Validate a JSON score and return it in canonical form.

    Canonical is the same structure, complete: chords in time order, every note
    with a velocity, every voice with a clef, articulations as bach names.
        {"voices": [{"name", "clef", "chords": [{"onset", "notes": [...], dyn?, art?, text?, lyric?}]}],
         "markers": [{"onset", "name"}]}
    """
    example = "{\"voices\": [{\"name\": \"Flute\", \"chords\": [{\"onset\": 0, \"notes\": [{\"pitch\": 6000, \"dur\": 500}]}]}]}"
    if isinstance(score, dict) and isinstance(score.get("score"), dict):
        score = score["score"]
    if not isinstance(score, dict):
        raise ScoreError(f"score must be a JSON object like {example}")
    voices_in = score.get("voices")
    if not isinstance(voices_in, list) or not voices_in:
        raise ScoreError(f"score needs \"voices\": a non-empty list, like {example}")

    total = 0
    voices = []
    for vi, v in enumerate(voices_in, start=1):
        if not isinstance(v, dict):
            raise ScoreError(f"voice {vi}: must be an object like {{\"name\": \"Flute\", \"chords\": [...]}}")
        if "chords" not in v and "notes" in v:
            raise ScoreError(
                f"voice {vi}: a voice holds \"chords\", and each chord holds its notes: "
                "{\"onset\": 0, \"notes\": [{\"pitch\": 6000, \"dur\": 500}]}"
            )
        name = _clean_name(v["name"]) if v.get("name") else ""
        clef = ""
        if v.get("clef"):
            given = str(v["clef"]).strip()
            clef = next((c for c in CLEFS if c.lower() == given.lower()), None) or _CLEF_ALIASES.get(given.lower())
            if not clef:
                raise ScoreError(f"voice {vi}: unknown clef {given!r}. Allowed: {' '.join(CLEFS)}")
        chords_in = v.get("chords", [])
        if not isinstance(chords_in, list):
            raise ScoreError(f"voice {vi}: \"chords\" must be a list")
        chords = [_chord(c, f"voice {vi}, chord {ci}") for ci, c in enumerate(chords_in, start=1)]
        chords.sort(key=lambda c: c["onset"])

        # A dynamic holds until the next one, so it also sets the velocity of the
        # notes that follow it.
        prevailing = DEFAULT_VELOCITY
        for chord in chords:
            implied = dynamic_velocity(chord["dyn"]) if "dyn" in chord else None
            if implied is not None:
                prevailing = implied
            for note in chord["notes"]:
                if note["vel"] is None:
                    note["vel"] = prevailing
            total += len(chord["notes"])
        if total > MAX_NOTES:
            raise ScoreError(f"score has more than {MAX_NOTES} notes")
        cents = [n["pitch"] for c in chords for n in c["notes"]]
        voices.append({"name": name, "clef": clef or clef_for_name(name) or auto_clef(cents), "chords": chords})

    markers = []
    markers_in = score.get("markers") or []
    if not isinstance(markers_in, list):
        raise ScoreError("\"markers\" must be a list like [{\"onset\": 0, \"name\": \"A\"}]")
    for mi, m in enumerate(markers_in, start=1):
        if not isinstance(m, dict):
            raise ScoreError(f"marker {mi}: must be an object like {{\"onset\": 0, \"name\": \"A\"}}")
        m = {_CHORD_ALIASES.get(k, k): val for k, val in m.items()}
        if m.get("onset") is None:
            raise ScoreError(f"marker {mi}: \"onset\" is required, in milliseconds")
        markers.append({"onset": _num(m["onset"], "onset", f"marker {mi}", 0.0),
                        "name": _clean_name(m.get("name", m.get("label", "")))})
    markers.sort(key=lambda m: m["onset"])
    return {"voices": voices, "markers": markers}


# ── Canonical score -> llll ──────────────────────────────────────────────── #

def _note_llll(note: Dict[str, Any], chord: Optional[Dict[str, Any]]) -> str:
    """One note in gathered syntax. `chord` is given for the note that carries the chord's slots."""
    parts = [_fmt(note["pitch"]), _fmt(note["dur"]), str(note["vel"])]
    if note.get("gliss"):
        points = " ".join(f"[{_fmt(x)} {_fmt(d)} {_fmt(s)}]" for x, d, s in note["gliss"])
        parts.append(f"[breakpoints [0 0 0] {points}]")
    chord = chord or {}
    slots = []
    if chord.get("dyn"):
        slots.append(f"[{SLOT_DYNAMICS} {chord['dyn']}]")
    if chord.get("lyric"):
        slots.append(f"[{SLOT_LYRICS} {chord['lyric']}]")
    if chord.get("art"):
        slots.append(f"[{SLOT_ARTICULATIONS} {' '.join(chord['art'])}]")
    if note.get("head"):
        slots.append(f"[{SLOT_NOTEHEAD} {note['head']}]")
    if chord.get("text"):
        slots.append(f"[{SLOT_ANNOTATION} {chord['text']}]")
    if slots:
        parts.append(f"[slots {' '.join(slots)}]")
    return f"[{' '.join(parts)}]"


def _chord_llll(chord: Dict[str, Any]) -> str:
    notes = " ".join(_note_llll(n, chord if i == 0 else None) for i, n in enumerate(chord["notes"]))
    return f"[{_fmt(chord['onset'])} {notes}]"


def _body_llll(score: Dict[str, Any]) -> List[str]:
    voices = []
    for v in score["voices"]:
        chords = " ".join(_chord_llll(c) for c in v["chords"])
        voices.append(f"[{chords}]" if chords else "[]")
    return voices


def score_to_llll(score: Dict[str, Any], with_header: bool = True) -> str:
    """Encode a canonical score as a full `roll ...` message (replaces the score).

    The header always states clefs, voice names and markers, so nothing of the
    previous score survives: an unnamed voice clears its old name, and an empty
    [markers] clears the old markers.
    """
    parts = ["roll"]
    if with_header:
        parts.append(f"[clefs {' '.join(v['clef'] for v in score['voices'])}]")
        parts.append(f"[voicenames {' '.join(v['name'] or 'nil' for v in score['voices'])}]")
        markers = [f"[{_fmt(m['onset'])} {m['name'] or 'nil'}]" for m in score.get("markers", [])]
        parts.append(f"[markers {' '.join(markers)}]" if markers else "[markers]")
    return " ".join(parts + _body_llll(score))


def score_to_addchords(score: Dict[str, Any]) -> str:
    """Encode a canonical score as an `addchords ...` message (adds to the score)."""
    return "addchords " + " ".join(_body_llll(score))


def required_tonedivision(score: Dict[str, Any]) -> int:
    """The bach `tonedivision` needed to show the score's pitches: 2 semitones, 4 quarter-tones, 8 finer."""
    need = 2
    for v in score["voices"]:
        for c in v["chords"]:
            for n in c["notes"]:
                rest = round(n["pitch"] % 100.0, 3)
                if rest == 50:
                    need = max(need, 4)
                elif rest:
                    return 8
    return need


def score_messages(score: Dict[str, Any], add: bool = False) -> List[str]:
    """Every message to send to bach.roll for this score, in order."""
    messages = []
    division = required_tonedivision(score)
    if division > 2:  # must precede the notes, or bach cannot draw the microtones
        messages.append(f"tonedivision {division}")
    if not add:
        return messages + [score_to_llll(score)]
    if any(v["chords"] for v in score["voices"]):
        messages.append(score_to_addchords(score))
    for m in score.get("markers", []):
        messages.append(f"addmarker {_fmt(m['onset'])} {m['name']}".rstrip())
    return messages


# ── llll -> JSON ─────────────────────────────────────────────────────────── #

_TOKEN = re.compile(r'"[^"]*"|[\[\]()]|[^\s\[\]()]+')
# A note bach holds as a pitch name rather than midicents, e.g. Db5 or C5+1/16t.
# bach's octave numbers put middle C at C5.
_BACH_PITCH = re.compile(r"^([A-Ga-g])([#bxqd^v]*)(-?\d+)(?:([+-])(\d+)/(\d+)t)?$")
_PITCH_CLASS = {"C": 0, "D": 200, "E": 400, "F": 500, "G": 700, "A": 900, "B": 1100}
_ACCIDENTAL = {"#": 100, "b": -100, "x": 200, "q": 50, "d": -50, "^": 25, "v": -25}


def bach_pitch_to_cents(token: str) -> Optional[float]:
    """Midicents of a bach pitch name as it may appear in a dump (C5 = middle C = 6000)."""
    m = _BACH_PITCH.match(token)
    if not m:
        return None
    letter, accs, octave, sign, num, den = m.groups()
    cents = int(octave) * 1200 + _PITCH_CLASS[letter.upper()] + sum(_ACCIDENTAL[a] for a in accs)
    if sign:
        cents += (1 if sign == "+" else -1) * 200.0 * int(num) / int(den)
    return float(cents)


def _atom(token: str) -> Any:
    if token.startswith('"'):
        return token.strip('"')
    if token.startswith("`"):  # bach's text format escapes symbols that look like numbers or pitches
        return token[1:]
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    if re.fullmatch(r"-?\d+/\d+", token):
        return float(Fraction(token))
    return token


def parse_llll(text: str) -> List[Any]:
    """Parse llll text into nested Python lists. Accepts both [ ] and ( ) brackets."""
    root: List[Any] = []
    stack = [root]
    for token in _TOKEN.findall(text):
        if token in "[(":
            new: List[Any] = []
            stack[-1].append(new)
            stack.append(new)
        elif token in "])":
            if len(stack) == 1:
                raise ValueError("unbalanced llll: unexpected closing bracket")
            stack.pop()
        else:
            stack[-1].append(_atom(token))
    if len(stack) != 1:
        raise ValueError("unbalanced llll: missing closing bracket (truncated message?)")
    return root


def _flatten_symbols(items: List[Any]) -> List[str]:
    out: List[str] = []
    for item in items:
        if isinstance(item, list):
            out.extend(_flatten_symbols(item))
        elif item not in ("nil", "null"):
            out.append(str(item))
    return out


def _plain_dynamics(tokens: List[str]) -> str:
    """Join plain-syntax tokens, without spaces when that stays unambiguous ("p<", "f<fff>mp")."""
    spaced = any(not (_DYN_WORD.fullmatch(t) or t in _DYN_HAIRPINS) for t in tokens)
    spaced = spaced or any(_DYN_WORD.fullmatch(a) and _DYN_WORD.fullmatch(b) for a, b in zip(tokens, tokens[1:]))
    return (" " if spaced else "").join(tokens)


def _dynamics_from_slot(content: List[Any]) -> str:
    """Turn the content of a dynamics slot into bach's plain syntax, e.g. "p<" or "f<fff>mp".

    bach outputs one of three forms (attribute dynamicsoutputmode; 2 is the default):
        0 plain       p < fff
        1 structured  [auto p <] [auto fff =]
        2 full        [[auto 0 0.] p <] [[auto 0 1.] fff =]
    """
    if not (content and all(isinstance(item, list) for item in content)):
        return _plain_dynamics(_flatten_symbols(content))
    tokens: List[str] = []
    items = [item for item in content if item]
    for index, item in enumerate(items):
        attach = item[0]
        marking = item[1] if len(item) > 1 else []
        hairpin = str(item[2]) if len(item) > 2 else "="
        prefix = ""
        if isinstance(attach, (int, float)):
            prefix = _fmt(float(attach))
        elif isinstance(attach, list) and attach and attach[0] == "breakpoint" and len(attach) > 1:
            prefix = f"@{attach[1]}"
        elif isinstance(attach, list) and attach and attach[0] == "manual":
            prefix = _fmt(float(attach[-1]))
        words = _flatten_symbols(marking if isinstance(marking, list) else [marking])
        if prefix:
            tokens.append(prefix)
        tokens.extend(words or ([] if prefix else ["|"]))
        if hairpin != "=" or index < len(items) - 1:
            tokens.append(hairpin)
    return _plain_dynamics(tokens)


def _gliss_from_breakpoints(points: List[Any]) -> Any:
    """Breakpoints [x cents slope] -> "gliss": a number of midicents, or [[x, cents(, slope)]]."""
    points = [p for p in points if isinstance(p, list) and len(p) >= 2 and p[0] > 0]
    if not any(p[1] != 0 for p in points):
        return None
    slope = lambda p: p[2] if len(p) > 2 and isinstance(p[2], (int, float)) else 0  # noqa: E731
    if len(points) == 1 and not slope(points[0]):
        return _tidy(points[0][1])
    return [[_tidy(p[0], 4), _tidy(p[1])] + ([_tidy(slope(p), 4)] if slope(p) else []) for p in points]


def _decode_chord(chord: List[Any]) -> Optional[Dict[str, Any]]:
    """Decode one gathered-syntax chord [onset NOTE NOTE ... flag] into a JSON chord."""
    marks: Dict[str, Any] = {}
    arts: List[str] = []
    notes = []
    for item in chord[1:]:
        if not isinstance(item, list) or len(item) < 3:
            continue
        raw_pitch, dur, vel = item[0], item[1], item[2]
        if not (isinstance(dur, (int, float)) and isinstance(vel, (int, float))):
            continue  # a chord spec such as [name john paul], not a note
        cents = raw_pitch if isinstance(raw_pitch, (int, float)) else bach_pitch_to_cents(str(raw_pitch))
        if cents is None:
            continue
        note: Dict[str, Any] = {"pitch": _tidy(cents), "dur": _tidy(dur), "vel": int(vel)}
        for spec in item[3:]:
            if not isinstance(spec, list) or not spec:
                continue
            if spec[0] == "breakpoints":
                gliss = _gliss_from_breakpoints(spec[1:])
                if gliss is not None:
                    note["gliss"] = gliss
            elif spec[0] == "slots":
                for slot in spec[1:]:
                    if not isinstance(slot, list) or len(slot) < 2:
                        continue
                    sid, content = _SLOT_NAMES.get(slot[0], slot[0]), slot[1:]
                    if sid == SLOT_NOTEHEAD:
                        head = _flatten_symbols(content)
                        if head and head[0] != "default":
                            note["head"] = _NOTEHEAD_ALIASES.get(head[0], head[0])
                    elif sid == SLOT_ARTICULATIONS:
                        for art in _flatten_symbols(content):
                            art = _ARTICULATION_NAMES.get(art, art)
                            if art not in arts:
                                arts.append(art)
                    elif sid == SLOT_DYNAMICS:
                        marks.setdefault("dyn", _dynamics_from_slot(content))
                    elif sid in (SLOT_ANNOTATION, SLOT_LYRICS):
                        marks.setdefault("text" if sid == SLOT_ANNOTATION else "lyric",
                                         " ".join(_flatten_symbols(content)))
        notes.append(note)
    if not notes:
        return None
    out: Dict[str, Any] = {"onset": _tidy(chord[0])}
    if marks.get("dyn"):
        out["dyn"] = marks["dyn"]
    if arts:
        out["art"] = arts[0] if len(arts) == 1 else arts
    out.update({k: marks[k] for k in ("text", "lyric") if marks.get(k)})
    out["notes"] = notes
    return out


def llll_to_score(text: str) -> Dict[str, Any]:
    """Decode a bach.roll dump (gathered syntax) into a JSON score."""
    items = parse_llll(text)
    if items and items[0] == "roll":
        items = items[1:]

    header: Dict[str, List[Any]] = {}
    voices_raw: List[List[Any]] = []
    for item in items:
        if not isinstance(item, list):
            continue
        if item and isinstance(item[0], str):
            header[item[0]] = item[1:]
        else:
            voices_raw.append(item)

    clefs = header.get("clefs", [])
    names = header.get("voicenames", [])
    voices = []
    for vi, voice in enumerate(voices_raw):
        v: Dict[str, Any] = {"voice": vi + 1}
        if vi < len(names) and names[vi] not in ("nil", "null", [], None):
            name = names[vi]
            v["name"] = " ".join(map(str, name)) if isinstance(name, list) else str(name)
        if vi < len(clefs):
            v["clef"] = str(clefs[vi])
        v["chords"] = []
        for chord in voice:
            if isinstance(chord, list) and chord and isinstance(chord[0], (int, float)):
                decoded = _decode_chord(chord)
                if decoded:
                    v["chords"].append(decoded)
        voices.append(v)

    score: Dict[str, Any] = {"voices": voices}
    markers = []
    for marker in header.get("markers", []):
        if isinstance(marker, list) and marker and isinstance(marker[0], (int, float)):
            markers.append({"onset": _tidy(marker[0]), "name": " ".join(_flatten_symbols(marker[1:2]))})
    if markers:
        score["markers"] = markers
    return score


# ── Summaries (what the model gets back instead of a dump) ───────────────── #

def count_notes(score: Dict[str, Any]) -> int:
    """Count the notes of a score (canonical or as decoded from a dump)."""
    return sum(len(c["notes"]) for v in score["voices"] for c in v.get("chords", []))


def summarize(score: Dict[str, Any], preview: int = 8) -> str:
    """One compact line per voice describing a canonical score, in bach's units."""
    lines = []
    for vi, v in enumerate(score["voices"], start=1):
        chords = v["chords"]
        label = f"voice {vi}" + (f" ({v['name']})" if v["name"] else "") + f" clef {v['clef']}"
        if not chords:
            lines.append(f"{label}: empty")
            continue
        cents = [n["pitch"] for c in chords for n in c["notes"]]
        end = max(c["onset"] + max(n["dur"] for n in c["notes"]) for c in chords)
        shown = [f"{'+'.join(_fmt(n['pitch']) for n in c['notes'])}@{_fmt(c['onset'])}" for c in chords[:preview]]
        more = f" ... +{len(chords) - preview} more" if len(chords) > preview else ""
        lines.append(
            f"{label}: {len(cents)} notes in {len(chords)} chords, {_fmt(chords[0]['onset'])}-{_fmt(end)} ms, "
            f"pitch {_fmt(min(cents))}-{_fmt(max(cents))}. Starts (pitch@onset): {' '.join(shown)}{more}"
        )
    if score.get("markers"):
        lines.append("markers: " + " ".join(f"{m['name']}@{_fmt(m['onset'])}" for m in score["markers"]))
    return "\n".join(lines)
