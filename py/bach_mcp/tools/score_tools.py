"""
score_tools.py
--------------
The score tools: write_score, write_markers, read_score, clear_score.

The model reads and writes scores in bachjson-complete, the syntax every other
part uses (bachjson-syntax-specification.md): voices > chords > notes as
objects, slots by number, markers in the header. read_score asks the server
patch for buffer.json and shows it through music/reader.py, which only leaves
out what says nothing (most of the header, "flag": 0, empty keys). write_score
puts what the model wrote onto the roll's score: a header element the model
gives replaces the roll's, and every one it does not give (slotinfo, clefs,
keys ...) is kept.

Markers with a role (timesig, barline, division, subdivision, tempo) are the
measures bach.quantize reads. write_score and write_markers check them with
music/markers.py: what bach would drop or misread is refused, and the answer
says the measures they make. write_markers changes the markers alone, so a
score's notes need not be sent again to give it measures.

Each call is for one instance (session.py: the one whose prompt is being
answered, else the active one). Scores travel through files (buffer.py), never
as messages: write_score writes the complete score to the instance's own file
in the playground, scores/<name>.json, and sends `<name> score_done`. Only a
score instance writes notes; any instance can have its roll read.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP

from ..bridge.buffer import RollBuffer, ServerBuffer
from ..bridge.max import MaxBridge
from ..bridge.protocol import line
from ..music import markers as grid
from ..music.reader import count_notes, describe, read_view
from .session import NoTarget, Target, conversation, target

SCORE_TOOLS = ("write_score", "write_markers", "read_score", "clear_score")
MAX_NOTES = 20000


def close_brackets(text: str) -> Optional[Any]:
    """A score whose only fault is the closing brackets at its very end, read with the right ones.

    The model sometimes closes a JSON score in the wrong order (`]] }]}]` instead of `]]]}]}`).
    If everything after the last value is only brackets, braces and spaces, that ending carries no
    music: it is dropped and written again from the brackets actually open. Anything else is left
    alone (None), so nothing is ever guessed."""
    body = text.rstrip()
    end = len(body)
    while end and body[end - 1] in "]} \t\r\n":
        end -= 1
    head = body[:end]
    stack, in_string, escaped = [], False, False
    for ch in head:
        if in_string:
            escaped = not escaped and ch == "\\"
            if ch == '"' and not escaped:
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[{":
            stack.append(ch)
        elif ch in "]}":
            if not stack or {"]": "[", "}": "{"}[ch] != stack.pop():
                return None  # a wrong bracket in the middle: not just the ending
    if in_string or not stack:
        return None
    closing = "".join({"[": "]", "{": "}"}[b] for b in reversed(stack))
    try:
        return json.loads(head + closing)
    except json.JSONDecodeError:
        return None


def json_error(text: str, exc: json.JSONDecodeError) -> str:
    """Where a JSON text breaks, in words the model can act on: what is wrong, and the text around it."""
    what = {"Expecting ',' delimiter": "a comma is missing", "Expecting value": "a value is missing",
            "Expecting property name enclosed in double quotes": "a key is missing or not in double quotes",
            "Extra data": "there is text after the end of the score",
            "Unterminated string starting at": "a text is not closed with a double quote"}.get(exc.msg, exc.msg.lower())
    before, after = text[max(0, exc.pos - 40):exc.pos], text[exc.pos:exc.pos + 25]
    return f"the score is not valid JSON: {what} at character {exc.pos}, here: ...{before}<HERE>{after}..."


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


EXAMPLE = '{"voices": [{"chords": [{"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "vel": 80}]}]}]}'

SCORE_KEYS = ("header", "voices")
VOICE_KEYS = ("chords", "flag")
CHORD_KEYS = ("onset", "notes", "name", "flag")
NOTE_KEYS = ("pitch", "spelling", "dur", "vel", "graphic", "breakpoints", "slots", "articulations", "name", "flag")
MARKER_KEYS = ("onset", "name", "role", "content")
MARKER_ROLES = grid.ROLES
# bach.roll's linked slots: where a mark written as a note field belongs.
MARK_SLOTS = {"dynamics": "20", "lyrics": "21", "articulation": "22", "notehead": "23", "annotation": "24"}


def _unknown(item: Dict[str, Any], known: tuple, what: str) -> Optional[str]:
    """A key the syntax does not have, which would be dropped without a word; None if there is none."""
    for key in item:
        if key in known:
            continue
        if what == "note" and key in MARK_SLOTS:
            return (f'"{key}" is not a note field: marks go in "slots", by slot number, each a list, '
                    f'e.g. "slots": {{"{MARK_SLOTS[key]}": [...]}}')
        return f'"{key}" is not a {what} field (a {what} has: {", ".join(known)})'
    return None


def check_markers(markers: Any) -> Optional[str]:
    """What is wrong with header.markers, said where it is; None if they can be written."""
    if not isinstance(markers, list):
        return '"markers" is a list of markers, each {"onset": 0, "name": ["A"], "role": "none"}'
    for mi, m in enumerate(markers, 1):
        where = f"marker {mi}"
        if not isinstance(m, dict) or not _is_number(m.get("onset")):
            return f'{where}: a marker is an object with its "onset" in ms, like {{"onset": 0, "name": ["A"], "role": "none"}}'
        problem = _unknown(m, MARKER_KEYS, "marker")
        if problem:
            return f"{where}: {problem}"
        if m.get("role", "none") not in MARKER_ROLES:
            return f'{where}: role "{m.get("role")}" does not exist (roles: {", ".join(MARKER_ROLES)})'
        if "content" in m and not isinstance(m["content"], list):
            return f'{where}: "content" is a list, e.g. [4, 4] for a time signature'
    errors, _ = grid.check(markers)
    return errors[0] if errors else None


def marker(m: Dict[str, Any]) -> Dict[str, Any]:
    """A checked marker written whole: its name a list, its role, no empty content."""
    out = {"onset": m["onset"], "name": _names(m.get("name")), "role": m.get("role", "none")}
    if m.get("content") not in (None, []):
        out["content"] = m["content"]
    return out


def measures_note(markers: List[Dict[str, Any]]) -> str:
    """What the markers mean to bach.quantize and what may not be meant, as lines to end an answer with."""
    _, warnings = grid.check(markers)
    lines = [grid.report(markers)] + [f"WARNING: {w}" for w in warnings]
    return "".join(f"\n{line}" for line in lines if line)


def check_score(score: Any) -> Optional[str]:
    """What is wrong with a score the model wrote, said where it is; None if it can be written."""
    if not isinstance(score, dict) or not isinstance(score.get("voices"), list) or not score["voices"]:
        return f'the score needs "voices": a non-empty list, like {EXAMPLE}'
    problem = _unknown(score, SCORE_KEYS, "score")
    if problem:
        return problem
    header = score.get("header", {})
    if not isinstance(header, dict):
        return '"header" is an object, e.g. {"voicenames": [["Flute"]]}'
    if "voicenames" in header and not isinstance(header["voicenames"], list):
        return '"voicenames" is a list with one entry per voice, e.g. [["Flute"], ["Cello"]]'
    if "markers" in header:
        problem = check_markers(header["markers"])
        if problem:
            return problem
    for vi, v in enumerate(score["voices"], 1):
        if not isinstance(v, dict) or not isinstance(v.get("chords", []), list):
            return f'voice {vi}: a voice is an object like {{"chords": [...]}}'
        problem = _unknown(v, VOICE_KEYS, "voice")
        if problem:
            hint = ' (a voice\'s name goes in the header: "voicenames": [["Flute"], ...])' if "name" in v else ""
            return f"voice {vi}: {problem}{hint}"
        for ci, c in enumerate(v.get("chords", []), 1):
            where = f"voice {vi}, chord {ci}"
            if not isinstance(c, dict) or not _is_number(c.get("onset")):
                return (f'{where}: a chord is an object with its "onset" in ms and its "notes", '
                        f'e.g. {{"onset": 0, "notes": [{{"pitch": 6000, "dur": 500, "vel": 80}}]}}')
            problem = _unknown(c, CHORD_KEYS, "chord")
            if problem:
                return f"{where}: {problem}"
            if not isinstance(c.get("notes"), list) or not c["notes"]:
                return f'{where}: a chord needs at least one note in "notes", e.g. [{{"pitch": 6000, "dur": 500, "vel": 80}}]'
            for ni, n in enumerate(c["notes"], 1):
                here = f"{where}, note {ni}"
                if not isinstance(n, dict) or not all(_is_number(n.get(k)) for k in ("pitch", "dur", "vel")):
                    return f'{here}: a note is an object with "pitch", "dur" and "vel" (numbers), e.g. {{"pitch": 6000, "dur": 500, "vel": 80}}'
                problem = _unknown(n, NOTE_KEYS, "note")
                if problem:
                    return f"{here}: {problem}"
                if 0 <= n["pitch"] <= 127:
                    return (f"{here}: pitch {n['pitch']} looks like a MIDI note number; "
                            f"pitch is in midicents (6000 = middle C, MIDI {n['pitch']} is {n['pitch'] * 100})")
                if n["dur"] <= 0:
                    return f"{here}: dur must be > 0 (milliseconds)"
                slots = n.get("slots", {})
                if not isinstance(slots, dict) or not all(isinstance(items, list) for items in slots.values()):
                    return f'{here}: "slots" is an object by slot number, each slot a list, e.g. {{"20": ["p"]}}'
                for key in ("breakpoints", "articulations"):
                    if key in n and not isinstance(n[key], list):
                        return f'{here}: "{key}" is a list'
    return None


def _names(value: Any) -> List[Any]:
    """The names of a voice or a marker as the list they are: "Flute" -> ["Flute"], nothing -> []."""
    if value in (None, "", []):
        return []
    return value if isinstance(value, list) else [value]


def complete(score: Dict[str, Any]) -> Dict[str, Any]:
    """A checked score with what the model may leave out written in: every flag, a marker's name
    and role, names as lists. What is stored and passed on is always the whole syntax."""
    out = json.loads(json.dumps(score))
    header = out.setdefault("header", {})
    if "voicenames" in header:
        header["voicenames"] = [_names(n) for n in header["voicenames"]]
    if "markers" in header:
        header["markers"] = grid.ordered([marker(m) for m in header["markers"]])
    for v in out["voices"]:
        v.setdefault("chords", [])
        v.setdefault("flag", 0)
        for c in v["chords"]:
            if "name" in c:
                c["name"] = _names(c["name"])
            c.setdefault("flag", 0)
            for n in c["notes"]:
                if "name" in n:
                    n["name"] = _names(n["name"])
                n.setdefault("flag", 0)
    return out


def onto(written: Dict[str, Any], current: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The written score on the roll's: its voices, and the roll's header with every element the
    written header gives in place of the roll's. slotinfo and commands are joined slot by slot and
    field by field, so a slot described by its name alone keeps the rest of its definition."""
    header = json.loads(json.dumps((current or {}).get("header") or {}))
    for key, value in (written.get("header") or {}).items():
        if isinstance(value, dict) and isinstance(header.get(key), dict):
            for number, fields in value.items():
                if isinstance(fields, dict) and isinstance(header[key].get(number), dict):
                    header[key][number].update(fields)
                else:
                    header[key][number] = fields
        else:
            header[key] = value
    return {"header": header, "voices": written["voices"]}


