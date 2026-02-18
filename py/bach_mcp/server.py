"""Core Bach MCP server implementation."""

from __future__ import annotations

import json
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from tcp import TCPSend, TCPServer

CommandHandler = Callable[[Dict[str, Any]], Any]


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


class BachMCPServer:
    """Owns MCP lifecycle, command routing, and TCP transport wiring."""

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
        self._command_handlers: Dict[str, CommandHandler] = {}
        self._register_builtin_commands()

    def register_command(self, command: str, handler: CommandHandler) -> None:
        """Register a command handler callable."""
        self._command_handlers[command] = handler

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
        """Run server loop until interrupted or shutdown command is received."""
        self.start()
        self._install_signal_handlers()

        try:
            while self.running:
                time.sleep(self.config.idle_sleep_seconds)
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.stop()

    def send_json(self, payload: Dict[str, Any]) -> bool:
        """Send JSON payload to Max through outgoing TCP transport."""
        return self.sender.send(payload)

    def emit_event(self, name: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Emit MCP event toward Max clients."""
        return self.send_json(
            {
                "type": "event",
                "event": name,
                "payload": payload or {},
            }
        )

    def _install_signal_handlers(self) -> None:
        def _handle_signal(signum, frame):  # noqa: ARG001
            self.running = False

        signal.signal(signal.SIGINT, _handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_signal)

    def _register_builtin_commands(self) -> None:
        self.register_command("ping", self._cmd_ping)
        self.register_command("status", self._cmd_status)
        self.register_command("echo", self._cmd_echo)
        self.register_command("shutdown", self._cmd_shutdown)

    def _handle_incoming_message(self, raw_message: str) -> None:
        command, payload, request_id = self._parse_command(raw_message)
        if not command:
            self._send_response(
                command="invalid",
                request_id=request_id,
                ok=False,
                data={"error": "Invalid command payload"},
            )
            return

        result = self._dispatch_command(command, payload)
        self._send_response(
            command=command,
            request_id=request_id,
            ok=result["ok"],
            data=result,
        )

    def _parse_command(
        self, raw_message: str
    ) -> Tuple[Optional[str], Dict[str, Any], Optional[Any]]:
        text = raw_message.strip()
        if not text:
            return None, {}, None

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: a plain-text message is interpreted as command name.
            return text, {}, None

        if not isinstance(parsed, dict):
            return None, {}, None

        command = parsed.get("command") or parsed.get("name")
        request_id = parsed.get("id")
        payload = parsed.get("payload", {})

        if not command:
            return None, {}, request_id

        if payload is None:
            payload = {}
        elif not isinstance(payload, dict):
            payload = {"value": payload}

        return str(command), payload, request_id

    def _dispatch_command(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        handler = self._command_handlers.get(command)
        if handler is None:
            return {"ok": False, "error": f"Unknown command: {command}"}

        try:
            result = handler(payload)
            return {"ok": True, "result": result}
        except Exception as exc:  # pragma: no cover - defensive for runtime transport loop
            return {"ok": False, "error": str(exc)}

    def _send_response(
        self,
        command: str,
        request_id: Optional[Any],
        ok: bool,
        data: Dict[str, Any],
    ) -> None:
        response: Dict[str, Any] = {
            "type": "response",
            "command": command,
            "ok": ok,
        }
        if request_id is not None:
            response["id"] = request_id
        response.update(data)
        self.send_json(response)

    def _cmd_ping(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG002
        return {"pong": True, "timestamp": time.time()}

    def _cmd_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG002
        return {
            "running": self.running,
            "incoming": {
                "host": self.config.incoming_host,
                "port": self.config.incoming_port,
            },
            "outgoing": {
                "host": self.config.outgoing_host,
                "port": self.config.outgoing_port,
                "connected": self.sender.connected,
            },
            "commands": sorted(self._command_handlers.keys()),
        }

    def _cmd_echo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return payload

    def _cmd_shutdown(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG002
        self.running = False
        return {"message": "Shutdown requested"}
