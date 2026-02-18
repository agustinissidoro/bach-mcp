"""FastMCP app factory and tool/resource registration."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from .server import BachMCPServer


def create_mcp_app(bach: BachMCPServer) -> FastMCP:
    """Create and configure MCP tools/resources for bridge communication."""
    mcp = FastMCP("max-bridge")

    @mcp.tool()
    def add_single_note(
        onset_ms: float = 0.0,
        pitch_cents: float = 6000.0,
        duration_ms: float = 1000.0,
        velocity: int = 100,
    ) -> Dict[str, Any]:
        """Send a single bach.roll note via llll.

        Notation items hierarchy:
        In bach.roll, notes belong to chords, and chords belong to voices.
        The hierarchy is encoded by nested square brackets.

        Format:
        [ [ onset_ms [ pitch_cents duration_ms velocity 0 ] 0 ] 0 ]

        Example (single note, middle C, 1 second, velocity 100):
        [ [ 0. [ 6000. 1000. 100 0 ] 0 ] 0 ]

        Pitch in cents: middle C = 6000, one semitone = 100 cents.
        Each hierarchy level must be wrapped in its own [ ].
        """
        if duration_ms <= 0:
            return {"ok": False, "message": "duration_ms must be > 0"}
        if velocity < 0 or velocity > 127:
            return {"ok": False, "message": "velocity must be between 0 and 127"}

        score_llll = (
            f"[ [ {float(onset_ms):.3f} [ {float(pitch_cents):.3f} "
            f"{float(duration_ms):.3f} {int(velocity)} 0 ] 0 ] 0 ]"
        )
        success = bach.send_score(score_llll)
        if not success:
            return {"ok": False, "message": "Failed to send llll score to Max"}
        return {"ok": True, "score_llll": score_llll}

    @mcp.tool()
    def send_score_to_max(score_llll: str) -> str:
        """Send a raw llll score string to Max/MSP."""
        score_llll = score_llll.strip()
        if not score_llll:
            return "Rejected empty llll score"
        success = bach.send_score(score_llll)
        return "Sent llll score to Max" if success else "Failed to send llll score"

    @mcp.tool()
    def send_process_message_to_max(message: str) -> str:
        """Send plain process/info message to Max (non-score text)."""
        message = message.strip()
        if not message:
            return "Rejected empty process message"
        success = bach.send_info(message)
        return "Sent process message to Max" if success else "Failed to send process message"

    @mcp.tool()
    def poll_from_max(message_type: str = "any") -> Dict[str, Any]:
        """Read and consume the next queued message from Max."""
        normalized = message_type.strip().lower()
        type_filter = None if normalized == "any" else normalized
        if type_filter not in {None, "llll", "info"}:
            return {"ok": False, "message": "message_type must be any|llll|info"}
        message = bach.pop_next_incoming(message_type=type_filter)
        if message is None:
            return {
                "ok": False,
                "message": "No queued Max messages matching requested type",
            }
        return {"ok": True, "message": message}

    @mcp.tool()
    def wait_for_from_max(timeout_seconds: float = 15.0, message_type: str = "any") -> Dict[str, Any]:
        """Wait for and consume the next Max message."""
        normalized = message_type.strip().lower()
        type_filter = None if normalized == "any" else normalized
        if type_filter not in {None, "llll", "info"}:
            return {"ok": False, "message": "message_type must be any|llll|info"}
        message = bach.wait_for_incoming(timeout_seconds=timeout_seconds, message_type=type_filter)
        if message is None:
            return {
                "ok": False,
                "message": f"No Max message ({normalized}) received within {timeout_seconds:.2f}s",
            }
        return {"ok": True, "message": message}

    @mcp.tool()
    def poll_score_from_max() -> Dict[str, Any]:
        """Read and consume the next queued llll score from Max (non-blocking)."""
        message = bach.pop_next_incoming(message_type="llll")
        if message is None:
            return {"ok": False, "message": "No queued llll scores from Max"}
        return {"ok": True, "score_llll": message["data"], "message": message}

    @mcp.tool()
    def wait_for_score_from_max(timeout_seconds: float = 15.0) -> Dict[str, Any]:
        """Wait for and consume the next llll score from Max."""
        message = bach.wait_for_incoming(timeout_seconds=timeout_seconds, message_type="llll")
        if message is None:
            return {
                "ok": False,
                "message": f"No llll score received within {timeout_seconds:.2f}s",
            }
        return {"ok": True, "score_llll": message["data"], "message": message}

    @mcp.tool()
    def max_inbox_status() -> Dict[str, Any]:
        """Inspect Max->Claude inbox status."""
        latest = bach.get_latest_incoming()
        latest_score = bach.get_latest_incoming(message_type="llll")
        latest_info = bach.get_latest_incoming(message_type="info")
        return {
            "queued_messages": bach.incoming_queue_size(),
            "latest_message": latest,
            "latest_score_llll": (latest_score or {}).get("data", ""),
            "latest_info_message": (latest_info or {}).get("data", ""),
        }

    @mcp.resource("max://score/latest")
    def latest_score_resource() -> str:
        """Latest received llll score string."""
        latest = bach.get_latest_incoming(message_type="llll")
        return "" if latest is None else str(latest["data"])

    @mcp.resource("max://info/latest")
    def latest_info_resource() -> str:
        """Latest received plain process/info message."""
        latest = bach.get_latest_incoming(message_type="info")
        return "" if latest is None else str(latest["data"])

    return mcp
