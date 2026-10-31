"""
buffer.py
---------
Scores travel between the MCP server and an instance's roll through a file,
not through messages (a long score would hit Max's message limit): the
instance's own file in the playground, scores/<name>.json, always in
bachjson-complete (bachjson-syntax-specification.md). In the patch the file
goes into a dictionary and through bachmcp.translate, the only place that
speaks bach's own syntax.

One short message each way drives it (over the UDP bridge, udp.py), prefixed
with the instance's name like everything for an instance; <file> is the file's
name in scores/:

    <name> load_roll <file>       the server has written the file: the roll takes it
    <name> write_roll <file>      the server wants the score: the patch writes it there,
                                  then Max answers <name> roll_written <file>
    <name> tonedivision <n>       before a load whose pitches need it (microtones)

read_score asks the server patch instead (ServerBuffer):

    server write_buffer           the patch dumps the roll as bachjson-complete into
                                  <repo>/buffer.json, then Max answers server buffer_done
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from ..config import REPO_ROOT
from .protocol import line, words

_POLL_SECONDS = 0.05


def write_json(path: str, data: Dict[str, Any]) -> None:
    """Write a score file whole (through a temporary file, so Max never reads half of one)."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    tmp = os.path.join(folder, f".{os.path.basename(path)}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


BUFFER_FILE = os.path.join(REPO_ROOT, "buffer.json")


def read_json(path: str) -> Optional[Dict[str, Any]]:
    """A score file, or None while it is missing or not whole yet."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


class RollBuffer:
    """The file exchange with the roll of one instance, over the bridge to Max (see the top)."""

    def __init__(self, bridge: Any, name: str, path: str) -> None:
        self.bridge = bridge  # a MaxBridge (max.py)
        self.name = name      # the instance
        self.path = path      # its file: <playground>/scores/<name>.json

    @property
    def file(self) -> str:
        return os.path.basename(self.path)

    def load(self, score: Dict[str, Any], tonedivision: int = 2) -> bool:
        """Write a complete score to the file and tell the instance's roll to take it."""
        write_json(self.path, score)
        if tonedivision > 2:  # must reach bach.roll before the notes, or it cannot draw the microtones
            if not self.bridge.send(line(self.name, "tonedivision", tonedivision)):
                return False
            time.sleep(_POLL_SECONDS)
        return self.bridge.send(line(self.name, "load_roll", self.file))

    def fetch(self, timeout_seconds: float = 5.0) -> Optional[Dict[str, Any]]:
        """Have the patch write the roll's score to the file and return it, or None if it does not."""
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        self.bridge.flush()
        if not self.bridge.send(line(self.name, "write_roll", self.file)):
            return None
        deadline = time.time() + timeout_seconds
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            answer = self.bridge.receive(timeout_seconds=remaining)
            if answer is None:
                return None
            if words(answer)[:2] == [self.name, "roll_written"]:
                break
        # The file may be finished just after the answer: wait until it reads whole.
        deadline = time.time() + 2.0
        while True:
            score = read_json(self.path)
            if score is not None:
                return score
            if time.time() > deadline:
                return None
            time.sleep(_POLL_SECONDS)


def _await_file(path: str, seconds: float = 2.0) -> Optional[Dict[str, Any]]:
    """The file once it reads whole: it may be finished just after Max's answer."""
    deadline = time.time() + seconds
    while True:
        data = read_json(path)
        if data is not None or time.time() > deadline:
            return data
        time.sleep(_POLL_SECONDS)


class ServerBuffer:
    """The score as the server patch dumps it: server write_buffer -> server buffer_done -> buffer.json."""

    def __init__(self, bridge: Any, path: Optional[str] = None) -> None:
        self.bridge = bridge
        self.path = path or BUFFER_FILE

    def fetch(self, timeout_seconds: float = 5.0) -> Optional[Dict[str, Any]]:
        """The complete score, or None if Max does not answer in time."""
        self.bridge.flush()
        if not self.bridge.send(line("server", "write_buffer")):
            return None
        deadline = time.time() + timeout_seconds
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            answer = self.bridge.receive(timeout_seconds=remaining)
            if answer is None:
                return None
            if words(answer)[:2] == ["server", "buffer_done"]:
                return _await_file(self.path)


__all__ = ["RollBuffer", "ServerBuffer", "BUFFER_FILE", "write_json", "read_json"]
