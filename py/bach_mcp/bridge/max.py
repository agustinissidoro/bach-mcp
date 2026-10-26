"""
max.py
------
The bridge to the Max patch: short plain-text lines over UDP (see udp.py).

    send(line)          a line to the patch: [udpreceive <send_port>]
    say(*words)         the same, from words: each one arrives in Max as one atom
    receive(timeout)    the next line the patch answered: [udpsend 127.0.0.1 <receive_port>]
    flush()             forget earlier answers, before asking something new
    on_request(fn)      lines the patch starts itself, `bach ...`, go to fn, not to receive()
    on_line(fn)         every other line goes to fn first (the hub, chat/hub.py): the
                        ones it takes (fn returns True) never reach receive()

Scores never travel this way: they go through the buffer file (buffer.py).
Only one process can listen on the receive port at a time.
"""

from __future__ import annotations

import sys
import threading
from collections import deque
from typing import Callable, Deque, Optional, Union

from .protocol import line
from .udp import UDPReceiver, UDPSend

REQUEST = "bach"  # the first word of a request from the patch (answered by utilities/status.py)


def _log(message: str) -> None:
    """Best-effort logging on stderr, which never breaks the MCP stdio transport."""
    try:
        print(message, file=sys.stderr)
    except Exception:
        pass


class BridgeBusy(RuntimeError):
    """The receive port is held by another process: only one Bach can talk to the patch at a time."""


class MaxBridge:
    """Sends lines to the patch and queues the lines it answers."""

    def __init__(self, send_port: int = 3000, receive_port: int = 3001, host: str = "127.0.0.1") -> None:
        self.host = host
        self.send_port = send_port
        self.receive_port = receive_port
        self._sender = UDPSend(host=host, port=send_port)
        self._receiver = UDPReceiver(host=host, port=receive_port)
        self._answers: Deque[str] = deque(maxlen=500)
        self._lock = threading.Lock()
        self._arrived = threading.Condition(self._lock)
        self._on_request: Optional[Callable[[str], None]] = None
        self._on_line: Optional[Callable[[str], bool]] = None
        self.running = False

    def start(self) -> None:
        """Listen for the patch's answers. Raises BridgeBusy if another process holds the port."""
        if self.running:
            return
        self._receiver.set_default_handler(self._on_answer)
        try:
            self._receiver.start()
        except OSError as exc:
            raise BridgeBusy(
                f"UDP port {self.receive_port} is taken: another Bach is already running (Claude Desktop "
                "starts one when it opens). Close it first, or use that one.") from exc
        self.running = True
        _log(f"Max bridge: sending to UDP {self.host}:{self.send_port}, listening on {self.receive_port}")

    def stop(self) -> None:
        self.running = False
        self._sender.close()
        self._receiver.stop()

    def send(self, line: str) -> bool:
        """Send one line to the patch. False if it could not be sent."""
        return self._sender.send(line)

    def say(self, *words: Union[str, int, float]) -> bool:
        return self.send(line(*words))

    def on_request(self, handler: Callable[[str], None]) -> None:
        """Hand every `bach ...` line from the patch to handler (on the receiving thread)."""
        self._on_request = handler

    def on_line(self, handler: Callable[[str], bool]) -> None:
        """Offer every other line to handler first (on the receiving thread); True means it took it."""
        self._on_line = handler

    def receive(self, timeout_seconds: float = 10.0) -> Optional[str]:
        """The oldest answer not yet read, waiting up to timeout_seconds; None if none came."""
        with self._arrived:
            if not self._answers:
                self._arrived.wait_for(lambda: bool(self._answers), timeout=max(0.0, timeout_seconds))
            return self._answers.popleft() if self._answers else None

    def flush(self) -> int:
        """Drop every answer not yet read, so an old one cannot pass for the next. Returns how many."""
        with self._lock:
            count = len(self._answers)
            self._answers.clear()
            return count

    def _on_answer(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if text.split()[0] == REQUEST and self._on_request is not None:
            try:
                self._on_request(text)
            except Exception as exc:  # noqa: BLE001 — a bad request must not stop the bridge
                _log(f"Max bridge: request {text!r} failed: {exc}")
            return
        if self._on_line is not None:
            try:
                if self._on_line(text):
                    return
            except Exception as exc:  # noqa: BLE001 — a bad line must not stop the bridge
                _log(f"Max bridge: line {text!r} failed: {exc}")
                return
        with self._arrived:
            self._answers.append(text)
            self._arrived.notify_all()


class OfflineBridge:
    """A bridge with no Max behind it: nothing is sent, nothing answers. For listing tools and for eval."""

    def send(self, line: str) -> bool:
        return False

    def say(self, *words: Union[str, int, float]) -> bool:
        return False

    def on_request(self, handler: Callable[[str], None]) -> None:
        pass

    def on_line(self, handler: Callable[[str], bool]) -> None:
        pass

    def receive(self, timeout_seconds: float = 10.0) -> Optional[str]:
        return None

    def flush(self) -> int:
        return 0

    def stop(self) -> None:
        pass


__all__ = ["MaxBridge", "OfflineBridge", "BridgeBusy", "REQUEST", "line"]