def tonedivision(score: Dict[str, Any]) -> int:
    """The bach tonedivision the score's pitches need: 2 semitones, 4 quarter-tones, 8 finer."""
    need = 2
    for v in score.get("voices") or []:
        for c in v.get("chords") or []:
            for n in c.get("notes") or []:
                rest = round(n["pitch"] % 100, 3)
                if rest == 50:
                    need = 4
                elif rest:
                    return 8
    return need


def add_chords(base: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """`new`'s chords added to `base`'s, voice by voice, in time order; voices base lacks are added.
    Its markers are added to base's too, in time order; any other header element it gives replaces base's."""
    out = json.loads(json.dumps(base))
    given = {k: v for k, v in (new.get("header") or {}).items() if k not in ("voicenames", "markers")}
    out["header"] = onto({"header": given, "voices": []}, out)["header"]
    if (new.get("header") or {}).get("markers"):
        out["header"]["markers"] = grid.ordered((out["header"].get("markers") or []) + new["header"]["markers"])
    voices: List[Dict[str, Any]] = out.setdefault("voices", [])
    names = out.setdefault("header", {}).setdefault("voicenames", [[] for _ in voices])
    new_names = (new.get("header") or {}).get("voicenames") or []
    for i, v in enumerate(new.get("voices") or []):
        if i < len(voices):
            voices[i]["chords"] = sorted(voices[i].get("chords", []) + v.get("chords", []), key=lambda c: c["onset"])
        else:
            voices.append(v)
            while len(names) < i:
                names.append([])
            names.append(new_names[i] if i < len(new_names) else [])
    return out


def _writer() -> Target:
    """The instance being served, if it is a score instance; else NoTarget saying what it takes instead."""
    t = target()
    if t.type in ("synth", "fx"):
        raise NoTarget(f"{t.name} is a {t.type}: it takes gen~ code (send_gen), not notes")
    if t.type != "score":
        raise NoTarget(f"{t.name} is a {t.type}: it takes an algorithm (send_algorithm), not notes")
    return t


def register_score_tools(mcp: FastMCP, bridge: MaxBridge) -> None:
    """Register the JSON score tools on `mcp`. Scores travel through each instance's file, signals through `bridge`."""
    state: Dict[str, Any] = {"last_read": None}

    def _send_score(raw: Any, add: bool) -> str:
        try:
            t = _writer()
        except NoTarget as exc:
            return f"ERROR: {exc}. Nothing was written."
        if isinstance(raw, str):  # the score arrived as text: read it, or say exactly where it breaks
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as exc:
                repaired = close_brackets(raw)
                if repaired is None:
                    return f"ERROR: {json_error(raw, exc)}. Nothing was written. Fix this spot and call the tool again."
                raw = repaired
        problem = check_score(raw)
        if problem:
            return f"ERROR: {problem}. Nothing was written. Fix this and call the tool again."
        current = ServerBuffer(bridge).fetch(timeout_seconds=3.0)  # read like read_score; its header is kept (and, with add, its notes)
        if add and current is None:
            return "ERROR: Max did not hand over the current score (is the patch open?). Nothing was added."
        written = complete(raw)
        if add:
            score = add_chords(current, written)
        else:
            score = onto(written, current)
            names = score["header"].get("voicenames")
            if names is not None:  # one entry per voice written: the roll may have had more voices, or fewer
                score["header"]["voicenames"] = (names + [[] for _ in score["voices"]])[:len(score["voices"])]
        if count_notes(score) > MAX_NOTES:
            return f"ERROR: more than {MAX_NOTES} notes. Nothing was written."
        markers = score["header"].get("markers") or []
        if add and written["header"].get("markers"):  # together with the roll's own
            problem = check_markers(markers)
            if problem:
                return f"ERROR: with the markers already in the roll, {problem}. Nothing was added."
        if not RollBuffer(bridge, t.name, t.roll_file).load(score, tonedivision(score)):
            return "ERROR: could not reach Max. Is the patch open?"
        state["last_read"] = None
        status = "Added to the score" if add else "Score written"
        return (f"OK. {status}.\n{describe(score)}{measures_note(markers)}\n"
                "This is the exact content. Do not call read_score to check it.")

    @mcp.tool()
    def write_score(score: Union[Dict[str, Any], str], add: bool = False) -> str:
        """Write music to the score. Decide the generating principle first, then send the
        complete score in one call.

        score = {"header": {"voicenames": [["Flute"], ...]}, "voices": [{"chords": [CHORD, ...]}, ...]}
        CHORD = {"onset": 0, "notes": [NOTE, ...]}     onset in milliseconds; a single note is a chord with one note.
        NOTE  = {"pitch": 6000, "dur": 500, "vel": 80}  pitch in midicents (6000 = middle C), copied from the
                pitch tools; dur in milliseconds; vel loudness 1-127.
                Only when needed: "slots" by slot number, each a list ({"20": ["p<"], "22": ["staccato"]}),
                "breakpoints" for a glissando ([[0, 0, 0], [1, 200, 0]]).
        One entry in "voices" per instrument, top staff first, its name at the same place in
        header "voicenames". Silence is a gap between onsets.
        Optional header "markers": [{"onset": 0, "name": ["A"], "role": "none"}, ...]. To change only
        the markers of a score, use write_markers.
        A header element you give replaces the roll's; what you leave out stays as it is.

        add: False replaces the notes, True adds these chords (and markers) to them.
        The result lists what was written.
        """
        return _send_score(score, add=add)

    @mcp.tool()
    def write_markers(markers: Union[List[Dict[str, Any]], str], add: bool = False) -> str:
        """Write the markers of the score, leaving its notes as they are.

        markers = [{"onset": 0, "name": [], "role": "timesig", "content": [4, 4]},
                   {"onset": 2000, "name": [], "role": "barline"}, ...]
        onset in milliseconds. role: "none" (a label: give it a name, e.g. ["A"]), or what
        bach.quantize reads as measures: "timesig" (content [numerator, denominator]; it is
        also the barline of its measure), "barline", "division" (a beat after the first),
        "subdivision", "tempo" (content [figure, value], e.g. ["1/4", 60]).

        add: False replaces every marker, True adds these to the ones there.
        The result says the measures the markers make. Markers bach would drop or misread
        are refused, with what to correct.
        """
        try:
            t = _writer()
        except NoTarget as exc:
            return f"ERROR: {exc}. Nothing was written."
        if isinstance(markers, str):
            try:
                markers = json.loads(markers)
            except json.JSONDecodeError as exc:
                return f"ERROR: {json_error(markers, exc).replace('the score', 'markers')}. Nothing was written."
        problem = check_markers(markers)
        if problem:
            return f"ERROR: {problem}. Nothing was written. Fix this and call the tool again."
        current = ServerBuffer(bridge).fetch(timeout_seconds=3.0)
        if current is None:
            return "ERROR: Max did not hand over the current score (is the patch open?). Nothing was written."
        score = json.loads(json.dumps(current))
        header = score.setdefault("header", {})
        new = [marker(m) for m in markers]
        header["markers"] = grid.ordered((header.get("markers") or []) + new if add else new)
        if add:
            problem = check_markers(header["markers"])
            if problem:
                return f"ERROR: with the markers already in the roll, {problem}. Nothing was added."
        if not RollBuffer(bridge, t.name, t.roll_file).load(score, tonedivision(score)):
            return "ERROR: could not reach Max. Is the patch open?"
        state["last_read"] = None
        status = f"Added {len(new)} markers ({len(header['markers'])} now)" if add else f"{len(new)} markers written"
        return f"OK. {status}; the notes are as they were.{measures_note(header['markers'])}"

    @mcp.tool()
    def read_score(voice: int = 0, from_ms: float = -1.0, to_ms: float = -1.0) -> str:
        """Read the current score from Max. Use ONLY when you need content you did not write yourself, e.g. the
        user edited the score or asks about it. Never use it to check your own write.

        It answers with one line per voice about the whole score, then the music in the same form
        write_score takes: {"header": ..., "voices": [{"chords": [{"onset", "notes": [{"pitch", "dur",
        "vel", ...}]}]}]}, every voice in its place. Only what says nothing is left out ("flag": 0,
        empty keys, most of the header). A long score is cut at one time for all voices; the answer
        says the from_ms to read on from.

        voice: 0 = all voices, or a voice number. from_ms / to_ms: optional window on the onsets, in milliseconds.
        """
        try:
            t = target()
        except NoTarget as exc:
            return f"ERROR: {exc}."
        current = ServerBuffer(bridge).fetch(timeout_seconds=5.0)
        if current is None:
            return "ERROR: Max did not answer. Is the patch open? Do not retry more than once."
        text = read_view(current, voice, from_ms, to_ms)
        key = (conversation(), t.name, voice, from_ms, to_ms, text)  # a new chat has not seen the last answer
        if state["last_read"] == key:
            return "Unchanged since your previous read_score. Use that result; do not read again."
        state["last_read"] = key
        return text

    @mcp.tool()
    def clear_score() -> str:
        """Erase all notes. Not needed before write_score: it replaces the score."""
        try:
            t = _writer()
        except NoTarget as exc:
            return f"ERROR: {exc}. Nothing was cleared."
        state["last_read"] = None
        return "Score cleared." if bridge.send(line(t.name, "clear")) else "ERROR: could not reach Max."


__all__ = ["register_score_tools", "SCORE_TOOLS"]
