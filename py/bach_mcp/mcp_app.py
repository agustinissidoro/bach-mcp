"""FastMCP app factory and tool/resource registration."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from .server import BachMCPServer


def create_mcp_app(bach: BachMCPServer) -> FastMCP:
    """Create and configure MCP tools/resources for bridge communication."""
    mcp = FastMCP("max-bridge")

    def _send_max_message(command: str) -> Dict[str, Any]:
        command = command.strip()
        if not command:
            return {"ok": False, "message": "Rejected empty process message"}
        success = bach.send_info(command)
        if not success:
            return {"ok": False, "message": "Failed to send process message to Max"}
        return {"ok": True, "sent_message": command}

    def _request_max_and_wait(command: str, timeout_seconds: float = 15.0) -> str:
        command = command.strip()
        if not command or timeout_seconds <= 0:
            return ""
        if not bach.send_info(command):
            return ""
        message = bach.wait_for_incoming(timeout_seconds=timeout_seconds, message_type=None)
        if message is None:
            return ""
        return str(message.get("data", ""))

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
    def dump(
        selection: str = "",
        mode: str = "body",
        dump_options: str = "",
        timeout_seconds: float = 15.0,
    ) -> str:
        """Send a `dump` request and return raw Max response text.

        Examples:
        - `dump()` -> `dump body`
        - `dump(mode="pitches")` -> `dump pitches`
        - `dump(selection="selection", mode="onsets")` -> `dump selection onsets`
        - `dump(mode="header")` -> `dump header`
        - `dump(mode="", dump_options="keys clefs body")` -> `dump keys clefs body`
        - `dump(selection="selection", mode="markers")` -> `dump selection markers`
        """
        selection = selection.strip()
        mode = mode.strip()
        dump_options = dump_options.strip()

        command_parts = ["dump"]
        if selection:
            command_parts.append(selection)
        if mode:
            command_parts.append(mode)
        if dump_options:
            command_parts.append(dump_options)

        command = " ".join(command_parts)
        return _request_max_and_wait(command=command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def dump_score(timeout_seconds: float = 15.0) -> str:
        """Shortcut for `dump body`; returns only the dumped score text."""
        return dump(mode="body", timeout_seconds=timeout_seconds)

    @mcp.tool()
    def dumpselection(
        router: str = "",
        start: str = "",
        end: str = "",
        timeout_seconds: float = 15.0,
    ) -> str:
        """Dump selected notation items in playout syntax and return raw response text.

        Optional attributes:
        - router: one symbol (replace standard router) or two symbols (note_router chord_router)
        - start: router marking dump start
        - end: router marking dump end
        """
        command_parts = ["dumpselection"]

        router = router.strip()
        start = start.strip()
        end = end.strip()

        if router:
            command_parts.extend(["@router", router])
        if start:
            command_parts.extend(["@start", start])
        if end:
            command_parts.extend(["@end", end])

        command = " ".join(command_parts)
        return _request_max_and_wait(command=command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def bgcolor(r: float = 1.0, g: float = 1.0, b: float = 1.0, a: float = 1.0) -> Dict[str, Any]:
        """Set bach.roll background color in RGBA format."""
        return _send_max_message(f"bgcolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def clefs(clefs_list: str = "G") -> Dict[str, Any]:
        """Set clefs; provide symbols or llll (e.g. 'G', 'FG', 'auto G FG', '[auto F G]')."""
        clefs_list = clefs_list.strip()
        if not clefs_list:
            return {"ok": False, "message": "clefs_list cannot be empty"}
        return _send_max_message(f"clefs {clefs_list}")

    @mcp.tool()
    def notecolor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> Dict[str, Any]:
        """Set note drawing color in RGBA format."""
        return _send_max_message(f"notecolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def numparts(parts: str = "1") -> Dict[str, Any]:
        """Set voice staff-ensemble grouping as int list/llll (e.g. '1 1 1 1', '2 2', '4')."""
        parts = parts.strip()
        if not parts:
            return {"ok": False, "message": "parts cannot be empty"}
        return _send_max_message(f"numparts {parts}")

    @mcp.tool()
    def numvoices(count: int) -> Dict[str, Any]:
        """Set number of voices."""
        if count <= 0:
            return {"ok": False, "message": "count must be > 0"}
        return _send_max_message(f"numvoices {int(count)}")

    @mcp.tool()
    def staffcolor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> Dict[str, Any]:
        """Set main staff color in RGBA format."""
        return _send_max_message(f"staffcolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def stafflines(value: str) -> Dict[str, Any]:
        """Set staff lines as llll or numeric pattern (e.g. '5 5', '[0 5 6] 3', '0')."""
        value = value.strip()
        if not value:
            return {"ok": False, "message": "value cannot be empty"}
        return _send_max_message(f"stafflines {value}")

    @mcp.tool()
    def voicenames(value: str) -> Dict[str, Any]:
        """Set voice names as llll (e.g. 'Foo [John Ringo] [] \"Electric Piano\"')."""
        value = value.strip()
        if not value:
            return {"ok": False, "message": "value cannot be empty"}
        return _send_max_message(f"voicenames {value}")

    @mcp.tool()
    def addmarker(
        position: str,
        name_or_names: str,
        role: str = "",
        content: str = "",
    ) -> Dict[str, Any]:
        """Add marker: addmarker <position|cursor|end> <name_llll> [role] [content_llll]."""
        position = position.strip()
        name_or_names = name_or_names.strip()
        role = role.strip()
        content = content.strip()
        if not position:
            return {"ok": False, "message": "position cannot be empty"}
        if not name_or_names:
            return {"ok": False, "message": "name_or_names cannot be empty"}

        command = f"addmarker {position} {name_or_names}"
        if role:
            command = f"{command} {role}"
            if content:
                command = f"{command} {content}"
        return _send_max_message(command)

    @mcp.tool()
    def deletemarker(marker_names: str) -> Dict[str, Any]:
        """Delete first marker matching given name list/llll."""
        marker_names = marker_names.strip()
        if not marker_names:
            return {"ok": False, "message": "marker_names cannot be empty"}
        return _send_max_message(f"deletemarker {marker_names}")

    @mcp.tool()
    def deletevoice(voice_number: int) -> Dict[str, Any]:
        """Delete N-th voice."""
        if voice_number <= 0:
            return {"ok": False, "message": "voice_number must be > 0"}
        return _send_max_message(f"deletevoice {int(voice_number)}")

    @mcp.tool()
    def explodechords(selection: str = "") -> Dict[str, Any]:
        """Explode polyphonic chords into overlapping single-note chords; optional `selection` mode."""
        selection = selection.strip()
        command = "explodechords" if not selection else f"explodechords {selection}"
        return _send_max_message(command)

    @mcp.tool()
    def exportmidi(
        filename: str = "",
        exportmarkers: int = 1,
        exportbarlines: int = 1,
        exportdivisions: int = 1,
        exportsubdivisions: int = 1,
        voices: str = "",
        format: int = 1,
        resolution: int = 960,
    ) -> Dict[str, Any]:
        """Export MIDI file with optional file name and export attributes."""
        parts = ["exportmidi"]
        filename = filename.strip()
        voices = voices.strip()
        if filename:
            parts.append(filename)
        parts.append(f"[exportmarkers {int(exportmarkers)}]")
        parts.append(f"[exportbarlines {int(exportbarlines)}]")
        parts.append(f"[exportdivisions {int(exportdivisions)}]")
        parts.append(f"[exportsubdivisions {int(exportsubdivisions)}]")
        if voices:
            parts.append(f"[voices {voices}]")
        parts.append(f"[format {int(format)}]")
        parts.append(f"[resolution {int(resolution)}]")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def getcurrentchord(timeout_seconds: float = 15.0) -> str:
        """Return playout response for notes sounding at current cursor position."""
        return _request_max_and_wait("getcurrentchord", timeout_seconds=timeout_seconds)

    @mcp.tool()
    def getnumchords(query_label: str = "", timeout_seconds: float = 15.0) -> str:
        """Return number of chords per voice; optional query label."""
        query_label = query_label.strip()
        command = "getnumchords"
        if query_label:
            command = f"getnumchords [label {query_label}]"
        return _request_max_and_wait(command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def getnumnotes(query_label: str = "", timeout_seconds: float = 15.0) -> str:
        """Return number of notes per chord for each voice; optional query label."""
        query_label = query_label.strip()
        command = "getnumnotes"
        if query_label:
            command = f"getnumnotes [label {query_label}]"
        return _request_max_and_wait(command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def getnumvoices(query_label: str = "", timeout_seconds: float = 15.0) -> str:
        """Return current number of voices; optional query label."""
        query_label = query_label.strip()
        command = "getnumvoices"
        if query_label:
            command = f"getnumvoices [label {query_label}]"
        return _request_max_and_wait(command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def glissando(trim_or_extend: str = "", slope: float = 0.0) -> Dict[str, Any]:
        """Apply glissando transform; optional `trim|extend` and slope from -1 to 1."""
        trim_or_extend = trim_or_extend.strip()
        parts = ["glissando"]
        if trim_or_extend:
            parts.append(trim_or_extend)
        parts.append(str(float(slope)))
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def insertvoice(voice_number: int, voice_or_ref: str = "") -> Dict[str, Any]:
        """Insert voice at index; optional source voice number or gathered voice llll."""
        if voice_number <= 0:
            return {"ok": False, "message": "voice_number must be > 0"}
        voice_or_ref = voice_or_ref.strip()
        command = f"insertvoice {int(voice_number)}"
        if voice_or_ref:
            command = f"{command} {voice_or_ref}"
        return _send_max_message(command)

    @mcp.tool()
    def legato(trim_or_extend: str = "") -> Dict[str, Any]:
        """Apply legato transform; optional `trim|extend` mode."""
        trim_or_extend = trim_or_extend.strip()
        command = "legato" if not trim_or_extend else f"legato {trim_or_extend}"
        return _send_max_message(command)

    @mcp.tool()
    def play(
        scheduling_mode: str = "",
        start_ms: str = "",
        end_ms: str = "",
    ) -> Dict[str, Any]:
        """Start playback with optional mode and start/end milliseconds."""
        scheduling_mode = scheduling_mode.strip()
        start_ms = start_ms.strip()
        end_ms = end_ms.strip()
        parts = ["play"]
        if scheduling_mode:
            parts.append(scheduling_mode)
        if start_ms:
            parts.append(start_ms)
        if end_ms:
            parts.append(end_ms)
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def sel(start_ms: float, end_ms: float) -> Dict[str, Any]:
        """Select notes by time range using `sel <start_ms> <end_ms>`."""
        return _send_max_message(f"sel {float(start_ms)} {float(end_ms)}")

    @mcp.tool()
    def select(start_ms: float, end_ms: float) -> Dict[str, Any]:
        """Involutive time-range selection using `select <start_ms> <end_ms>`."""
        return _send_max_message(f"select {float(start_ms)} {float(end_ms)}")

    @mcp.tool()
    def unselect(start_ms: float, end_ms: float) -> Dict[str, Any]:
        """Unselect notation items in a time range using `unsel <start_ms> <end_ms>`."""
        return _send_max_message(f"unsel {float(start_ms)} {float(end_ms)}")

    return mcp
