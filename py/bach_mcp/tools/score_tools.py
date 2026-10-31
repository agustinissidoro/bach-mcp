"""
score_tools.py
--------------
The score tools: write_score, read_score, clear_score.

The model reads and writes scores in the compressed form (music/compress.py):
chords and notes as plain lists, nothing empty, slots by name. Everywhere else a
score is bachjson-complete, and so is what these tools pass on: read_score
asks the server patch for buffer.json and shows it through music/reader.py; write_score expands what the model wrote
onto the roll's score, so everything the model does not see (the header:
slotinfo, clefs, keys ...) is kept.

Each call is for one instance (session.py: the one whose prompt is being
answered, else the active one): its score travels through its own file in the
playground, scores/<name>.json (buffer.py), never as messages. Only a writer
writes notes; any instance can have its roll read.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP

from ..bridge.buffer import RollBuffer, ServerBuffer
from ..bridge.max import MaxBridge
from ..bridge.protocol import line
from ..music.compress import count_notes, describe, expand
from ..music.reader import read_view
from .session import NoTarget, Target, conversation, target

SCORE_TOOLS = ("write_score", "read_score", "clear_score")
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


def check_short(short: Any) -> Optional[str]:
    """What is wrong with a compressed score, said where it is; None if it can be expanded."""
    example = '{"voices": [{"name": "Flute", "chords": [[0, [6000, 500, 80]]]}]}'
    if not isinstance(short, dict) or not isinstance(short.get("voices"), list) or not short["voices"]:
        return f"the score needs \"voices\": a non-empty list, like {example}"
    for vi, v in enumerate(short["voices"], 1):
        if not isinstance(v, dict) or not isinstance(v.get("chords", []), list):
            return f'voice {vi}: must be an object like {{"name": "Flute", "chords": [...]}}'
        for ci, c in enumerate(v.get("chords", []), 1):
            where = f"voice {vi}, chord {ci}"
            if not isinstance(c, list) or not c or not _is_number(c[0]):
                return f"{where}: a chord is [onset, note, note, ...], e.g. [0, [6000, 500, 80]]"
            if not any(isinstance(n, list) for n in c[1:]):
                return f"{where}: a chord needs at least one note after its onset, e.g. [0, [6000, 500, 80]]"
            for ni, n in enumerate((n for n in c[1:] if isinstance(n, list)), 1):
                plain = [x for x in n if not isinstance(x, dict)]
                if len(plain) != 3 or not all(_is_number(x) for x in plain):
                    return f"{where}, note {ni}: a note is [pitch, dur, vel] (numbers), then optionally {{extras}}"
                if 0 <= plain[0] <= 127:
                    return (f"{where}, note {ni}: pitch {plain[0]} looks like a MIDI note number; "
                            f"pitch is in midicents (6000 = middle C, MIDI {plain[0]} is {plain[0] * 100})")
                if plain[1] <= 0:
                    return f"{where}, note {ni}: dur must be > 0 (milliseconds)"
    return None


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
    """`new`'s chords added to `base`'s, voice by voice, in time order; voices base lacks are added."""
    out = json.loads(json.dumps(base))
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
    """The instance being served, if it is a writer; else NoTarget saying what it takes instead."""
    t = target()
    if t.kind != "writer":
        raise NoTarget(f"{t.name} is a {t.kind}: it takes an algorithm (send_algorithm), not notes")
    return t


def register_score_tools(mcp: FastMCP, bridge: MaxBridge) -> None:
    """Register the JSON score tools on `mcp`. Scores travel through each instance's file, signals through `bridge`."""
    state: Dict[str, Any] = {"last_read": None}

    def _buffer(t: Target) -> RollBuffer:
        return RollBuffer(bridge, t.name, t.roll_file)

    def _send_score(raw: Any, add: bool) -> str:
        try:
            buffer = _buffer(_writer())
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
        problem = check_short(raw)
        if problem:
            return f"ERROR: {problem}. Nothing was written. Fix this and call the tool again."
        current = ServerBuffer(bridge).fetch(timeout_seconds=3.0)  # read like read_score; its header is kept (and, with add, its notes)
        if add and current is None:
            return "ERROR: Max did not hand over the current score (is the patch open?). Nothing was added."
        written = expand(raw, current)
        score = add_chords(current, written) if add else written
        if count_notes(score) > MAX_NOTES:
            return f"ERROR: more than {MAX_NOTES} notes. Nothing was written."
        if not buffer.load(score, tonedivision(score)):
            return "ERROR: could not reach Max. Is the patch open?"
        state["last_read"] = None
        status = "Added to the score" if add else "Score written"
        return f"OK. {status}.\n{describe(score)}\nThis is the exact content. Do not call read_score to check it."

    @mcp.tool()
    def write_score(score: Union[Dict[str, Any], str], add: bool = False) -> str:
        """Write music to the score. Decide the generating principle first, then send the
        complete score in one call.

        score = {"voices": [{"name": "Flute", "chords": [CHORD, ...]}, ...]}
        CHORD = [onset, NOTE, NOTE, ...]     onset in milliseconds; a single note is a chord with one note.
        NOTE  = [pitch, dur, vel]            pitch in midicents (6000 = middle C), copied from the pitch
                tools; dur in milliseconds; vel loudness 1-127.
                Extras, only when needed, in an object after vel:
                [6000, 500, 80, {"dynamics": "p<", "articulations": ["staccato"], "gliss": 200}]
        One entry in "voices" per instrument, top staff first. Silence is a gap between onsets.
        Optional "markers": [[0, "A"], [8000, "B"]] labels sections.

        add: False replaces the notes, True adds these chords to them.
        The result lists what was written.
        """
        return _send_score(score, add=add)

    @mcp.tool()
    def read_score(voice: int = 0, from_ms: float = -1.0, to_ms: float = -1.0) -> str:
        """Read the current score from Max. Use ONLY when you need content you did not write yourself, e.g. the
        user edited the score or asks about it. Never use it to check your own write.

        It answers with one line per voice about the whole score, then the music in the same form
        write_score takes (chord = [onset, note, ...], note = [pitch, dur, vel], extras in an object
        after vel), each voice with its number. A long score is cut at one time for all voices; the
        answer says the from_ms to read on from.

        voice: 0 = all voices, or a voice number. from_ms / to_ms: optional window on the onsets, in milliseconds.
        """
        try:
            t = target()
        except NoTarget as exc:
            return f"ERROR: {exc}."
        complete = ServerBuffer(bridge).fetch(timeout_seconds=5.0)
        if complete is None:
            return "ERROR: Max did not answer. Is the patch open? Do not retry more than once."
        text = read_view(complete, voice, from_ms, to_ms)
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
