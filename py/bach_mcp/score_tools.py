"""
score_tools.py
--------------
The lean, JSON-facing tool set: write_score, read_score, play, stop, clear_score.

These are the only tools a local model needs. They speak the JSON score of
`translate.py`: bach.roll's own hierarchy (voices > chords > notes) and units
(milliseconds, midicents), without the llll brackets or the header syntax.
Every write is checked against bach.roll here, in code, and the result is
reported back in one compact summary — so the model has no reason to dump the
score to see whether its write worked.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .server import BachMCPServer
from .translate import (
    ScoreError,
    count_notes,
    llll_to_score,
    normalize_score,
    score_messages,
    summarize,
)

LEAN_TOOLS = ("write_score", "read_score", "play", "stop", "clear_score")

# Gap between two messages to Max so the Node bridge receives them as separate packets.
_SEND_GAP_SECONDS = 0.05
_READ_CHORD_LIMIT = 400


def register_score_tools(mcp: FastMCP, bach: BachMCPServer) -> None:
    """Register the JSON score tools on `mcp`."""
    verify_writes = os.getenv("BACH_VERIFY", "1") != "0"
    state: Dict[str, Any] = {"last_read": None}

    def _request_roll(command: str, timeout_seconds: float) -> Optional[str]:
        """Send a query to bach.roll and return its llll reply, ignoring unrelated messages."""
        bach.flush_incoming()
        if not bach.send_info(command):
            return None
        deadline = time.time() + timeout_seconds
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            message = bach.wait_for_incoming(timeout_seconds=remaining)
            if message is None:
                return None
            data = str(message.get("data", "")).strip()
            if data.startswith("roll") or data.startswith("["):
                return data

    def _send_score(raw: Any, add: bool, extra: str = "") -> str:
        try:
            score = normalize_score(raw)
        except ScoreError as exc:
            return f"ERROR: {str(exc).rstrip('.')}. Nothing was written. Fix this and call the tool again."

        expected = count_notes(score)
        for index, message in enumerate(score_messages(score, add=add)):
            if index:
                time.sleep(_SEND_GAP_SECONDS)
            if not bach.send_score(message):
                return "ERROR: could not reach Max. Is the patch open and the script started?"
        state["last_read"] = None

        status = "Added to the score" if add else "Score written"
        if verify_writes:
            time.sleep(_SEND_GAP_SECONDS)
            reply = _request_roll("dump body", timeout_seconds=3.0)
            if reply is None:
                status += " (sent; Max did not confirm)"
            else:
                try:
                    actual = count_notes(llll_to_score(reply))
                except ValueError:
                    actual = -1
                if add or actual == expected:
                    status += f" and verified in Max ({actual} notes now in the score)"
                else:
                    status += f", but Max holds {actual} notes and {expected} were sent"
        return (
            f"OK. {status}.\n{summarize(score)}{extra}\n"
            "This is the exact content. Do not call read_score to check it."
        )

    @mcp.tool()
    def write_score(score: Dict[str, Any], add: bool = False) -> str:
        """Write music to the score as JSON. Decide the generating principle first, then
        send the complete score in one call.

        score = {"voices": [{"name": "Flute", "chords": [CHORD, ...]}, ...]}
        CHORD = {"onset": 0, "notes": [NOTE, ...]}
          onset: when the chord starts, in milliseconds from the beginning.
          Optional on the chord: "dyn": "p" "mf" "f" "p<"; "art": "staccato" "accent"
          "tenuto" "marcato" "fermata" "trill" "tremolo"; "text": words above the
          chord; "lyric": a syllable below it.
        NOTE  = {"pitch": 6000, "dur": 500}
          pitch: midicents. 6000 = middle C, 100 = one semitone, 50 = a quarter-tone.
          dur:   duration in milliseconds.
          Optional on the note: "vel": 1-127; "gliss": midicents to slide by, or
          [[position 0-1, midicents], ...]; "head": "diamond" "cross" "white" ...
        A note has no onset: it starts with its chord. A single note is a chord with
        one note. Silence is a gap between onsets.
        One entry in "voices" per instrument, top staff first. Clefs are automatic.
        Optional "markers": [{"onset": 0, "name": "A"}] labels sections.

        add: False replaces the whole score, True adds these chords to it.
        The result lists what was written; it is already verified.
        """
        return _send_score(score, add=add)

    @mcp.tool()
    def read_score(voice: int = 0, from_ms: float = -1.0, to_ms: float = -1.0) -> str:
        """Read the current score from Max as JSON (same format as write_score). Use ONLY when you need content you did not write yourself, e.g. the
        user edited the score or asks about it. Never use it to check your own write.

        voice: 0 = all voices, or a voice number. from_ms / to_ms: optional window on the onsets, in milliseconds.
        """
        reply = _request_roll("dump clefs voicenames markers body", timeout_seconds=5.0)
        if reply is None:
            time.sleep(_SEND_GAP_SECONDS)
            reply = _request_roll("dump body", timeout_seconds=5.0)
        if reply is None:
            return "ERROR: Max did not answer. Is the patch open and the script started? Do not retry more than once."
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

        text = json.dumps(score, ensure_ascii=False, separators=(",", ":"))
        key = (voice, from_ms, to_ms, text)
        if state["last_read"] == key:
            return "Unchanged since your previous read_score. Use that result; do not read again."
        state["last_read"] = key
        note = f"\n(truncated to {_READ_CHORD_LIMIT} chords; narrow with voice/from_ms/to_ms)" if truncated else ""
        return f"{len(score['voices'])} voice(s), {total} notes in the whole score.\n{text}{note}"

    @mcp.tool()
    def play(from_ms: float = 0.0) -> str:
        """Start playback from the given position in milliseconds (default: the beginning)."""
        return "Playing." if bach.send_info(f"play {max(0.0, from_ms):.1f}") else "ERROR: could not reach Max."

    @mcp.tool()
    def stop() -> str:
        """Stop playback."""
        return "Stopped." if bach.send_info("stop") else "ERROR: could not reach Max."

    @mcp.tool()
    def clear_score() -> str:
        """Erase all notes. Not needed before write_score: it replaces the score."""
        state["last_read"] = None
        return "Score cleared." if bach.send_info("clear") else "ERROR: could not reach Max."


__all__ = ["register_score_tools", "LEAN_TOOLS"]
