"""
buffer.py
---------
Scores travel between the MCP server and bach.roll through one file, not
through messages (a long score gets chunked on the way). The file is
`buffer.txt` in the bach-mcp folder, always in bach's text llll format, the
format bach.roll's own `read` and `writetxt` use.

One short plain-text message each way drives it (over the UDP bridge, udp.py):

    mcp_buffer_written <path>   the server has written the file: bach.roll reads it (read <path>)
    write_buffer <path>         the server wants the score: bach.roll writes it (writetxt <path>),
                                then Max answers bach_buffer_written

Adding to the score (write_score add=True) cannot use `read`, which replaces
everything: the server fetches the score, inserts the new chords into bach's
own text and writes the result back. Whatever the JSON does not model (other
slots, slotinfo, ...) stays as it was.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from .translate import chord_llll, fmt

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POLL_SECONDS = 0.05

# Tokens of bach's text format, with their place in the text: quoted symbols, brackets, atoms.
_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[\[\]]|[^\s\[\]"]+')


def buffer_path() -> str:
    """The buffer file: [max] buffer in bach.toml, relative to the repo (default buffer.txt)."""
    path = os.path.expanduser(os.getenv("BACH_BUFFER") or os.path.join("max", "bach-mcp", "buffer.txt"))
    return path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)


def spaced(llll: str) -> str:
    """An llll with every bracket as its own token, as bach writes its text files."""
    return " ".join(llll.replace("[", " [ ").replace("]", " ] ").split())


def is_complete(text: str) -> bool:
    """A whole score written by bach: starts with roll and every bracket is closed."""
    if not text.lstrip().startswith("roll"):
        return False
    depth = 0
    for m in _TOKEN.finditer(text):
        token = m.group(0)
        depth += token == "["
        depth -= token == "]"
        if depth < 0:
            return False
    return depth == 0 and text.rstrip().endswith("]")


def _write_atomic(path: str, text: str) -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    tmp = os.path.join(folder, f".{os.path.basename(path)}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    os.replace(tmp, path)


def _top_level_lists(text: str) -> Tuple[List[Tuple[int, int, List[Tuple[str, int]]]], int]:
    """The top-level lists after `roll`, and where `roll` ends.

    Each list is (start, end, children): its direct children as (token, position),
    a child list given as "[".
    """
    tokens = [(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(text)]
    if not tokens or tokens[0][0] != "roll":
        raise ValueError("the buffer does not hold a bach.roll score (it should start with roll)")
    lists: List[Tuple[int, int, List[Tuple[str, int]]]] = []
    depth, start, children = 0, 0, []
    for token, s, e in tokens[1:]:
        if token == "[":
            depth += 1
            if depth == 1:
                start, children = s, []
            elif depth == 2:
                children.append(("[", s))
        elif token == "]":
            depth -= 1
            if depth == 0:
                lists.append((start, e, children))
        elif depth == 1:
            children.append((token, s))
    return lists, tokens[0][2]


def add_to_roll(text: str, score: Dict[str, Any]) -> str:
    """Insert the chords and markers of a canonical score into bach's text of the current score.

    Voice n of `score` goes into voice n of the roll, before its closing flag; voices
    the roll does not have yet are added after the last one.
    """
    lists, after_roll = _top_level_lists(text)

    def is_header(item: Tuple[int, int, List[Tuple[str, int]]]) -> bool:
        children = item[2]
        return bool(children) and children[0][0] != "[" and not _is_number(children[0][0])

    headers = [item for item in lists if is_header(item)]
    voices = [item for item in lists if not is_header(item)]
    inserts: List[Tuple[int, str]] = []
    new_voices: List[str] = []

    for vi, voice in enumerate(score["voices"]):
        chords = " ".join(spaced(chord_llll(c)) for c in voice["chords"])
        if vi < len(voices):
            if chords:
                _, end, children = voices[vi]
                last = children[-1] if children else None
                at = last[1] if last is not None and _is_number(last[0]) else end - 1
                inserts.append((at, chords + " "))
        else:
            new_voices.append(f"[ {chords} 0 ]" if chords else "[ 0 ]")
    if new_voices:
        inserts.append((lists[-1][1] if lists else after_roll, " " + " ".join(new_voices)))

    markers = score.get("markers") or []
    if markers:
        items = " ".join(f"[ {fmt(m['onset'])} {m['name'] or 'nil'} ]" for m in markers)
        found = next((h for h in headers if h[2][0][0] == "markers"), None)
        if found:
            inserts.append((found[1] - 1, items + " "))
        else:
            inserts.append((after_roll, f" [ markers {items} ]"))

    for at, piece in sorted(inserts, key=lambda x: -x[0]):
        text = text[:at] + piece + text[at:]
    return text


def _is_number(token: str) -> bool:
    return re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?", token) is not None


class RollBuffer:
    """The file exchange with bach.roll, over the bridge to Max. One message each way:

        mcp_buffer_written <path>   the server wrote the file: bach.roll reads it (no answer)
        write_buffer <path>         bach.roll writes the file, then Max sends bach_buffer_written
    """

    def __init__(self, bach: Any, path: Optional[str] = None) -> None:
        self.bach = bach
        self.path = path or buffer_path()

    def _quoted(self) -> str:
        return f'"{self.path}"'

    def load(self, text: str, tonedivision: int = 2) -> bool:
        """Write `text` (a whole `roll ...` llll) to the buffer and tell bach.roll to read it."""
        _write_atomic(self.path, text)
        if tonedivision > 2:  # must reach bach.roll before the notes, or it cannot draw the microtones
            if not self.bach.send_info(f"tonedivision {tonedivision}"):
                return False
            time.sleep(_POLL_SECONDS)
        return self.bach.send_info(f"mcp_buffer_written {self._quoted()}")

    # Confirmation of a load, switched off for now: Max would answer
    # `bach_buffer_loaded <notes of each chord...>` (getnumnotes) and load() would return the count.
    #
    # def _await(self, signal, timeout_seconds):
    #     deadline = time.time() + timeout_seconds
    #     while time.time() < deadline:
    #         message = self.bach.wait_for_incoming(timeout_seconds=deadline - time.time())
    #         words = str((message or {}).get("data", "")).replace("[", " [ ").replace("]", " ] ").split()
    #         if words and words[0] == signal:
    #             return words[1:]
    #     return None
    #
    # notes = sum(int(w) for w in self._await("bach_buffer_loaded", 3.0) or [] if w.isdigit())

    def fetch(self, timeout_seconds: float = 5.0) -> Optional[str]:
        """Have bach.roll write the score to the buffer and return its text, or None if it does not."""
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        self.bach.flush_incoming()
        if not self.bach.send_info(f"write_buffer {self._quoted()}"):
            return None
        deadline = time.time() + timeout_seconds
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            message = self.bach.wait_for_incoming(timeout_seconds=remaining)
            if message is None:
                return None
            if str(message.get("data", "")).split()[:1] == ["bach_buffer_written"]:
                break
        # bach.roll may finish the file just after it answers: wait until it is whole.
        deadline = time.time() + 2.0
        while True:
            try:
                with open(self.path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
                if is_complete(text):
                    return text
            except OSError:
                pass
            if time.time() > deadline:
                return None
            time.sleep(_POLL_SECONDS)


__all__ = ["RollBuffer", "buffer_path", "add_to_roll", "spaced", "is_complete"]
