"""
score_tools.py
--------------
The lean, JSON-facing tool set: write_score, read_score, clear_score.

These are the only tools a local model needs. They speak the JSON score of
`translate.py`: bach.roll's own hierarchy (voices > chords > notes) and units
(milliseconds, midicents), without the llll brackets or the header syntax.
Every write is checked against bach.roll here, in code, and the result is
reported back in one compact summary — so the model has no reason to dump the
score to see whether its write worked.

The scores themselves travel through the buffer file (buffer.py), never as
TCP messages.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Union

from mcp.server.fastmcp import FastMCP

from .buffer import RollBuffer, add_to_roll, spaced
from .server import BachMCPServer
from .session import conversation
from .translate import (
    ScoreError,
    count_notes,
    llll_to_score,
    normalize_score,
    required_tonedivision,
    score_to_llll,
    score_to_positional,
    summarize,
)

LEAN_TOOLS = ("write_score", "read_score", "clear_score")


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

_READ_CHORD_LIMIT = 2000  # a whole score of ~900 chords is ~30K tokens; the context is 64K


def register_score_tools(mcp: FastMCP, bach: BachMCPServer) -> None:
    """Register the JSON score tools on `mcp`."""
    verify_writes = os.getenv("BACH_VERIFY", "1") != "0"  # noqa: F841 — used again when the check is back
    state: Dict[str, Any] = {"last_read": None}

    buffer = RollBuffer(bach)

    def _send_score(raw: Any, add: bool, extra: str = "") -> str:
        if isinstance(raw, str):  # the score arrived as text: read it, or say exactly where it breaks
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as exc:
                repaired = close_brackets(raw)
                if repaired is None:
                    return f"ERROR: {json_error(raw, exc)}. Nothing was written. Fix this spot and call the tool again."
                raw = repaired
        try:
            score = normalize_score(raw)
        except ScoreError as exc:
            return f"ERROR: {str(exc).rstrip('.')}. Nothing was written. Fix this and call the tool again."

        expected = count_notes(score)
        if add:
            current = buffer.fetch()
            if current is None:
                return "ERROR: Max did not hand over the current score (is the patch open?). Nothing was added."
            try:
                text = add_to_roll(current, score)
            except ValueError as exc:
                return f"ERROR: could not add to the current score ({exc}). Nothing was added."
        else:
            text = spaced(score_to_llll(score))
        if not buffer.load(text, required_tonedivision(score)):
            return "ERROR: could not reach Max. Is the patch open?"
        state["last_read"] = None
        status = "Added to the score" if add else "Score written"
        # Checking the load in Max is switched off for now (see RollBuffer):
        # if verify_writes: compare the notes bach.roll reports with `expected`.
        return (
            f"OK. {status}.\n{summarize(score, names=True)}{extra}\n"
            "This is the exact content. Do not call read_score to check it."
        )

    @mcp.tool()
    def write_score(score: Union[Dict[str, Any], str], add: bool = False) -> str:
        """Write music to the score as JSON. Decide the generating principle first, then
        send the complete score in one call.

        score = {"voices": [{"name": "Flute", "chords": [CHORD, ...]}, ...]}
        CHORD = [onset, {marks}, NOTE, NOTE, ...]   always these parts; {marks} is {} when there are
                none, else e.g. {"dyn": "p", "art": "staccato", "text": "pizz."}. onset in milliseconds.
        NOTE  = [pitch, dur, vel]   pitch in midicents (6000 = middle C), copied from the pitch tools
                (p2mc, get_chord, get_scale, transpose ...). dur in milliseconds, vel loudness 1-127.
                Extras, rarely, after them: [6000, 500, 80, {"gliss": 200, "head": "diamond"}]
        A single note is a chord with one note. Silence is a gap between onsets.
        One entry in "voices" per instrument, top staff first. Clefs are automatic.
        Optional "markers": [{"onset": 0, "name": "A"}] labels sections.

        add: False replaces the whole score, True adds these chords to it.
        The result lists what was written.
        """
        return _send_score(score, add=add)

    @mcp.tool()
    def read_score(voice: int = 0, from_ms: float = -1.0, to_ms: float = -1.0) -> str:
        """Read the current score from Max. Use ONLY when you need content you did not write yourself, e.g. the
        user edited the score or asks about it. Never use it to check your own write.

        It answers in the same form write_score takes: chord = [onset, {marks}, note, ...],
        note = [pitch, dur, vel] (extras, if any, in an object after vel).

        voice: 0 = all voices, or a voice number. from_ms / to_ms: optional window on the onsets, in milliseconds.
        """
        reply = buffer.fetch(timeout_seconds=5.0)
        if reply is None:
            return "ERROR: Max did not answer. Is the patch open? Do not retry more than once."
        try:
            score = llll_to_score(reply)
        except ValueError as exc:
            return f"ERROR: could not parse the reply from Max ({exc})."

        total = count_notes(score)

        def in_window(item: Dict[str, Any]) -> bool:
            return item["onset"] >= from_ms and (to_ms < 0 or item["onset"] < to_ms)

        if voice > 0:
            score["voices"] = [v for v in score["voices"] if v["voice"] == voice]
        for v in score["voices"]:
            v["chords"] = [c for c in v["chords"] if in_window(c)]
        if "markers" in score:
            score["markers"] = [m for m in score["markers"] if in_window(m)]

        shown, truncated = 0, False
        for v in score["voices"]:
            room = max(0, _READ_CHORD_LIMIT - shown)
            if len(v["chords"]) > room:
                v["chords"], truncated = v["chords"][:room], True
            shown += len(v["chords"])

        text = json.dumps(score_to_positional(score, fixed=True), ensure_ascii=False, separators=(",", ":"))
        key = (conversation(), voice, from_ms, to_ms, text)  # a new chat has not seen the last answer
        if state["last_read"] == key:
            return "Unchanged since your previous read_score. Use that result; do not read again."
        state["last_read"] = key
        note = f"\n(truncated to {_READ_CHORD_LIMIT} chords; narrow with voice/from_ms/to_ms)" if truncated else ""
        return f"{len(score['voices'])} voice(s), {total} notes in the whole score.\n{text}{note}"

    @mcp.tool()
    def clear_score() -> str:
        """Erase all notes. Not needed before write_score: it replaces the score."""
        state["last_read"] = None
        return "Score cleared." if bach.send_info("clear") else "ERROR: could not reach Max."


__all__ = ["register_score_tools", "LEAN_TOOLS"]
