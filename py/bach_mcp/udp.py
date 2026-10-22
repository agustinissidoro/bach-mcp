"""
udp.py
------
The bridge to Max over UDP. Everything here is plain text: one message is one
line such as `mcp_buffer_written q3 "/path/buffer.txt"`. [udpreceive] only
reads OSC packets, so `encode` packs the line into one (the first word is the
message name, every other word an argument: a whole number, a decimal, or a
symbol; a quoted part stays one symbol), and Max outputs it as the same plain
message.

In the patch, [udpreceive 3000] feeds the router directly, and replies go
straight into [udpsend 127.0.0.1 3001]. A reply may arrive as plain text or
in the packet form udpsend uses by default (an address and typed arguments,
each padded to 4 bytes); both are read here as one line of text.

Scores never travel this way (see buffer.py): only short commands and signals,
far below the size of a UDP packet.
"""

from __future__ import annotations

import re
import shlex
import socket
import struct
import sys
import threading
from typing import Callable, Optional

MAX_DATAGRAM = 65507


def _log(message: str) -> None:
    try:
        print(message, file=sys.stderr)
    except Exception:
        pass


def _pad(raw: bytes) -> bytes:
    raw += b"\x00"
    return raw + b"\x00" * (-len(raw) % 4)


def encode(message: str) -> bytes:
    """A line of text as the packet [udpreceive] reads: name, type tags, arguments."""
    words = shlex.split(message, posix=True)
    tags, args = ",", b""
    for word in words[1:]:
        if re.fullmatch(r"[+-]?\d+", word) and -2**31 <= int(word) < 2**31:
            tags += "i"
            args += struct.pack(">i", int(word))
        elif re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?", word):
            tags += "f"
            args += struct.pack(">f", float(word))
        else:
            tags += "s"
            args += _pad(word.encode("utf-8"))
    return _pad(words[0].encode("utf-8")) + _pad(tags.encode("ascii")) + args


def _osc_string(data: bytes, pos: int):
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", errors="replace"), (end + 4) & ~3


def decode(data: bytes) -> str:
    """One datagram as a line of text: plain text as it is, an udpsend packet as `address args...`."""
    try:
        if b"\x00" in data and len(data) % 4 == 0:
            address, pos = _osc_string(data, 0)
            words = [address.lstrip("/")]
            if pos < len(data) and data[pos:pos + 1] == b",":
                tags, pos = _osc_string(data, pos)
                for tag in tags[1:]:
                    if tag == "s":
                        value, pos = _osc_string(data, pos)
                        words.append(f'"{value}"' if " " in value else value)
                    elif tag == "i":
                        words.append(str(int.from_bytes(data[pos:pos + 4], "big", signed=True)))
                        pos += 4
                    elif tag == "f":
                        words.append(repr(struct.unpack(">f", data[pos:pos + 4])[0]))
                        pos += 4
            return " ".join(w for w in words if w)
    except (ValueError, struct.error):
        pass
    return data.decode("utf-8", errors="replace").strip().strip("\x00")


class UDPSend:
    """Sends text messages to Max. UDP has no connection: a send only fails if the address is unusable."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3000) -> None:
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, message: str) -> bool:
        try:
            data = encode(message.strip()) if message.strip() else b""
        except ValueError as exc:  # unbalanced quotes
            _log(f"[UDP] cannot send {message[:80]!r}: {exc}")
            return False
        if not data or len(data) > MAX_DATAGRAM:
            _log(f"[UDP] not sent ({len(data)} bytes): scores go through the buffer file, not messages")
            return False
        try:
            self.socket.sendto(data, (self.host, self.port))
            return True
        except OSError as exc:
            _log(f"[UDP] send to {self.host}:{self.port} failed: {exc}")
            return False

    def close(self) -> None:
        self.socket.close()


class UDPReceiver:
    """Receives text messages from Max on a port and hands each one to a handler, on its own thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3001) -> None:
        self.host = host
        self.port = port
        self.handler: Optional[Callable[[str], None]] = None
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def set_default_handler(self, handler: Callable[[str], None]) -> None:
        self.handler = handler

    def start(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.settimeout(0.5)
        self.port = self.socket.getsockname()[1]
        self.running = True
        self.thread = threading.Thread(target=self._run, name="udp-receive", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        while self.running:
            try:
                data, _ = self.socket.recvfrom(MAX_DATAGRAM)
            except socket.timeout:
                continue
            except OSError:
                break
            text = decode(data)
            if text and self.handler:
                try:
                    self.handler(text)
                except Exception as exc:  # noqa: BLE001 — a bad message must not stop the bridge
                    _log(f"[UDP] handler error: {exc}")

    def stop(self) -> None:
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=1.0)


__all__ = ["UDPSend", "UDPReceiver"]
