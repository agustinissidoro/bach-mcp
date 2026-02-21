"""Core Bach MCP server implementation."""

from __future__ import annotations

import json
import signal
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Optional

try:
    from .tcp import TCPSend, TCPServer
except ImportError:
    from tcp import TCPSend, TCPServer


def _log(message: str) -> None:
    """Best-effort logging that never breaks stdio transport."""
    try:
        print(message, file=sys.stderr)
    except Exception:
        pass


@dataclass
class MCPConfig:
    """Runtime settings for the Bach MCP server."""

    incoming_host: str = "127.0.0.1"
    incoming_port: int = 3001
    outgoing_host: str = "127.0.0.1"
    outgoing_port: int = 3000
    idle_sleep_seconds: float = 0.2


@dataclass
class BridgeMessage:
    """Canonical message envelope shared by Max and Claude."""

    type: str
    data: str
    raw: str
    received_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "raw": self.raw,
            "received_at": self.received_at,
        }


class BachMCPServer:
    """Owns MCP lifecycle and TCP transport wiring."""

    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig()
        self.server = TCPServer(
            host=self.config.incoming_host,
            port=self.config.incoming_port,
        )
        self.sender = TCPSend(
            host=self.config.outgoing_host,
            port=self.config.outgoing_port,
        )
        self.running = False
        self._incoming_messages: Deque[BridgeMessage] = deque(maxlen=500)
        self._incoming_lock = threading.Lock()
        self._incoming_event = threading.Event()

    def start(self) -> None:
        """Start server and bind incoming message handler."""
        if self.running:
            return

        self.server.set_default_handler(self._handle_incoming_message)
        self.server.start()
        self.running = True

        _log("=" * 50)
        _log("BACH MCP - Ready")
        _log("=" * 50)
        _log(f"Incoming TCP: {self.config.incoming_host}:{self.config.incoming_port}")
        _log(f"Outgoing TCP: {self.config.outgoing_host}:{self.config.outgoing_port}")

    def stop(self) -> None:
        """Graceful server shutdown."""
        self.running = False
        if self.sender:
            self.sender.close()
        if self.server:
            self.server.stop()
        _log("BACH MCP - Stopped")

    def run_forever(self) -> None:
        """Run server loop until interrupted."""
        self.start()
        self._install_signal_handlers()

        try:
            while self.running:
                time.sleep(self.config.idle_sleep_seconds)
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.stop()

    def send_score(self, score_llll: str) -> bool:
        """Send raw llll score to Max."""
        return self.sender.send(score_llll)

    def send_info(self, message: str) -> bool:
        """Send plain process message to Max."""
        return self.sender.send(message)

    def pop_next_incoming(self, message_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Pop oldest incoming message from Max, optionally filtered by type."""
        with self._incoming_lock:
            if not self._incoming_messages:
                self._incoming_event.clear()
                return None
            if message_type is None:
                message = self._incoming_messages.popleft()
                if not self._incoming_messages:
                    self._incoming_event.clear()
                return message.to_dict()

            for index, message in enumerate(self._incoming_messages):
                if message.type != message_type:
                    continue
                selected = self._incoming_messages[index]
                del self._incoming_messages[index]
                if not self._incoming_messages:
                    self._incoming_event.clear()
                return selected.to_dict()
            return None

    def get_latest_incoming(self, message_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return latest incoming message without consuming it."""
        with self._incoming_lock:
            if not self._incoming_messages:
                return None
            if message_type is None:
                return self._incoming_messages[-1].to_dict()
            for message in reversed(self._incoming_messages):
                if message.type == message_type:
                    return message.to_dict()
            return None

    def wait_for_incoming(
        self,
        timeout_seconds: float = 10.0,
        message_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Wait for next incoming message from Max (consuming read)."""
        deadline = time.time() + max(0.0, timeout_seconds)
        while True:
            message = self.pop_next_incoming(message_type=message_type)
            if message is not None:
                return message

            remaining = deadline - time.time()
            if remaining <= 0:
                return None

            has_data = self._incoming_event.wait(timeout=min(remaining, 0.25))
            if not has_data and remaining <= 0:
                return None

    def incoming_queue_size(self) -> int:
        """Return number of queued incoming Max messages."""
        with self._incoming_lock:
            return len(self._incoming_messages)

    def flush_incoming(self) -> int:
        """Discard all queued incoming messages and return how many were dropped.

        Call this immediately before sending a query command (dump, subroll,
        getnumvoices, etc.) so that stale responses from earlier tool calls
        cannot be mistaken for the reply we are about to request.
        """
        with self._incoming_lock:
            count = len(self._incoming_messages)
            self._incoming_messages.clear()
            self._incoming_event.clear()
            return count

    def _install_signal_handlers(self) -> None:
        def _handle_signal(signum, frame):  # noqa: ARG001
            self.running = False

        signal.signal(signal.SIGINT, _handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_signal)

    def _handle_incoming_message(self, raw_message: str) -> None:
        text = raw_message.strip()
        if not text:
            return
        parsed = self._parse_incoming(text)
        with self._incoming_lock:
            self._incoming_messages.append(parsed)
            self._incoming_event.set()
        _log(f"Queued incoming Max message type={parsed.type}")

    def _parse_incoming(self, text: str) -> BridgeMessage:
        """Parse incoming raw text using envelope if present."""
        message_type = "llll" if self._looks_like_llll(text) else "info"
        data = text

        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                candidate_type = str(parsed.get("type") or "").strip().lower()
                if candidate_type in {"llll", "info"}:
                    message_type = candidate_type
                    data = str(parsed.get("data", ""))
                elif "message" in parsed:
                    message_type = "info"
                    data = str(parsed.get("message", ""))

        return BridgeMessage(
            type=message_type,
            data=data,
            raw=text,
            received_at=time.time(),
        )

    @staticmethod
    def _looks_like_llll(text: str) -> bool:
        """Heuristic for raw llll strings, with optional selector prefix."""
        stripped = text.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return True
        if stripped.lower().startswith("roll [") and stripped.endswith("]"):
            return True
        return False
