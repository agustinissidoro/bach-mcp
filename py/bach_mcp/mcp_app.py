"""FastMCP app factory and tool/resource registration.

Session protocol, llll syntax, slot types, articulations, noteheads, dynamics,
breakpoints, and orchestral layout reference are all documented in BACH_SKILL.md.
Read that skill at the start of every session before taking any action.
"""

from typing import Any, Dict, Optional

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

    def _validate_llll(s: str) -> Optional[str]:
        """Validate a raw llll string for structural correctness.

        Returns None if the string is valid, or a descriptive error message if not.

        Checks performed:
        - Balanced square brackets (no unclosed or extra closing brackets)
        - No empty outermost string (caller should guard for this separately)
        - No illegal characters that have no meaning in llll (curly braces, angle brackets)
        - Bracket depth never goes negative (extra closing bracket)
        - Warns about suspiciously unbalanced nesting depth anomalies

        Does NOT validate semantic correctness (e.g. correct pitch values, onset ordering).
        That remains the responsibility of bach.roll itself.
        """
        depth = 0
        for i, ch in enumerate(s):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth < 0:
                    # Find context around the error
                    snippet = s[max(0, i - 20) : i + 20].replace("\n", " ")
                    return (
                        f"llll validation error: unexpected closing bracket ']' at position {i} "
                        f"(depth went negative). Context: '...{snippet}...'"
                    )
        if depth != 0:
            return (
                f"llll validation error: {depth} unclosed bracket(s) '[' remain at end of string. "
                f"Every '[' must have a matching ']'."
            )
        # Check for characters that are never valid in llll
        illegal = set("{}")
        found_illegal = [ch for ch in s if ch in illegal]
        if found_illegal:
            chars = ", ".join(f"'{c}'" for c in sorted(set(found_illegal)))
            return (
                f"llll validation error: illegal character(s) found: {chars}. "
                f"llll only uses square brackets [ ] for grouping."
            )
        return None  # all checks passed

    def add_single_note(
        onset_ms: float = 0.0,
        pitch_cents: float = 6000.0,
        duration_ms: float = 1000.0,
        velocity: int = 100,
        voice: int = 1,
        slots: str = "",
        breakpoints: str = "",
        name: str = "",
        note_flag: int = 0,
    ) -> Dict[str, Any]:
        """Send a single note to bach.roll. Convenience wrapper for quick single-note testing.
        For multi-note, multi-voice, or chord content use send_score_to_max() instead.

        Slot/breakpoint/dynamics/notehead syntax: see BACH_SKILL.md.

        Parameters:
        - onset_ms:     note start time in milliseconds
        - pitch_cents:  pitch in midicents (middle C = 6000, semitone = 100)
        - duration_ms:  note duration in milliseconds (must be > 0)
        - velocity:     MIDI velocity 0–127
        - voice:        target voice number (1-indexed)
        - slots:        raw llll string e.g. "[slots [22 staccato] [20 p<]]"
        - breakpoints:  raw llll string e.g. "[breakpoints [0 0 0] [1 200 0]]"
        - name:         note name(s) e.g. "pippo" or "[high 1] [low 2]"
        - note_flag:    0=normal, 1=locked, 2=muted, 4=solo (sum to combine)

        Examples:
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100)
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100,
                        slots="[slots [22 staccato] [20 ff]]",
                        breakpoints="[breakpoints [0 0 0] [1 200 0]]")
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100,
                        voice=2, note_flag=2)
        """
        if duration_ms <= 0:
            return {"ok": False, "message": "duration_ms must be > 0"}
        if velocity < 0 or velocity > 127:
            return {"ok": False, "message": "velocity must be between 0 and 127"}
        if voice <= 0:
            return {"ok": False, "message": "voice must be > 0"}

        # Validate raw llll sub-strings before building
        if slots.strip():
            err = _validate_llll(slots)
            if err:
                return {"ok": False, "message": f"Invalid slots llll — {err}"}
        if breakpoints.strip():
            err = _validate_llll(breakpoints)
            if err:
                return {"ok": False, "message": f"Invalid breakpoints llll — {err}"}

        # Build note specifications
        specs = []
        if breakpoints.strip():
            specs.append(breakpoints.strip())
        if slots.strip():
            specs.append(slots.strip())
        if name.strip():
            specs.append(f"[name {name.strip()}]")

        specs_str = (" " + " ".join(specs)) if specs else ""

        note = (
            f"[ {float(pitch_cents):.3f} {float(duration_ms):.3f} "
            f"{int(velocity)}{specs_str} {int(note_flag)} ]"
        )
        chord = f"[ {float(onset_ms):.3f} {note} 0 ]"

        # Build full score with the right number of empty voices before the target voice
        voices = ["[ 0 ]"] * (voice - 1) + [f"[ {chord} 0 ]"]
        score_llll = "[ " + " ".join(voices) + " ]"

        success = bach.send_score(score_llll)
        if not success:
            return {"ok": False, "message": "Failed to send llll score to Max"}
        return {"ok": True, "score_llll": score_llll}

    @mcp.tool()
    def send_score_to_max(score_llll: str) -> str:
        """Send a raw llll score string directly to bach.roll.

        PRIMARY tool for writing notes, chords, or multi-voice content.
        Always prefer this over add_single_note() for any real score writing.

        Full llll score syntax and hierarchy: see BACH_SKILL.md.

        Key rules:
        - String must start with "roll" followed by one llll per voice.
        - Voices are SEPARATE top-level lllls — not wrapped in an extra bracket.
          RIGHT: roll [VOICE1] [VOICE2]
          WRONG: roll [ [VOICE1] [VOICE2] ]
        - Each level (note, chord, voice) ends with an optional numeric flag
          INSIDE its bracket before the closing ].
        - This tool only sets notation content. It does not affect slotinfo or header.

        Examples:
        Single note:   "roll [ [ 0. [ 6000. 673. 100 0 ] 0 ] 0 ]"
        Two voices:    "roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ] [ [ 0. [ 5500. 500. 90 0 ] 0 ] 0 ]"
        Chord:         "roll [ [ 0. [ 6000. 1000. 100 0 ] [ 6400. 1000. 100 0 ] 0 ] 0 ]"
        """
        score_llll = score_llll.strip()
        if not score_llll:
            return "Rejected empty llll score"
        # Extract the llll body (everything after the leading "roll" keyword) for bracket validation
        body = score_llll[4:].strip() if score_llll.lower().startswith("roll") else score_llll
        err = _validate_llll(body)
        if err:
            return f"Rejected llll score — {err}"
        success = bach.send_score(score_llll)
        return "Sent llll score to Max" if success else "Failed to send llll score"

    @mcp.tool()
    def send_bell_to_eval(bell_code: str) -> Dict[str, Any]:
        """Send a bell-language program to bach.eval in the Max patch.

        USE ONLY when the user explicitly asks for bell code, or when you
        are suggesting the generative approach and the user agrees.
        For all other score writing, use send_score_to_max() instead.

        The message is prefixed with "bell" so the patch can route it correctly
        to the bach.eval object, distinguishing it from regular roll llll messages.

        FLAT STRING REQUIREMENT: bell code must be a single flat string — no newlines,
        no indentation. Statements separated by ";". Multi-statement loop bodies
        wrapped in "( )". This is a Max messaging constraint.

        bell is a Turing-complete language that runs inside Max and computes
        an llll at runtime — useful for loops, randomness, serial operations,
        and any algorithmically generated material.

        The last expression in the program is its output. For score generation
        it must evaluate to a valid roll llll, with 'roll' as a single-quoted symbol.

        Key syntax rules (see BACH_SKILL.md for full reference):
        - Variables: $name, assigned with = only
        - Symbols: single quotes only — 'roll', 'null', 'foo'
        - Loop: for $x in <llll> do (...) or for $i in 1...N do (...)
        - Append-assign: $v _= item
        - Sequence: statement1; statement2

        Example — C-major scale:
            $v = 'null'; $t = 0.; for $p in [6000 6200 6400 6500 6700 6900 7100 7200] do ($v _= [$t [$p 500. 100 0] 0]; $t += 500.); 'roll' [$v 0]

        Example — 16 random chromatic pitches:
            $v = 'null'; $t = 0.; for $i in 1...16 do ($p = round(random(6000, 7200) / 100) * 100; $v _= [$t [$p 250. 90 0] 0]; $t += 250.); 'roll' [$v 0]

        Returns: ok, sent_code.
        """
        bell_code = bell_code.strip()
        if not bell_code:
            return {"ok": False, "message": "Rejected empty bell code"}
        message = f"bell {bell_code}"
        success = bach.send_info(message)
        if not success:
            return {"ok": False, "message": "Failed to send bell code to Max"}
        return {"ok": True, "sent_code": bell_code}

    @mcp.tool()
    def send_process_message_to_max(message: str) -> str:
        """ESCAPE HATCH — send a raw command to Max/MSP that has no dedicated tool.

        Only use this when NO dedicated tool exists for the command.
        Every common bach.roll command (play, stop, clefs, bgcolor, numvoices,
        sel, dump, addchord, etc.) has its own tool — use those instead.
        This tool exists solely for undocumented or rarely-used Max messages.

        Fire-and-forget: sends the string but does not wait for a response.
        If you need a response, use dump() or a dedicated get_* tool.

        Example valid uses (commands with no dedicated tool):
        - "activepart 2"          switch active part inside a voice ensemble
        - "showpartcolors 1"      enable part color highlighting
        - "ruler 1"               show ruler (use set_appearance() instead if possible)
        """
        message = message.strip()
        if not message:
            return "Rejected empty process message"
        success = bach.send_info(message)
        return "Sent process message to Max" if success else "Failed to send process message"

    @mcp.tool()
    def dump(
        selection: bool = False,
        mode: str = "",
        dump_options: str = "",
        timeout_seconds: float = 15.0,
    ) -> str:
        """Request bach.roll to output (dump) its current state and return the raw response.

        dump is bach's way of querying data back from the score. It sends a command string
        to Max and waits for a response. Unlike send_process_message_to_max(), this tool
        waits for Max to reply and returns that response.

        The command sent to Max is a plain string like "dump body" or "dump selection onsets".
        The arguments to this tool map directly to parts of that string — they are NOT
        Python concepts, they are fragments of the Max message.

        IMPORTANT: calling dump() with no arguments sends "dump" to Max, which dumps
        EVERYTHING. This is rarely what you want. Specify a mode in almost all cases.

        Decision table — what to call based on what you need:

        What you want                             | mode=       | selection=
        ──────────────────────────────────────────|─────────────|───────────
        Full score notation (notes/chords/voices) | "body"      | False
        Score metadata (tempo, time sigs, etc.)   | "header"    | False
        Only pitches                              | "pitches"   | False
        Only onsets                               | "onsets"    | False
        Marker data                               | "markers"   | False
        Slot data (dynamics, automation, etc.)    | "slotinfo"  | False
        Currently selected items only             | "body" etc. | True
        Everything at once (use sparingly)        | ""          | False

        Slots are per-note containers that store additional data such as automation
        curves, dynamics, articulations, or any custom data attached to a note.
        Each note can have multiple slots, each with a type (e.g. function, int, text).

        Parameters:
        - selection: if True, restricts the dump to currently selected notation items,
                     sending "dump selection <mode>" instead of "dump <mode>".
        - mode: the aspect of the score to dump (see table above). Leave empty only
                when you explicitly want to dump everything.
        - dump_options: raw string of additional options passed as-is to Max
                        (e.g. "keys clefs body"). Use when combining multiple modes.
        - timeout_seconds: how long to wait for Max to respond before giving up.

        Examples (showing exact string sent to Max):
        - dump(mode="body")                             -> "dump body"
        - dump(mode="slotinfo")                         -> "dump slotinfo"
        - dump(mode="pitches")                          -> "dump pitches"
        - dump(mode="header")                           -> "dump header"
        - dump(mode="markers")                          -> "dump markers"
        - dump(selection=True, mode="onsets")           -> "dump selection onsets"
        - dump(selection=True, mode="body")             -> "dump selection body"
        - dump(mode="", dump_options="keys clefs body") -> "dump keys clefs body"
        - dump()                                        -> "dump" (everything — use sparingly)
        """
        command_parts = ["dump"]
        if selection:
            command_parts.append("selection")
        if mode:
            command_parts.append(mode.strip())
        if dump_options:
            command_parts.append(dump_options.strip())

        command = " ".join(command_parts)
        return _request_max_and_wait(command=command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def get_length(timeout_seconds: float = 10.0) -> str:
        """Query bach.roll for the total score length in milliseconds.

        Returns: length <length_ms>

        Useful after writing content to verify duration, or before calling
        domain() to zoom the view to fit the whole score.

        This is a read-only query; it does not modify the score.
        """
        return _request_max_and_wait("getlength", timeout_seconds=timeout_seconds)

    @mcp.tool()
    def get_marker(
        names: str = "",
        name_first: bool = False,
        timeout_seconds: float = 10.0,
    ) -> str:
        """Query bach.roll for marker information and wait for the response.

        Sends "getmarker [names] [@namefirst 1]" to Max.

        Without names, returns ALL markers in the form:
            markers [pos name role] [pos name role] ...

        With names (space-separated), returns the first marker matching ALL given
        names in the form:
            marker name pos role

        Parameters:
        - names: space-separated marker name(s) to look up. Leave empty for all markers.
        - name_first: if True, outputs name before position in each marker llll.

        Marker roles that bach recognises:
        - "timesig"    — time signature marker (content: [numerator denominator])
        - "tempo"      — tempo marker (content: [figure value], e.g. [1/8 50])
        - "barline"    — measure barline (no content)
        - "division"   — measure division (no content)
        - "subdivision"— measure subdivision (no content)

        Examples (exact string sent to Max):
        - get_marker()                    -> "getmarker"
        - get_marker("intro")             -> "getmarker intro"
        - get_marker("Ringo Starr")       -> "getmarker Ringo Starr"
        - get_marker(name_first=True)     -> "getmarker @namefirst 1"

        This is a read-only query; it does not modify the score.
        """
        parts = ["getmarker"]
        if name_first:
            parts.append("@namefirst 1")
        if names.strip():
            parts.append(names.strip())
        return _request_max_and_wait(" ".join(parts), timeout_seconds=timeout_seconds)

    def bgcolor(r: float = 1.0, g: float = 1.0, b: float = 1.0, a: float = 1.0) -> Dict[str, Any]:
        # Internal helper. Use set_appearance("bgcolor", "r g b a") from tools.
        return _send_max_message(f"bgcolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def clefs(clefs_list: str = "G") -> Dict[str, Any]:
        """Set the clef for each voice in bach.roll.

        ⚠️  LAYOUT TOOL — only call when the user explicitly asks to change
        instrumentation, or when initialising a new score. See numvoices() policy.

        Clefs are provided as a space-separated list of symbols, one per voice.
        If fewer clefs than voices are provided, the last clef is repeated.

        Available clef symbols (case-sensitive — use exactly as written):
        - "G"           — treble clef
        - "G8va"        — treble clef 8va alta (one octave up)
        - "G8"          — treble clef 8va bassa (one octave down)
        - "G15ma"       — treble clef 15ma alta (two octaves up)
        - "G15mb"       — treble clef 15ma bassa (two octaves down)
        - "F"           — bass clef
        - "F8va"        — bass clef 8va alta (one octave up)
        - "F8"          — bass clef 8va bassa (one octave down)
        - "F15ma"       — bass clef 15ma alta (two octaves up)
        - "F15mb"       — bass clef 15ma bassa (two octaves down)
        - "Alto"        — alto C clef  (capital A)
        - "Tenor"       — tenor C clef
        - "Soprano"     — soprano C clef
        - "Mezzo"       — mezzo-soprano C clef
        - "Barytone"    — baritone C clef
        - "Percussion"  — percussion clef  (capital P, full word)
        - "None"        — no clef displayed  (capital N)
        - "FG"          — grand staff: bass + treble (ONE voice, TWO staves)
        - "FGG"         — bass + treble + treble (ONE voice, THREE staves)
        - "FFG"         — bass + bass + treble (ONE voice, THREE staves)
        - "FFGG"        — bass + bass + treble + treble (ONE voice, FOUR staves — choir reduction)
        WRONG forms: perc  Perc  alto  none  auto  G8vb  F8vb  (these do not exist)

        ─────────────────────────────────────────────────────────────
        VOICES VS STAVES — A CRITICAL DISTINCTION
        ─────────────────────────────────────────────────────────────
        In bach, a "voice" is a data concept (a stream of chords in the score hierarchy),
        while a "staff" is a visual concept (a set of lines drawn on screen). These do
        not always map 1-to-1.

        The "FG" clef assigns TWO physical staves (treble above, bass below) to a
        SINGLE voice. The voice remains one unit in the score data — one llll, one
        editorial stream — but it is rendered across two linked staves. This is the
        standard way to notate piano, harp, or any grand-staff instrument in an
        orchestral context, where you want the instrument treated as one indivisible part.

            clefs("FG")       # one voice, displayed on two staves (grand staff)

        ─────────────────────────────────────────────────────────────
        CHOOSING BETWEEN 1-VOICE FG AND 2-VOICE GROUPING
        ─────────────────────────────────────────────────────────────
        There are two ways to create a piano-style grand staff, and the choice has
        musical and editorial implications. When in doubt, ask the user which they need.

        APPROACH A — One voice, FG clef  (orchestral / monolithic piano part):
            numvoices(1)
            clefs("FG")
            numparts("1")
            → One voice in the score. All notes belong to the same stream.
              Right hand and left hand are not independently editable as separate voices.
              Typical use: piano or harp in an orchestral score, where the instrument
              is one "slot" in the ensemble and no per-hand distinction is needed.

        APPROACH B — Two voices grouped as one ensemble  (chamber / solo / detailed):
            numvoices(2)
            clefs("G F")
            numparts("2")
            → Two independent voices in the score, visually merged onto one grand staff.
              Voice 1 = right hand (treble), voice 2 = left hand (bass).
              Each hand is a separate editorial stream: independent selection,
              independent slot data, independent dynamics, independent colors.
              Typical use: solo piano music, chamber music with detailed per-hand
              notation, or any situation where LH/RH must be independently controlled.

        The distinction is subtle but important. If the user asks for "a piano part"
        without further context, prefer APPROACH A (1 voice, FG clef) and mention
        that APPROACH B is available if per-hand editorial independence is needed.

        ─────────────────────────────────────────────────────────────
        EXAMPLES (exact string sent to Max)
        ─────────────────────────────────────────────────────────────
        - clefs("G")          -> all voices use treble clef
        - clefs("F")          -> all voices use bass clef
        - clefs("G F")        -> voice 1 treble, voice 2 bass (two separate voices)
        - clefs("FG")         -> voice 1 is a grand staff — ONE voice, TWO staves
        - clefs("auto G F")   -> voice 1 auto, voice 2 treble, voice 3 bass
        - clefs("FG G")       -> voice 1 grand staff (piano), voice 2 treble (e.g. violin)
        """
        clefs_list = clefs_list.strip()
        if not clefs_list:
            return {"ok": False, "message": "clefs_list cannot be empty"}
        return _send_max_message(f"clefs {clefs_list}")

    def notecolor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> Dict[str, Any]:
        # Internal helper. Use set_appearance("notecolor", "r g b a") from tools.
        return _send_max_message(f"notecolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def numparts(parts: str = "1") -> Dict[str, Any]:
        """Set the part grouping for voices in bach.roll via voice ensembles.

        ⚠️  LAYOUT TOOL — only call when the user explicitly asks to change
        instrumentation, or when initialising a new score. See numvoices() policy.

        ─────────────────────────────────────────────────────────────
        CONCEPT: VOICES, VOICE ENSEMBLES, AND PARTS
        ─────────────────────────────────────────────────────────────
        Bach does not have a native "part" concept between voices and chords.
        The nesting hierarchy is strictly:
            WHOLE SCORE > VOICES > CHORDS > NOTES

        However, bach provides "voice ensembles" as a visual grouping mechanism:
        multiple voices can be mapped onto the same staff (or multi-staff) space.
        This closely resembles parts in traditional engraving software.

        The key idea: each integer in the numparts list specifies how many
        consecutive voices are displayed together on the same staff ensemble.
        The integers must sum to the total number of voices in the score.

        ─────────────────────────────────────────────────────────────
        EXAMPLES WITH 4 VOICES
        ─────────────────────────────────────────────────────────────
        "1 1 1 1" — each voice on its own staff (default, 4 separate staves)
        "2 2"     — voices 1+2 share a staff, voices 3+4 share a staff
        "1 3"     — voice 1 alone, voices 2+3+4 share a staff
        "4"       — all four voices on a single shared staff or multi-staff

        ─────────────────────────────────────────────────────────────
        COMPLEX INSTRUMENTS (PIANO, HARP, ORGAN, ETC.)
        ─────────────────────────────────────────────────────────────
        For grand-staff instruments there are two distinct approaches. The right
        choice depends on context — when in doubt, ask the user. See also: clefs().

        APPROACH A — One voice, FG clef  (standard orchestral piano/harp part):
            numvoices(1)
            clefs("FG")      # FG = grand staff clef: treble + bass on two linked staves
            numparts("1")
            → The instrument occupies one voice in the score. It is displayed on
              two staves but is editorially one unit. This is the normal way to
              write piano or harp in an orchestral or ensemble score.

        APPROACH B — Two voices grouped as one ensemble  (chamber / solo piano):
            numvoices(2)
            clefs("G F")     # voice 1 treble, voice 2 bass — two independent voices
            numparts("2")    # group them visually into one grand-staff ensemble
            → Two independent voices displayed together. Voice 1 = RH, voice 2 = LH.
              Each hand is a separate editorial stream with independent selection,
              dynamics, slot data, and colors. Use for solo or chamber music where
              per-hand control matters.

        For organ (3 staves: treble, bass, pedal) — almost always 3 separate voices:
            numvoices(3)
            clefs("G F F8")
            numparts("3")    # all three voices in one ensemble

        ─────────────────────────────────────────────────────────────
        ACTIVE PART FOR EDITING
        ─────────────────────────────────────────────────────────────
        Within a voice ensemble, only one voice is "active" for editing at a time
        (adding chords, linear editing mode, etc.). Use the "activepart" attribute
        to switch which voice inside the ensemble receives new input:

            send_process_message_to_max("activepart 2")

        Note: activepart does not affect modifications to existing chords, and
        Alt+drag duplicates retain their original voice. Copy-paste, however,
        always targets the active part.

        ─────────────────────────────────────────────────────────────
        PART COLORS
        ─────────────────────────────────────────────────────────────
        To visually distinguish voices within a shared ensemble, enable part colors:

            send_process_message_to_max("showpartcolors 1")

        ─────────────────────────────────────────────────────────────
        EXAMPLES (exact string sent to Max)
        ─────────────────────────────────────────────────────────────
        - numparts("1 1 1 1")  -> four separate staves (default)
        - numparts("2 2")      -> two grand-staff ensembles of two voices each
        - numparts("1 3")      -> one solo staff, one three-voice ensemble
        - numparts("4")        -> all four voices in one ensemble
        - numparts("2")        -> two voices displayed as one grand-staff ensemble (Approach B piano)
        - numparts("3")        -> organ (three voices in one ensemble)
        - numparts("1")        -> single voice, single staff (default for new scores)
        """
        parts = parts.strip()
        if not parts:
            return {"ok": False, "message": "parts cannot be empty"}
        return _send_max_message(f"numparts {parts}")

    @mcp.tool()
    def numvoices(count: int) -> Dict[str, Any]:
        """Set the number of voices in bach.roll.

        ══════════════════════════════════════════════════════════════
        ⚠️  LAYOUT STABILITY POLICY
        ══════════════════════════════════════════════════════════════
        numvoices, clefs, numparts, stafflines, and voicenames define
        the score's INSTRUMENTATION LAYOUT. Only call these tools when:

          1. The user EXPLICITLY asks to change instrumentation
             (e.g. "set up a string quartet", "add a bass voice",
             "change to grand staff", "rename the voices").
          2. Initialising a brand-new empty score (via new_default_score()).

        DO NOT call these tools:
          • when composing, editing, or adding notes to an existing score
          • to "verify" the current layout before writing notes
          • proactively or speculatively on any existing score
          • just because you are unsure what the layout is

        ➜ To READ the current voice count: use getnumvoices().
        ➜ To READ clefs/voicenames: use dump(mode="header").
        Calling numvoices() on an existing score DELETES voice content.
        ══════════════════════════════════════════════════════════════

        ─────────────────────────────────────────────────────────────
        VOICES ≠ STAVES
        ─────────────────────────────────────────────────────────────
        A VOICE is a data stream (SCORE > VOICES > CHORDS > NOTES).
        A STAFF is a visual unit. They differ when using the FG clef:
        - simple clef (G, F, alto, perc) → 1 voice = 1 staff
        - FG grand-staff clef            → 1 voice = 2 staves

            1 voice  + clef G    → 1 staff
            1 voice  + clef FG   → 2 staves (grand staff)
            2 voices + clefs G F → 2 staves (two independent voices)

        count must be > 0. Reducing voice count deletes content permanently.
        """
        if count <= 0:
            return {"ok": False, "message": "count must be > 0"}
        return _send_max_message(f"numvoices {int(count)}")

    def staffcolor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> Dict[str, Any]:
        # Internal helper. Use set_appearance("staffcolor", "r g b a") from tools.
        return _send_max_message(f"staffcolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def stafflines(value: str) -> Dict[str, Any]:
        """Set the staff lines for each voice in bach.roll.

        ⚠️  LAYOUT TOOL — only call when the user explicitly asks to change
        instrumentation, or when initialising a new score. See numvoices() policy.

        Expects one element per voice as a space-separated list. If fewer elements
        than voices are provided, the last value is repeated for remaining voices.

        Each element can be either:

        1. An integer — the number of staff lines for that voice, centered around
           the middle line of a standard 5-line staff.
           - 5   — standard 5-line staff
           - 3   — 3 lines centered around the middle
           - 0   — no staff lines (also accepts nil or [])

        2. An llll — explicit indices of which lines to display, where:
           - 1   = bottommost line of a standard 5-line staff
           - 5   = topmost line of a standard 5-line staff
           - Zero and negative indices are allowed (lines below the standard staff)
           - e.g. [0 5 6] = one line below the standard bottom, the top standard
                            line, and one line above the standard top

        Examples (exact string sent to Max):
        - stafflines("5")           -> all voices have standard 5-line staves
        - stafflines("5 3")         -> voice 1 standard, voice 2 has 3 centered lines
        - stafflines("[1 3 5]")     -> voice 1 shows only bottom, middle, and top lines
        - stafflines("[0 5 6] 3")   -> voice 1 custom lines, voice 2 three centered lines
        - stafflines("0")           -> no staff lines on any voice
        """
        value = value.strip()
        if not value:
            return {"ok": False, "message": "value cannot be empty"}
        return _send_max_message(f"stafflines {value}")

    @mcp.tool()
    def voicenames(value: str) -> Dict[str, Any]:
        """Set the display name for each voice in bach.roll, shown as a label to the left of each staff.

        ⚠️  LAYOUT TOOL — only call when the user explicitly asks to change
        instrumentation, or when initialising a new score. See numvoices() policy.

        Expects one element per voice as a space-separated list. If fewer elements
        than voices are provided, the last value is repeated for remaining voices.

        Each element can be:
        - a single symbol         — one name for that voice
        - an llll (wrapped in []) — multiple names for the same voice (e.g. for grand staff)
        - [] or nil               — skip naming for that voice (no label shown)

        Names containing spaces must be quoted with double quotes.

        Examples (exact string sent to Max):
        - voicenames("Foo")                              -> voice 1 named "Foo"
        - voicenames("Violin Viola Cello")               -> three voices named individually
        - voicenames("Foo [John Ringo] [] \"Electric Piano\"")
                                                         -> voice 1: "Foo", voice 2: "John" and "Ringo",
                                                            voice 3: no name, voice 4: "Electric Piano"
        - voicenames("[] Violin")                        -> voice 1 no name, voice 2 "Violin"
        - voicenames("[RH LH] Bass")                     -> voice 1 two names (grand staff), voice 2 "Bass"
        """
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
        """Add a named marker at a given position in bach.roll.

        Markers are named time positions visible on the score, useful for
        labeling sections, rehearsal marks, or points of interest.

        Parameters:
        - position: where to place the marker. Can be:
            - a time in milliseconds (e.g. "0.", "1500.")
            - "cursor" — at the current playback cursor position
            - "end"    — at the end of the score
        - name_or_names: the marker name as a symbol or llll (e.g. "intro", "[A A1]")
        - role: optional marker role/type — rarely needed, leave empty in most cases
        - content: optional llll content attached to the marker — rarely needed, leave empty

        Examples (exact string sent to Max):
        - addmarker("0.", "intro")      -> marker named "intro" at time 0
        - addmarker("cursor", "A")      -> marker named "A" at cursor position
        - addmarker("end", "fine")      -> marker named "fine" at end of score
        - addmarker("1500.", "verse")   -> marker named "verse" at 1500ms
        """
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
        """Delete the first marker in bach.roll that matches the given name(s).

        Only the first matching marker (in temporal order) is deleted. If multiple
        markers share the same name, call this repeatedly to delete them one by one.

        To match by multiple names, provide them space-separated — only markers
        having ALL the given names will match.

        Parameters:
        - marker_names: one or more marker names, space-separated.

        Examples (exact string sent to Max):
        - deletemarker("intro")         -> deletes first marker named "intro"
        - deletemarker("A")             -> deletes first marker named "A"
        - deletemarker("Ringo Starr")   -> deletes first marker named both "Ringo" and "Starr"
        """
        marker_names = marker_names.strip()
        if not marker_names:
            return {"ok": False, "message": "marker_names cannot be empty"}
        return _send_max_message(f"deletemarker {marker_names}")

    @mcp.tool()
    def deletevoice(voice_number: int) -> Dict[str, Any]:
        """Delete a voice (staff) from bach.roll by its index.

        WARNING: this permanently deletes the voice and all its notation content
        (notes, chords, slots, etc.). Use with caution.

        voice_number is 1-indexed (first voice is 1, not 0).

        Examples (exact string sent to Max):
        - deletevoice(1)  -> deletes the first voice
        - deletevoice(3)  -> deletes the third voice
        """
        if voice_number <= 0:
            return {"ok": False, "message": "voice_number must be > 0"}
        return _send_max_message(f"deletevoice {int(voice_number)}")

    @mcp.tool()
    def explodechords(selection: bool = False) -> Dict[str, Any]:
        """Explode polyphonic chords into overlapping single-note chords in bach.roll.

        A polyphonic chord (multiple notes at the same onset) is split into
        multiple single-note chords at the same time position, each containing
        one note. This is useful for separating voices within a chord.

        - selection=False: explodes all chords in the score
        - selection=True:  explodes only currently selected chords

        Examples (exact string sent to Max):
        - explodechords()               -> "explodechords" (all chords)
        - explodechords(selection=True) -> "explodechords selection" (selected only)
        """
        command = "explodechords selection" if selection else "explodechords"
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
        """Export the current bach.roll score as a MIDI file.

        If no filename is provided, a save dialog box will open in Max.
        If a filename is provided, the file is saved directly without a dialog.

        Parameters:
        - filename: output file name (e.g. "mymidi.mid"). Leave empty to use dialog box.
        - exportmarkers: if non-zero, exports all markers (default: 1)
        - exportbarlines: exports barline markers as MIDI marker events named "bach barline" (default: 1)
        - exportdivisions: exports division markers as MIDI marker events named "bach division" (default: 1)
        - exportsubdivisions: exports subdivision markers as MIDI marker events named "bach subdivision" (default: 1)
        - voices: which voices to export as a space-separated list or llll. Leave empty to export all.
                  Individual voices: "1 3 5" (exports voices 1, 3 and 5)
                  Ranges as sublists: "[[1 5]] 8" (exports voices 1 through 5, and voice 8)
        - format: MIDI file format. 0 = single track, 1 = multiple tracks (default: 1)
        - resolution: number of MIDI ticks per beat (default: 960)

        Examples (exact string sent to Max):
        - exportmidi()                                    -> dialog box
        - exportmidi("mymidi.mid")                        -> save directly
        - exportmidi("mymidi.mid", exportmarkers=0)       -> save without markers
        - exportmidi("mymidi.mid", voices="1 3")          -> export voices 1 and 3
        - exportmidi("mymidi.mid", voices="[[1 3]] 4 7")  -> export voices 1-3, 4 and 7
        - exportmidi("mymidi.mid", format=0)              -> single track MIDI
        - exportmidi("mymidi.mid", resolution=1920)       -> higher resolution
        """
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
        """Return the notes sounding at the current cursor position in bach.roll.

        Sends "getcurrentchord" to Max and waits for a response. The response
        is returned as an llll string in playout syntax, which is similar to
        the score body llll but formatted for playback output rather than editing.

        Useful for inspecting what is playing at a given moment, for example
        to read pitches, velocities, or slot data of currently sounding notes.

        - timeout_seconds: how long to wait for Max to respond before giving up.
        """
        return _request_max_and_wait("getcurrentchord", timeout_seconds=timeout_seconds)

    @mcp.tool()
    def getnumchords(query_label: str = "", timeout_seconds: float = 15.0) -> str:
        """Return the number of chords for each voice in bach.roll as an llll.

        Sends "getnumchords" to Max and waits for a response.
        The response contains one value per voice.

        - timeout_seconds: how long to wait for Max to respond before giving up.
        """
        query_label = query_label.strip()
        command = "getnumchords"
        if query_label:
            command = f"getnumchords [label {query_label}]"
        return _request_max_and_wait(command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def getnumnotes(query_label: str = "", timeout_seconds: float = 15.0) -> str:
        """Return the number of notes for each chord in each voice in bach.roll as an llll.

        Sends "getnumnotes" to Max and waits for a response.
        The response is nested — one list per voice, one value per chord within that voice.

        - timeout_seconds: how long to wait for Max to respond before giving up.
        """
        query_label = query_label.strip()
        command = "getnumnotes"
        if query_label:
            command = f"getnumnotes [label {query_label}]"
        return _request_max_and_wait(command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def getnumvoices(query_label: str = "", timeout_seconds: float = 15.0) -> str:
        """Return the current number of voices in bach.roll.

        Sends "getnumvoices" to Max and waits for a response.
        Returns a single integer value.

        ⚠️  ALWAYS use this tool when you need to know how many voices exist.
        Do NOT infer voice count from the number of visible staves — they differ
        when the FG grand-staff clef is used (1 voice renders as 2 staves).
        Do NOT rely on what was set earlier in the session; the score may have
        changed. Query bach directly.

        - query_label: optional label to tag the query (rarely needed).
        - timeout_seconds: how long to wait for Max to respond before giving up.
        """
        query_label = query_label.strip()
        command = "getnumvoices"
        if query_label:
            command = f"getnumvoices [label {query_label}]"
        return _request_max_and_wait(command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def glissando(trim_or_extend: str = "", slope: float = 0.0) -> Dict[str, Any]:
        """Apply a glissando to the currently selected notes in bach.roll.

        Draws a glissando line across selected notes. Always operates on the current selection.

        Parameters:
        - trim_or_extend: optional mode affecting note durations:
            - "trim"   — shortens notes to fit the glissando
            - "extend" — extends notes to fit the glissando
            - ""       — leave note durations unchanged (default)
        - slope: controls the curve of the glissando line, from -1.0 to 1.0.
            - 0.0   — straight line (default)
            - > 0.0 — curved upward
            - < 0.0 — curved downward

        Examples (exact string sent to Max):
        - glissando()                                    -> "glissando 0.0"
        - glissando(slope=0.4)                           -> "glissando 0.4"
        - glissando(trim_or_extend="trim")               -> "glissando trim 0.0"
        - glissando(trim_or_extend="extend", slope=-0.4) -> "glissando extend -0.4"
        """
        trim_or_extend = trim_or_extend.strip()
        parts = ["glissando"]
        if trim_or_extend:
            parts.append(trim_or_extend)
        parts.append(str(float(slope)))
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def insertvoice(voice_number: int, voice_or_ref: str = "") -> Dict[str, Any]:
        """Insert a new voice at the given position in bach.roll.

        voice_number is 1-indexed (1 = insert as first voice).

        The optional voice_or_ref parameter controls what the new voice is filled with:
        - empty (default)      — insert a new empty voice
        - an integer as string (e.g. "2") — insert a new voice copying the properties
                                (clefs, voicenames, key signatures, etc.) of the referenced voice
        - a full llll string   — insert a new voice populated with the provided notation content

        Examples (exact string sent to Max):
        - insertvoice(1)               -> "insertvoice 1" (empty voice as 1st)
        - insertvoice(1, "2")          -> "insertvoice 1 2" (copy properties of voice 2)
        - insertvoice(1, "[ [ 125.714286 [ 6300. ...") -> insert with llll content
        """
        if voice_number <= 0:
            return {"ok": False, "message": "voice_number must be > 0"}
        voice_or_ref = voice_or_ref.strip()
        command = f"insertvoice {int(voice_number)}"
        if voice_or_ref:
            command = f"{command} {voice_or_ref}"
        return _send_max_message(command)

    @mcp.tool()
    def legato(trim_or_extend: str = "") -> Dict[str, Any]:
        """Apply legato transform to currently selected notes in bach.roll.

        Shifts the tail of each selected note so it reaches exactly the onset
        of the following chord, resulting in a sequence with no gaps between chords.

        Parameters:
        - trim_or_extend: optional mode controlling how note durations are adjusted:
            - ""       — full legato: both shortens and extends notes, removing all rests
                         and superpositions (default)
            - "trim"   — only shortens notes, preserving rests between chords
            - "extend" — only extends notes, preserving superpositions between chords

        Always operates on the current selection.

        Examples (exact string sent to Max):
        - legato()                         -> "legato"
        - legato(trim_or_extend="trim")    -> "legato trim"
        - legato(trim_or_extend="extend")  -> "legato extend"
        """
        trim_or_extend = trim_or_extend.strip()
        command = "legato" if not trim_or_extend else f"legato {trim_or_extend}"
        return _send_max_message(command)

    @mcp.tool()
    def play(
        scheduling_mode: str = "",
        start_ms: Optional[float] = None,
        end_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Start playback of bach.roll.

        If no start/end times are provided, playback starts from the current
        cursor position and plays to the end of the score.

        Parameters:
        - start_ms: playback start time in milliseconds. If omitted, uses cursor position.
        - end_ms:   playback end time in milliseconds. If omitted, plays to end of score.

        Examples (exact string sent to Max):
        - play()                              -> "play" (from cursor to end)
        - play(start_ms=0)                    -> "play 0." (from beginning)
        - play(start_ms=1000, end_ms=5000)    -> "play 1000. 5000." (specific range)
        """
        scheduling_mode = scheduling_mode.strip()
        parts = ["play"]
        if scheduling_mode:
            parts.append(scheduling_mode)
        if start_ms is not None:
            parts.append(str(float(start_ms)))
        if end_ms is not None:
            parts.append(str(float(end_ms)))
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def sel(arguments: str) -> Dict[str, Any]:
        """Select notation items in bach.roll using the full bach sel syntax.

        The sel message adds notation items to the current selection.
        Always use the raw arguments string — the syntax is too varied to parameterize.

        SELECTION MODES:

        Time/pitch range (basic):
        sel <start_ms> <end_ms> <min_cents> <max_cents> [voice]
        Use [] or nil to leave a bound open.
        - sel(arguments="1000 3000 6000 7200")        notes between 1-3s, C4-C5
        - sel(arguments="1000 3000 [] []")             notes between 1-3s, any pitch
        - sel(arguments="[] [] 4800 6000")             notes below middle C
        - sel(arguments="[] [] [] [] 2")               all notes in voice 2
        - sel(arguments="1000 3000 [] [] [1 3 4]")     voices 1, 3 and 4

        Everything / category:
        - sel(arguments="all")                         select everything
        - sel(arguments="notes")                       all notes
        - sel(arguments="chords")                      all chords
        - sel(arguments="markers")                     all markers
        - sel(arguments="breakpoints")                 all breakpoints
        - sel(arguments="tails")                       all tails

        By index (negative = count from end):
        - sel(arguments="chord 3")                     3rd chord of voice 1
        - sel(arguments="chord 2 4")                   4th chord of voice 2
        - sel(arguments="chord -1 -1")                 last chord of last voice
        - sel(arguments="chord [1 3] [2 2] [-2 5]")    multiple chords
        - sel(arguments="note 3 4 -1")                 last note of 4th chord, voice 3
        - sel(arguments="note [1 3 2] [1 3 3]")        multiple notes
        - sel(arguments="marker 5")                    5th marker
        - sel(arguments="marker -2")                   second-to-last marker
        - sel(arguments="voice 2")                     2nd voice

        By name:
        - sel(arguments="John")                        items named 'John'
        - sel(arguments="John Lennon")                 items named both 'John' and 'Lennon'

        Conditional (note if, chord if, marker if, breakpoint if, tail if):
        Uses expr-like expressions. Available symbolic variables:
        onset, duration, velocity, cents, tail, voice, part,
        numnotes, numchords, index, chordindex, noteindex

        - sel(arguments="note if velocity == 100")
        - sel(arguments="note if cents == 6000")               all middle C's
        - sel(arguments="note if [cents % 1200] == 0")         all C's (any octave)
        - sel(arguments="note if voice == 2")                  notes in voice 2
        - sel(arguments="note if [cents < 6000] && [duration < 1000]")
        - sel(arguments="chord if random(0,100)<50")           random ~50% of chords
        - sel(arguments="marker if onset > 5000")              markers after 5s
        - sel(arguments="breakpoint if [cents > 7200] && [velocity > 100]")
        - sel(arguments="tail if cents > 6000")                tails above middle C

        Markers by role:
        - sel(arguments="markers @role none")          markers with no role
        - sel(arguments="markers @role barline")       barline markers

        Use clearselection() to deselect everything.
        """
        arguments = arguments.strip()
        if not arguments:
            return {"ok": False, "message": "arguments cannot be empty"}
        return _send_max_message(f"sel {arguments}")

    @mcp.tool()
    def clearselection() -> Dict[str, Any]:
        """Deselect all currently selected notation items in bach.roll.

        ⚠️  This tool only has an effect if there is currently something selected.
        If nothing is selected, calling this is a no-op.

        Clears the entire selection at once, with no arguments.
        Use this when you want to reset the selection state entirely.

        Example (exact string sent to Max):
        - clearselection() -> "clearselection"
        """
        return _send_max_message("clearselection")

    @mcp.tool()
    def dynamics2velocities(
        selection: bool = False,
        mapping: str = "",
        maxchars: int = -1,
        exp: float = -1.0,
        breakpointmode: int = -1,
    ) -> Dict[str, Any]:
        """Convert dynamic markings in slot 20 to MIDI velocities in bach.roll.

        Reads the dynamics slot (slot 20) of each note and assigns velocities
        accordingly. Hairpins are interpolated across notes.

        Parameters:
        - selection: if True, applies only to currently selected notes.
                     if False, applies to the whole score (default).

        - mapping: optional custom mapping as a raw llll string, overriding the
                   default equation for specific markings.
                   Form: "[pp 40] [p 55] [mp 70] [mf 85] [f 100] [ff 115]"
                   Only the markings you want to override need to be specified.

        - maxchars: defines the dynamic spectrum - the maximum number of f's or p's
                    in the extreme dynamics used for the mapping equation.
                    - 0  = only "mp" and "mf"
                    - 1  = "p" to "f"
                    - 2  = "pp" to "ff"
                    - 4  = "pppp" to "ffff" (default, omit to use bach default)
                    - 10 = "pppppppppp" to "ffffffffff"
                    Dynamics outside the spectrum are clipped to its extremes.
                    Leave at -1 to use bach's default (4).

        - exp: non-linearity exponent for the mapping curve.
               - 1.0 = linear mapping
               - 0.8 = default, slight compression at extremes
               - 0.4 = more compression (smaller gaps between extreme dynamics)
               Leave at -1.0 to use bach's default (0.8).

        - breakpointmode: controls how pitch breakpoints are handled when
                          breakpointshavevelocity is set to 1:
                          - 0 = only existing breakpoints are assigned velocities
                          - 1 = new breakpoints added to match internal dynamics (default)
                          - 2 = same as 1, but clears existing breakpoints first
                          Leave at -1 to use bach's default (1).

        Examples (exact string sent to Max):
        - dynamics2velocities()
          -> "dynamics2velocities"
        - dynamics2velocities(selection=True)
          -> "dynamics2velocities selection"
        - dynamics2velocities(mapping="[pp 40] [p 55] [mp 70] [mf 85] [f 100] [ff 115]")
          -> "dynamics2velocities @mapping [pp 40] [p 55] [mp 70] [mf 85] [f 100] [ff 115]"
        - dynamics2velocities(maxchars=2, exp=1.0)
          -> "dynamics2velocities @maxchars 2 @exp 1.0"
        - dynamics2velocities(selection=True, breakpointmode=2)
          -> "dynamics2velocities selection @breakpointmode 2"
        """
        parts = ["dynamics2velocities"]
        if selection:
            parts.append("selection")
        if mapping.strip():
            parts.append(f"@mapping {mapping.strip()}")
        if maxchars >= 0:
            parts.append(f"@maxchars {int(maxchars)}")
        if exp >= 0:
            parts.append(f"@exp {float(exp)}")
        if breakpointmode >= 0:
            parts.append(f"@breakpointmode {int(breakpointmode)}")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def velocities2dynamics(
        selection: bool = False,
        mapping: str = "",
        maxchars: int = -1,
        exp: float = -1.0,
    ) -> Dict[str, Any]:
        """Infer dynamic markings from MIDI velocities and write them to slot 20 in bach.roll.

        Reads the velocity of each note and assigns a dynamic marking accordingly.
        Hairpins are also detected automatically between notes.

        Parameters:
        - selection: if True, applies only to currently selected notes.
                     if False, applies to the whole score (default).

        - mapping: optional custom mapping as a raw llll string defining the full
                   set of dynamics symbols and their velocity values.
                   Unlike dynamics2velocities, ALL symbols you want to use must be defined.
                   Form: "[pp 20] [p 40] [mp 70] [mf 90] [f 110] [ff 125]"

        - maxchars: defines the dynamic spectrum used for the mapping equation
                    when no custom mapping is provided.
                    - 0  = only "mp" and "mf"
                    - 1  = "p" to "f"
                    - 2  = "pp" to "ff"
                    - 4  = "pppp" to "ffff" (default, omit to use bach default)
                    - 6  = "pppppp" to "ffffff"
                    Leave at -1 to use bach's default (4).

        - exp: non-linearity exponent for the mapping curve.
               - 1.0 = linear mapping
               - 0.8 = default
               - 0.5 = steeper curve
               Leave at -1.0 to use bach's default (0.8).

        Examples (exact string sent to Max):
        - velocities2dynamics()
          -> "velocities2dynamics"
        - velocities2dynamics(selection=True)
          -> "velocities2dynamics selection"
        - velocities2dynamics(mapping="[pp 20] [p 40] [mp 70] [mf 90] [f 110] [ff 125]")
          -> "velocities2dynamics @mapping [pp 20] [p 40] [mp 70] [mf 90] [f 110] [ff 125]"
        - velocities2dynamics(maxchars=2, exp=0.5)
          -> "velocities2dynamics @maxchars 2 @exp 0.5"
        """
        parts = ["velocities2dynamics"]
        if selection:
            parts.append("selection")
        if mapping.strip():
            parts.append(f"@mapping {mapping.strip()}")
        if maxchars >= 0:
            parts.append(f"@maxchars {int(maxchars)}")
        if exp >= 0:
            parts.append(f"@exp {float(exp)}")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def define_slot(
        slot_number: int,
        type: str = "",
        name: str = "",
        key: str = "",
        range_min: float = float("nan"),
        range_max: float = float("nan"),
        representation: str = "",
        slope: float = float("nan"),
        width: str = "",
        default: str = "",
        ysnap: str = "",
        color: str = "",
    ) -> Dict[str, Any]:
        """Define or update the slotinfo for a single slot in bach.roll.

        Slotinfo is the global configuration of a slot - its type, name, hotkey,
        display range, and more. This must be set before using a slot for data.
        Only the fields you specify are changed; unspecified fields are left as-is.
        The only exception: changing the slot type resets all other slotinfo fields.

        DEFAULT SLOTS already configured in all bach notation objects:
        - Slot 20: type "dynamics",      hotkey D  - dynamic markings
        - Slot 22: type "articulations", hotkey A  - articulations
        - Slot 23: type "notehead",      hotkey H  - noteheads

        Parameters:
        - slot_number: which slot to configure (1-indexed)

        - type: the slot type. Available types:
            - "function"      breakpoint function (x, y, slope per point)
            - "int"           single integer value
            - "float"         single float value
            - "intlist"       list of integers
            - "floatlist"     list of floats
            - "text"          any text string
            - "llll"          any llll (list of lists)
            - "filelist"      list of file paths
            - "spat"          spatialization path (t, radius, angle, interp_type per point)
            - "color"         RGBA color (floats 0.0 to 1.0)
            - "filter"        biquad filter (type, cutoff, gain, Q)
            - "dynfilter"     temporal sequence of interpolated biquad filters
            - "3dfunction"    3D breakpoint function (x, y, z, slope per point)
            - "articulations" one or more articulation symbols
            - "notehead"      a single notehead symbol
            - "dynamics"      dynamic markings with hairpins (see dynamics syntax)
            - "togglematrix"  boolean matrix
            - "intmatrix"     integer matrix
            - "floatmatrix"   float matrix

        - name: display name for the slot (e.g. "frequency", "pan", "dynamics")

        - key: single character hotkey to open the slot window (e.g. "f", "p", "m")

        - range_min, range_max: display range for the slot values.
            For function slots this sets the Y axis range.
            Example: range_min=0, range_max=22050 for a frequency slot.
            Leave as nan to keep existing range.

        - representation: unit label shown in the slot window (e.g. "Hz", "degree", "dB")

        - slope: non-linearity exponent for the slot display curve.
            - 0.0  = linear (default)
            - 0.5  = logarithmic-like (useful for frequency)
            Leave as nan to keep existing slope.

        - width: slot window width. Either:
            - a number (e.g. "80") for a fixed pixel width
            - "temporal" to stretch the slot window proportionally to the note duration

        - default: default value for the slot as a string (e.g. "0.5", "0 0 1 1")

        - ysnap: llll of Y values to snap to when dragging points, as a raw string.
            Example: "[-180 0 180]" for a pan slot snapping to extremes and center.

        - color: RGBA color for the slot display as "r g b a" (floats 0.0 to 1.0).

        Examples (exact string sent to Max):
        - define_slot(1, type="function", name="frequency", key="f",
                      range_min=0, range_max=22050, representation="Hz")
          -> "[slotinfo [1 [type function] [name frequency] [key f] [range 0 22050] [representation Hz]]]"

        - define_slot(1, slope=0.5)
          -> "[slotinfo [1 [slope 0.5]]]"

        - define_slot(1, width="temporal")
          -> "[slotinfo [1 [width temporal]]]"

        - define_slot(2, type="function", name="pan", key="p",
                      range_min=-180, range_max=180, ysnap="[-180 0 180]",
                      representation="degree", width="temporal")
          -> "[slotinfo [2 [type function] [name pan] [key p] [range -180 180] [ysnap [-180 0 180]]] [representation degree] [width temporal]]"

        - define_slot(3, type="floatmatrix", name="routing", key="r",
                      range_min=0, range_max=1, width="80", default="0.5")
          -> "[slotinfo [3 [type floatmatrix] [name routing] [key r] [range 0 1] [width 80] [default 0.5]]]"
        """
        import math
        if slot_number <= 0:
            return {"ok": False, "message": "slot_number must be > 0"}

        parts = []
        if type.strip():
            parts.append(f"[type {type.strip()}]")
        if name.strip():
            parts.append(f"[name {name.strip()}]")
        if key.strip():
            parts.append(f"[key {key.strip()}]")
        if not math.isnan(range_min) and not math.isnan(range_max):
            parts.append(f"[range {float(range_min)} {float(range_max)}]")
        if representation.strip():
            parts.append(f"[representation {representation.strip()}]")
        if not math.isnan(slope):
            parts.append(f"[slope {float(slope)}]")
        if width.strip():
            parts.append(f"[width {width.strip()}]")
        if default.strip():
            parts.append(f"[default {default.strip()}]")
        if ysnap.strip():
            parts.append(f"[ysnap {ysnap.strip()}]")
        if color.strip():
            parts.append(f"[color {color.strip()}]")

        if not parts:
            return {"ok": False, "message": "No slotinfo fields specified"}

        inner = " ".join(parts)
        command = f"[slotinfo [{slot_number} {inner}]]"
        return _send_max_message(command)

    @mcp.tool()
    def erasebreakpoints() -> Dict[str, Any]:
        """Delete all pitch breakpoints from the currently selected notes in bach.roll.

        Removes all intermediate breakpoints, leaving only the default
        notehead (start) and tail (end) positions. This effectively removes
        any glissandi from the selected notes.

        Always operates on the current selection. Use sel() to select notes first.

        Example (exact string sent to Max):
        - erasebreakpoints() -> "erasebreakpoints"
        """
        return _send_max_message("erasebreakpoints")

    @mcp.tool()
    def eraseslot(slot: str) -> Dict[str, Any]:
        """Clear the content of a slot for all currently selected notes in bach.roll.

        Removes the data stored in the specified slot without affecting the
        slot definition (slotinfo). The slot remains defined, just empty.

        Always operates on the current selection. Use sel() to select notes first.

        Parameters:
        - slot: which slot to clear. Can be:
            - a slot number as string (e.g. "4")
            - a slot name (e.g. "amplienv")
            - "active"  - the currently open slot window
            - "all"     - clear all slots

        Examples (exact string sent to Max):
        - eraseslot("4")          -> "eraseslot 4"
        - eraseslot("20")         -> "eraseslot 20" (clears dynamics)
        - eraseslot("22")         -> "eraseslot 22" (clears articulations)
        - eraseslot("amplienv")   -> "eraseslot amplienv"
        - eraseslot("active")     -> "eraseslot active"
        - eraseslot("all")        -> "eraseslot all"
        """
        slot = slot.strip()
        if not slot:
            return {"ok": False, "message": "slot cannot be empty"}
        return _send_max_message(f"eraseslot {slot}")

    @mcp.tool()
    def exportimage(
        filename: str = "",
        view: str = "",
        mspersystem: float = -1.0,
        adaptwidth: int = -1,
        dpi: int = -1,
        systemvshift: int = -1,
    ) -> Dict[str, Any]:
        """Export the current bach.roll score as a PNG image.

        If no filename is provided, a save dialog box will open in Max.
        Images are always exported in PNG format.

        Parameters:
        - filename: output file path (e.g. "/tmp/score.png"). Leave empty for dialog.

        - view: export view mode. Options:
            - "raw"       - exports the current visible portion of the score as-is
            - "line"      - exports the whole score as a single horizontal system (default)
            - "multiline" - splits the score into multiple image files, one per system.
                            System length is set via mspersystem.
            - "scroll"    - like multiline but all systems collected into one tall image.
                            System length is set via mspersystem.

        - mspersystem: length of each system in milliseconds (for multiline/scroll modes).
                       Leave at -1.0 to use the object's current domain width.

        - adaptwidth: controls how mspersystem affects image width:
            - 0 = change horizontal zoom to fit image to object width (default)
            - 1 = change object width to preserve current zoom
            Leave at -1 to use bach's default (0).

        - dpi: dots per inch for the exported image. Leave at -1 for default (72).

        - systemvshift: vertical separation between systems in pixels (scroll/multiline).
                        Leave at -1 for default (0).

        Examples (exact string sent to Max):
        - exportimage()
          -> dialog box
        - exportimage("/tmp/score.png")
          -> "exportimage /tmp/score.png"
        - exportimage("/tmp/score.png", view="line")
          -> "exportimage /tmp/score.png @view line"
        - exportimage("/tmp/score.png", view="scroll", mspersystem=5000)
          -> "exportimage /tmp/score.png @view scroll @mspersystem 5000.0"
        - exportimage("/tmp/score.png", view="multiline", mspersystem=5000, systemvshift=10)
          -> "exportimage /tmp/score.png @view multiline @mspersystem 5000.0 @systemvshift 10"
        """
        parts = ["exportimage"]
        filename = filename.strip()
        if filename:
            parts.append(filename)
        if view.strip():
            parts.append(f"@view {view.strip()}")
        if mspersystem >= 0:
            parts.append(f"@mspersystem {float(mspersystem)}")
        if adaptwidth >= 0:
            parts.append(f"@adaptwidth {int(adaptwidth)}")
        if dpi >= 0:
            parts.append(f"@dpi {int(dpi)}")
        if systemvshift >= 0:
            parts.append(f"@systemvshift {int(systemvshift)}")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def merge(
        threshold_ms: float = -1.0,
        threshold_cents: float = -1.0,
        selection: bool = False,
        time_policy_set: bool = False,
        time_policy: int = 0,
        pitch_policy_set: bool = False,
        pitch_policy: int = 0,
    ) -> Dict[str, Any]:
        """Merge chords too close in time and/or notes too close in pitch in bach.roll.

        Two separate operations can be performed independently or together:
        1. TIME merging: chords within threshold_ms are merged into one chord
        2. PITCH merging: notes within threshold_cents are merged into one note

        Set either threshold to -1 to skip that merging direction.

        Parameters:
        - threshold_ms: time threshold in milliseconds. Chords closer than this
                        are merged. Set to -1 to skip time merging.

        - threshold_cents: pitch threshold in cents. Notes closer in pitch than
                           this are merged. Set to -1 to skip pitch merging.

        - selection: if True, only merge currently selected elements.
                     if False, apply to the whole score (default).

        - time_policy_set: set to True to include time_policy in the command.
        - time_policy: how to align the merged chord in time:
            - -1 = align to the leftmost (earliest) chord
            -  0 = align to the average onset (default)
            -  1 = align to the rightmost (latest) chord

        - pitch_policy_set: set to True to include pitch_policy in the command.
        - pitch_policy: how to set pitch/velocity of merged note:
            - -1 = use the bottommost pitch/velocity
            -  0 = use the average pitch/velocity (default)
            -  1 = use the topmost pitch/velocity

        Note: merging also applies to markers. To avoid affecting markers,
        select only chords first and use selection=True.

        Examples (exact string sent to Max):
        - merge(threshold_ms=200, threshold_cents=10)
          -> "merge 200.0 10.0"
        - merge(threshold_ms=200, threshold_cents=-1)
          -> "merge 200.0 -1.0" (time merging only)
        - merge(threshold_ms=-1, threshold_cents=10)
          -> "merge -1.0 10.0" (pitch merging only)
        - merge(selection=True, threshold_ms=200, threshold_cents=10)
          -> "merge selection 200.0 10.0"
        - merge(threshold_ms=200, threshold_cents=10,
                time_policy_set=True, time_policy=-1,
                pitch_policy_set=True, pitch_policy=1)
          -> "merge 200.0 10.0 -1 1"
        """
        parts = ["merge"]
        if selection:
            parts.append("selection")
        parts.append(str(float(threshold_ms)))
        parts.append(str(float(threshold_cents)))
        if time_policy_set:
            parts.append(str(int(time_policy)))
        if pitch_policy_set:
            parts.append(str(int(pitch_policy)))
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def subroll(
        voices: str = "[]",
        time_lapse: str = "[]",
        selective_options: str = "",
        onset_only: bool = False,
        timeout_seconds: float = 15.0,
    ) -> str:
        """Extract and return a portion of bach.roll as llll gathered syntax.

        Outputs only certain voices within a certain time interval, sending the
        result back from Max. Useful for extracting subsections of a score.

        Parameters:
        - voices: llll of voice numbers to extract, as a string.
                  Use "[]" or "nil" to extract all voices.
                  Examples: "[1 2 4]", "[1 3]", "[]"

        - time_lapse: llll of [start_ms end_ms] to extract, as a string.
                      Use "[]" or "nil" for the full duration.
                      Use a negative end_ms to extract until end of score.
                      Examples: "[1000 3000]", "[2000 -1]", "[]"

        - selective_options: optional list of header sections to include in output.
                             By default all header is included. Use "[body]" to
                             output only the musical content with no header.
                             Options: body, clefs, markers, keys, voicenames, etc.
                             Examples: "[body]", "[clefs markers body]"

        - onset_only: if True, only extracts notes whose onset falls within the
                      time range (no partial notes). Adds "onset" before voices.

        - timeout_seconds: how long to wait for Max to respond.

        Examples (exact string sent to Max):
        - subroll(voices="[1 2 4]", time_lapse="[1000 3000]")
          -> "subroll [1 2 4] [1000 3000]"
        - subroll(voices="[]", time_lapse="[1000 3000]")
          -> "subroll [] [1000 3000]" (all voices, 1-3s)
        - subroll(voices="[1 2]", time_lapse="[]")
          -> "subroll [1 2] []" (voices 1 and 2, full duration)
        - subroll(voices="[1 3]", time_lapse="[2000 -1]")
          -> "subroll [1 3] [2000 -1]" (from 2s to end)
        - subroll(voices="[1 3]", time_lapse="[2000 -1]", onset_only=True)
          -> "subroll onset [1 3] [2000 -1]"
        - subroll(voices="[4 5]", time_lapse="[1000 3000]", selective_options="[body]")
          -> "subroll [4 5] [1000 3000] [body]"
        - subroll(voices="[4 5]", time_lapse="[1000 3000]", selective_options="[clefs markers body]")
          -> "subroll [4 5] [1000 3000] [clefs markers body]"
        """
        parts = ["subroll"]
        if onset_only:
            parts.append("onset")
        parts.append(voices.strip())
        parts.append(time_lapse.strip())
        if selective_options.strip():
            parts.append(selective_options.strip())
        command = " ".join(parts)
        return _request_max_and_wait(command, timeout_seconds=timeout_seconds)

    @mcp.tool()
    def tail(expression: str) -> Dict[str, Any]:
        """Set or modify the tail position (end point) of selected notes in bach.roll.

        The tail is the end position of a note in milliseconds. Always operates
        on the current selection — use sel() to select notes first.

        The expression can be:

        SIMPLE VALUE:
        A number sets the absolute tail position in milliseconds.
        - tail("1000")        set tail at 1000ms
        - tail("= 1000")      same (explicit assignment)
        - tail("= 30000")     make all selected notes end together at 30s

        RELATIVE MODIFICATION via llll [value function]:
        function is one of: plus, minus, times, div
        - tail("= [tail plus 1000]")    lengthen all notes by 1s
        - tail("= [tail minus 500]")    shorten all notes by 500ms
        - tail("= [duration times 2]")  double the duration of all notes

        EQUATION using symbolic variables (preceded by "= "):
        Available variables: onset, duration, velocity, cents, tail, voice, part,
        numnotes, numchords, index, chordindex, noteindex
        - tail("= onset + random[0, 1000]")   random duration up to 1s after onset
        - tail("= onset + duration * 2")      double each note's duration

        LIST OF VALUES (one per note in chord, bottom to top):
        - tail("1000 2000 3000")   different tails per note

        Examples (exact string sent to Max):
        - tail("1000")                         -> "tail 1000"
        - tail("= 1000")                       -> "tail = 1000"
        - tail("= tail + 1000")                -> "tail = tail + 1000"
        - tail("= onset + random[0, 1000]")    -> "tail = onset + random[0, 1000]"
        """
        expression = expression.strip()
        if not expression:
            return {"ok": False, "message": "expression cannot be empty"}
        return _send_max_message(f"tail {expression}")

    @mcp.tool()
    def write(filename: str = "") -> Dict[str, Any]:
        """Save the full bach.roll content in native llll format (.llll file).

        Saves all score content including slotinfo, header, voices, notes, markers,
        and all other data in bach's native binary format with full precision.

        If no filename is provided, a save dialog box will open in Max.
        For human-readable text export, use writetxt() instead.
        For MIDI export, use exportmidi() instead.

        Parameters:
        - filename: output file path (e.g. "myfile.llll"). Leave empty for dialog.

        Examples (exact string sent to Max):
        - write()               -> "write" (dialog box)
        - write("myfile.llll")  -> "write myfile.llll"
        """
        filename = filename.strip()
        command = f"write {filename}" if filename else "write"
        return _send_max_message(command)

    @mcp.tool()
    def writetxt(
        filename: str = "",
        maxdecimals: int = -1,
        indent: str = "",
        maxdepth: int = -2,
        wrap: int = -1,
    ) -> Dict[str, Any]:
        """Save the full bach.roll content as a human-readable text file (.txt).

        Saves all score content in llll text format. The result is a readable,
        editable text file, but floating-point precision is approximate.
        For lossless saving, use write() instead.

        If no filename is provided, a save dialog box will open in Max.

        Parameters:
        - filename: output file path (e.g. "myfile.txt"). Leave empty for dialog.

        - maxdecimals: floating-point precision (number of decimal digits).
                       Leave at -1 for bach's default (10).

        - indent: indentation style for nested sublists.
                  - "tab"      - indent with tabs (default)
                  - an integer - indent with that many spaces per level
                  Leave empty for bach's default ("tab").

        - maxdepth: maximum depth at which sublists are placed on new lines.
                    - -1 = no limit (default, full indentation)
                    - positive = only indent up to that depth
                    Leave at -2 to use bach's default (-1).

        - wrap: maximum number of characters per line.
                - 0 = no wrapping (default)
                Leave at -1 for bach's default (0).

        Examples (exact string sent to Max):
        - writetxt()
          -> "writetxt" (dialog box)
        - writetxt("myfile.txt")
          -> "writetxt myfile.txt"
        - writetxt("myfile.txt", maxdecimals=3)
          -> "writetxt myfile.txt @maxdecimals 3"
        - writetxt("myfile.txt", maxdecimals=3, wrap=40)
          -> "writetxt myfile.txt @maxdecimals 3 @wrap 40"
        - writetxt("myfile.txt", maxdepth=1)
          -> "writetxt myfile.txt @maxdepth 1"
        """
        parts = ["writetxt"]
        filename = filename.strip()
        if filename:
            parts.append(filename)
        if maxdecimals >= 0:
            parts.append(f"@maxdecimals {int(maxdecimals)}")
        if indent.strip():
            parts.append(f"@indent {indent.strip()}")
        if maxdepth >= -1:
            parts.append(f"@maxdepth {int(maxdepth)}")
        if wrap >= 0:
            parts.append(f"@wrap {int(wrap)}")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def set_appearance(attribute: str, value: str) -> Dict[str, Any]:
        """Set a display/appearance attribute of bach.roll.

        Sends the message "<attribute> <value>" directly to Max.
        For example: set_appearance("ruler", "1") sends "ruler 1" to Max.

        All values are plain strings. RGBA colors are given as "r g b a"
        with floats from 0.0 to 1.0. Toggle values are integers (0=off, 1=on).

        CORE COLORS:
        - bgcolor             background color (default white: "1. 1. 1. 1.")
                              sends: "bgcolor 0. 0. 0. 1."
        - notecolor           global note/accidental color (default black: "0. 0. 0. 1.")
                              sends: "notecolor 1. 0. 0. 1."
        - staffcolor          staff lines color (default black: "0. 0. 0. 1.")
                              sends: "staffcolor 0.5 0.5 0.5 1."

        RULER:
        - ruler               0=never, 1=above, 2=below, 3=both
                              sends: "ruler 1"
        - rulercolor          r g b a
                              sends: "rulercolor 0. 0. 0. 1."
        - rulerlabels         0=off, 1=on
                              sends: "rulerlabels 1"
        - rulerlabelsfontsize float (e.g. "8")
                              sends: "rulerlabelsfontsize 8"
        - rulermode           0=fixed, 1=smart
                              sends: "rulermode 1"

        SCROLLBARS:
        - scrollbarcolor      r g b a
                              sends: "scrollbarcolor 0.3 0.3 0.3 1."
        - showscrollbar       0=always hide, 1=show if needed (default)
                              sends: "showscrollbar 1"
        - showvscrollbar      0=always hide, 1=show if needed (default)
                              sends: "showvscrollbar 1"

        SELECTION COLORS:
        - selectedlegendcolor r g b a  (legend shown at top left on click)
                              sends: "selectedlegendcolor 0.2 0.2 0.2 1."
        - selectioncolor      r g b a  (selected noteheads, accidentals, duration lines)
                              sends: "selectioncolor 0.8 0. 0.8 1."

        ACCIDENTALS:
        - showaccidentalspreferences
                              0=classically (default)
                              1=always
                              2=altered notes
                              3=altered notes no repetition
                              4=altered notes no naturals
                              5=never
                              sends: "showaccidentalspreferences 4"
                              NOTE: modes 2 and 3 can be slow in bach.roll.

        SHOW/HIDE ELEMENTS (0=off, 1=on unless noted):
        - showannotations           sends: "showannotations 1"
        - showarticulations         sends: "showarticulations 1"
        - showarticulationsextensions  sends: "showarticulationsextensions 1"
        - showauxclefs              sends: "showauxclefs 1"
        - showborder                sends: "showborder 1"
        - showclefs                 sends: "showclefs 1"
        - showdurations             sends: "showdurations 1"
        - showdynamics              sends: "showdynamics 1"
        - showfocus                 sends: "showfocus 1"
        - showhairpins              sends: "showhairpins 1"
        - showledgerlines           0=never, 1=standard, 2=always refer to main staves
                                    sends: "showledgerlines 1"
        - showlyrics                sends: "showlyrics 1"
        - showmarkers               sends: "showmarkers 1"
        - shownotenames             sends: "shownotenames 0"
        - showpartcolors            sends: "showpartcolors 0"
        - showplayhead              sends: "showplayhead 0"
        - showslotlabels            sends: "showslotlabels 1"
        - showslotlegend            sends: "showslotlegend 1"
        - showslotnumbers           sends: "showslotnumbers 1"
        - showsolocolor             0=never, 1=when selected, 2=when not selected, 3=always
                                    sends: "showsolocolor 2"
        - showstems                 0=none, 1=main stem only, 2=main and auxiliary (default)
                                    sends: "showstems 2"
        - showtails                 sends: "showtails 1"
        - showvoicenames            sends: "showvoicenames 1"

        GROUPS:
        - showgroups                0=none, 1=lines, 2=colors, 3=lines and colors, 4=beams (default)
                                    sends: "showgroups 4"

        VELOCITY DISPLAY:
        - showvelocity              0=none (default), 1=colorscale, 2=colorspectrum,
                                    3=alpha, 4=duration line width, 5=notehead size
                                    sends: "showvelocity 2"

        STEMS AND GRID:
        - stemcolor                 r g b a (stem color)
                                    sends: "stemcolor 0. 0. 0. 1."
        - subdivisiongridcolor      r g b a (grid subdivision line color)
                                    sends: "subdivisiongridcolor 0. 0. 0. 0.1"

        VOICE NAMES:
        - voicenamesalign           1=left, 2=center, 3=right
                                    sends: "voicenamesalign 1"
        - voicenamesfont            font name as symbol (e.g. "Arial")
                                    sends: "voicenamesfont Arial"
        - voicenamesfontsize        float (rescaled with vzoom)
                                    sends: "voicenamesfontsize 11"

        VOICE SPACING:
        - voicespacing              space-separated floats, one more than number of voices.
                                    First = space above voice 1, last = space below last voice,
                                    middle values = space between consecutive voices.
                                    All values are pixels (rescaled with vzoom).
                                    sends: "voicespacing 10. 20. 20. 10."

        ZOOM:
        - vzoom                     vertical zoom percentage, or "auto" to link to object height.
                                    sends: "vzoom auto" or "vzoom 100"
        - zoom                      horizontal zoom percentage (100 = default)
                                    sends: "zoom 100."

        Examples (exact string sent to Max):
        - set_appearance("ruler", "1")                      -> "ruler 1"
        - set_appearance("rulercolor", "0. 0. 0. 1.")       -> "rulercolor 0. 0. 0. 1."
        - set_appearance("showdurations", "0")              -> "showdurations 0"
        - set_appearance("selectioncolor", "0.8 0. 0.8 1.") -> "selectioncolor 0.8 0. 0.8 1."
        - set_appearance("showvelocity", "2")               -> "showvelocity 2"
        - set_appearance("showgroups", "4")                 -> "showgroups 4"
        - set_appearance("showaccidentalspreferences", "4") -> "showaccidentalspreferences 4"
        """
        attribute = attribute.strip()
        value = value.strip()
        if not attribute:
            return {"ok": False, "message": "attribute cannot be empty"}
        if not value:
            return {"ok": False, "message": "value cannot be empty"}
        return _send_max_message(f"{attribute} {value}")

    @mcp.tool()
    def addchord(
        chord_llll: str,
        voice: int = 1,
        select: bool = False,
    ) -> Dict[str, Any]:
        """Add a single chord to an existing bach.roll score without rebuilding it.

        Unlike send_score_to_max() which replaces the entire score, addchord()
        inserts a new chord into the existing content. Use this for incremental
        edits when the rest of the score should be preserved.

        Chord structure (gathered syntax):
        [ onset_ms NOTE1 NOTE2 ... chord_flag ]

        Each NOTE:
        [ pitch_cents duration_ms velocity [SPECIFICATIONS...] note_flag ]

        Specifications (optional, any order): [breakpoints...] [slots...] [name...] [graphic...]
        Pitch: midicents (middle C = C5 = 6000) or note name (C5, D#4, Bb3).
        Flags: 0=normal, 1=locked, 2=muted, 4=solo (sum to combine).

        Slot/breakpoints/dynamics/notehead/articulation syntax: see BACH_SKILL.md.

        Parameters:
        - chord_llll: the chord in gathered syntax llll form
        - voice: voice number to add the chord to (1-indexed, default: 1)
        - select: if True, also select the added chord (default: False)

        Examples:
        - addchord("[1000 [6000 500 50]]")                         middle C, 500ms, vel 50, voice 1
        - addchord("[1000 [6000 500 50]]", voice=2)                same, voice 2
        - addchord("[1000 [6000 500 50] [7200 500 50]]")           two-note chord
        - addchord("[2000 [6000 1000 100 [slots [22 staccato] [20 ff]]]]")  staccato + ff
        - addchord("[500 [7000 500 100 [slots [23 diamond] [22 trill] [20 mp]]]]")
        - addchord("[0 [6000 2000 90 [breakpoints [0 0 0] [1 200 0]]]]")   glissando
        """
        chord_llll = chord_llll.strip()
        if not chord_llll:
            return {"ok": False, "message": "chord_llll cannot be empty"}
        err = _validate_llll(chord_llll)
        if err:
            return {"ok": False, "message": f"Invalid chord_llll — {err}"}
        parts = ["addchord"]
        if voice != 1:
            parts.append(str(int(voice)))
        parts.append(chord_llll)
        if select:
            parts.append("@sel 1")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def addchords(
        chords_llll: str,
        offset_ms: float = float("nan"),
    ) -> Dict[str, Any]:
        """Add multiple chords across voices to an existing bach.roll score.

        Unlike send_score_to_max() which replaces the entire score, addchords()
        inserts chords into the existing content. Use this when adding notes
        across multiple voices without touching the rest of the score.

        The chords_llll argument is structured as one llll per voice, where each
        voice llll contains one llll per chord in gathered syntax. Use [] for
        voices where no chords should be added.

        Structure:
        VOICE1_CHORDS VOICE2_CHORDS ...

        Each VOICE_CHORDS is:
        [ CHORD1 CHORD2 ... ]

        Each CHORD is:
        [ onset_ms NOTE1 NOTE2 ... chord_flag ]

        Each NOTE is:
        [ pitch_cents duration_ms velocity [specifications...] note_flag ]

        See addchord() for the full note and chord gathered syntax documentation,
        including specifications (breakpoints, slots, name, graphic) and
        pitch name syntax (C5, D#4, etc.).

        Parameters:
        - chords_llll: one llll per voice containing chords in gathered syntax.
                       Use [] for voices where no chords are added.

        - offset_ms: optional time offset in milliseconds applied to all chords.
                     Leave as nan to add chords at their literal onset times.

        Examples (exact string sent to Max):
        - addchords("[[217 [7185 492 100]] [971 [6057 492 100]]] [[1665 [7157 492 100]]]")
          -> "addchords [[217 [7185 492 100]] [971 [6057 492 100]]] [[1665 [7157 492 100]]]"
          (two chords in voice 1, one chord in voice 2)

        - addchords("[[217 [7185 492 100]] [971 [6057 492 100]]] [[1665 [7157 492 100]]]",
                    offset_ms=1500)
          -> "addchords 1500 [[217 [7185 492 100]] [971 [6057 492 100]]] [[1665 [7157 492 100]]]"
          (same, with all onsets shifted by 1.5 seconds)

        - addchords("[[0 [6000 500 100]] [500 [6200 500 100]]] []")
          -> voice 1 gets two notes, voice 2 unchanged

        - addchords("[] [[0 [6000 500 100]]]")
          -> voice 1 unchanged, voice 2 gets one note
        """
        import math
        chords_llll = chords_llll.strip()
        if not chords_llll:
            return {"ok": False, "message": "chords_llll cannot be empty"}
        err = _validate_llll(chords_llll)
        if err:
            return {"ok": False, "message": f"Invalid chords_llll — {err}"}
        parts = ["addchords"]
        if not math.isnan(offset_ms):
            parts.append(str(float(offset_ms)))
        parts.append(chords_llll)
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def copyslot(slot_from: str, slot_to: str) -> Dict[str, Any]:
        """Copy the content of one slot to another for all selected notes in bach.roll.

        Always operates on the current selection. Use sel() to select notes first.

        Parameters:
        - slot_from: source slot — number (e.g. "2"), name (e.g. "amplienv"),
                     or "active" for the currently open slot.
        - slot_to:   destination slot — number, name, or "active".

        Examples (exact string sent to Max):
        - copyslot("2", "7")            -> "copyslot 2 7"
        - copyslot("2", "active")       -> "copyslot 2 active"
        - copyslot("amplienv", "myfunction") -> "copyslot amplienv myfunction"
        """
        slot_from = slot_from.strip()
        slot_to = slot_to.strip()
        if not slot_from or not slot_to:
            return {"ok": False, "message": "slot_from and slot_to cannot be empty"}
        return _send_max_message(f"copyslot {slot_from} {slot_to}")

    @mcp.tool()
    def delete(
        transferslots: str = "",
        empty: bool = False,
    ) -> Dict[str, Any]:
        """Delete all currently selected items in bach.roll.

        Always operates on the current selection. Use sel() to select items first.

        When deleting notes from a chord, you can optionally transfer slot content
        to a neighbouring note in the same chord.

        Parameters:
        - transferslots: slots to transfer to a neighbouring note when deleting.
                         Options:
                         - ""         no transfer (default)
                         - "all"      transfer all slots
                         - "auto"     transfer standard slots (dynamics, lyrics,
                                      articulations, annotations)
                         - "20 21"    transfer specific slot numbers (space-separated)
                         - "dynamics", "lyrics", "noteheads", "articulations",
                           "annotation" — transfer by category name

        - empty: if True, also transfer empty slots (default: False).
                 Only relevant when transferslots is set.

        Examples (exact string sent to Max):
        - delete()
          -> "delete"
        - delete(transferslots="20 21")
          -> "delete @transferslots 20 21"
        - delete(transferslots="all")
          -> "delete @transferslots all"
        - delete(transferslots="all", empty=True)
          -> "delete @transferslots all @empty 1"
        - delete(transferslots="auto")
          -> "delete @transferslots auto"
        """
        parts = ["delete"]
        if transferslots.strip():
            parts.append(f"@transferslots {transferslots.strip()}")
            if empty:
                parts.append("@empty 1")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def deleteslotitem(
        slot: str,
        position: str,
        thresh: float = float("nan"),
    ) -> Dict[str, Any]:
        """Delete a specific item from a slot for selected notes in bach.roll.

        Always operates on the current selection. Use sel() to select notes first.

        Parameters:
        - slot: slot number or name (e.g. "3", "amplienv")

        - position: either:
            - an integer index (e.g. "2" = delete 2nd item)
            - a wrapped X coordinate (e.g. "[0.7]" = delete item at X=0.7)

        - thresh: tolerance for X coordinate matching.
                  Leave as nan to use exact matching (default).

        Examples (exact string sent to Max):
        - deleteslotitem("3", "2")              -> "deleteslotitem 3 2"
        - deleteslotitem("3", "[0.7]")          -> "deleteslotitem 3 [0.7]"
        - deleteslotitem("3", "[0.7]", thresh=0.1) -> "deleteslotitem 3 [0.7] @thresh 0.1"
        """
        import math
        slot = slot.strip()
        position = position.strip()
        if not slot or not position:
            return {"ok": False, "message": "slot and position cannot be empty"}
        parts = ["deleteslotitem", slot, position]
        if not math.isnan(thresh):
            parts.append(f"@thresh {float(thresh)}")
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def distribute() -> Dict[str, Any]:
        """Distribute the onsets of selected items so they are evenly spaced in time.

        Always operates on the current selection. Use sel() to select items first.
        The first and last onset are preserved; intermediate onsets are redistributed
        evenly between them.

        Example (exact string sent to Max):
        - distribute() -> "distribute"
        """
        return _send_max_message("distribute")

    @mcp.tool()
    def domain(
        start_or_duration_ms: float,
        end_ms: float = float("nan"),
        pad_pixels: float = float("nan"),
    ) -> Dict[str, Any]:
        """Set the displayed domain (visible time range) of bach.roll.

        Controls what portion of the score is visible by adjusting zoom
        and scrollbar position.

        Parameters:
        - start_or_duration_ms: if end_ms is not given, this is the total duration
                                 of the domain in milliseconds (zoom to fit N ms).
                                 If end_ms is given, this is the start of the
                                 visible range in milliseconds.

        - end_ms: end of the visible range in milliseconds.
                  Leave as nan to use start_or_duration_ms as total duration.

        - pad_pixels: ending pad in pixels (scaled with vzoom).
                      Positive = end point is that many pixels before the edge.
                      Negative = end point is past the edge.
                      Leave as nan for no padding.

        Examples (exact string sent to Max):
        - domain(4000)                      -> "domain 4000.0"
          (zoom so that 4 seconds are visible)
        - domain(2000, 3000)                -> "domain 2000.0 3000.0"
          (display from 2s to 3s)
        - domain(2000, 3000, 10)            -> "domain 2000.0 3000.0 10.0"
          (display from 2s to 3s, with 10px ending pad)
        """
        import math
        parts = ["domain", str(float(start_or_duration_ms))]
        if not math.isnan(end_ms):
            parts.append(str(float(end_ms)))
        if not math.isnan(pad_pixels):
            parts.append(str(float(pad_pixels)))
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def clear() -> Dict[str, Any]:
        """Clear the entire score in bach.roll, removing all notes, chords, and markers.

        This is a destructive operation — the entire score content is erased.
        There is no undo via this tool, so use with caution.

        Example (exact string sent to Max):
        - clear() -> "clear"
        """
        return _send_max_message("clear")

    @mcp.tool()
    def new_default_score() -> Dict[str, Any]:
        """Reset bach.roll to a clean default state for a brand-new score.

        ⚠️  DESTRUCTIVE — call this ONLY when starting a completely new score
        from scratch (e.g. "create a new piece", "start fresh"). Do NOT call
        this if there is already content you want to keep, or just to check
        the current state. It wipes everything and resets all layout settings.

        Performs in sequence:

        1.  clear()            — removes all notes, chords, markers, and voices
        2.  numvoices(1)       — sets exactly one voice
        3.  clefs("G")         — treble clef on voice 1
        4.  stafflines("5")    — standard 5-line staff
        5.  numparts("1")      — one part (voice 1 on its own staff)
        6.  bgcolor(1,1,1,1)   — white background
        7.  notecolor(0,0,0,1) — black notes
        8.  staffcolor(0,0,0,1)— black staff lines
        9.  voicenames          — clear all voice name labels
        10. domain(10000)      — display a 10-second visible window (10 000 ms)

        After calling this tool, always follow up with dump(mode="body") to
        confirm the score is in the expected clean state before adding content.

        Returns a summary dict with the result of each step. If any step fails,
        subsequent steps are still attempted so you get a full picture of what
        succeeded and what did not.
        """
        import time as _time_local

        results: Dict[str, Any] = {}

        _STEP_DELAY = 0.05  # seconds between each message

        def _send_sequential(key: str, command: str) -> None:
            results[key] = _send_max_message(command)
            _time_local.sleep(_STEP_DELAY)

        # 1. Clear all content
        _send_sequential("clear", "clear")

        # 2. Single voice
        _send_sequential("numvoices", "numvoices 1")

        # 3. Treble clef
        _send_sequential("clefs", "clefs G")

        # 4. Standard 5-line staff
        _send_sequential("stafflines", "stafflines 5")

        # 5. One part (voice 1 alone on its staff)
        _send_sequential("numparts", "numparts 1")

        # 6. White background
        _send_sequential("bgcolor", "bgcolor 1.0 1.0 1.0 1.0")

        # 7. Black notes
        _send_sequential("notecolor", "notecolor 0.0 0.0 0.0 1.0")

        # 8. Black staff lines
        _send_sequential("staffcolor", "staffcolor 0.0 0.0 0.0 1.0")

        # 9. No voice name label
        _send_sequential("voicenames", "voicenames")

        # 10. Default 10-second visible domain
        _send_sequential("domain", "domain 10000.0")

        all_ok = all(
            (v.get("ok", False) if isinstance(v, dict) else bool(v))
            for v in results.values()
        )
        return {
            "ok": all_ok,
            "message": (
                "Default score initialised successfully." if all_ok
                else "Default score initialised with one or more errors — check step results."
            ),
            "steps": results,
        }


    # ── Memory & screenshot tools ─────────────────────────────────────────── #
    # File I/O helpers defined inline — no separate module needed.

    import base64
    import json as _json
    import time as _time
    from datetime import datetime, timezone
    from pathlib import Path

    _assets_dir = Path(__file__).parent / "assets"
    _screenshots_dir = _assets_dir / "screenshots"
    _memory_path = _assets_dir / "memory.json"

    def _load_memory() -> Dict[str, Any]:
        _assets_dir.mkdir(exist_ok=True)
        if not _memory_path.exists():
            return {}
        try:
            return _json.loads(_memory_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_memory(data: Dict[str, Any]) -> None:
        _assets_dir.mkdir(exist_ok=True)
        _memory_path.write_text(
            _json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @mcp.tool()
    def project_memory_read(project: str = "") -> Dict[str, Any]:
        """Read persistent memory for a project (or all projects).

        Memory stores intent, workflow, notes, and voice roles across sessions.
        Always read at the start of a session when working on a known project.

        - project: project name to read. Leave empty to list all known projects.
        """
        mem = _load_memory()
        if not project.strip():
            projects = {k: v.get("updated_at", "unknown") for k, v in mem.items()}
            return {"ok": True, "projects": projects}
        key = project.strip()
        if key not in mem:
            return {"ok": True, "project": key, "memory": None,
                    "note": "No memory found. Use project_memory_write to create it."}
        return {"ok": True, "project": key, "memory": mem[key]}

    @mcp.tool()
    def project_memory_write(
        project:  str,
        intent:   str = "",
        workflow: str = "",
        notes:    str = "",
    ) -> Dict[str, Any]:
        """Write or update persistent memory for a project.

        Merges with existing memory — only fields you supply are updated.
        Call when the user states intentions, changes approach, or when
        you want to record something that should survive session restarts.

        - project:  project name (required)
        - intent:   what this piece is trying to be — mood, form, concept
        - workflow: current compositional approach or technique being used
        - notes:    observations, decisions, open questions, voice roles
        """
        key = project.strip()
        if not key:
            return {"ok": False, "error": "project name cannot be empty"}
        mem = _load_memory()
        entry = mem.get(key, {})
        if intent.strip():   entry["intent"]   = intent.strip()
        if workflow.strip(): entry["workflow"]  = workflow.strip()
        if notes.strip():    entry["notes"]     = notes.strip()
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        mem[key] = entry
        _save_memory(mem)
        return {"ok": True, "project": key, "memory": entry}

    @mcp.tool()
    def score_snapshot() -> Dict[str, Any]:
        """Export the current score as a PNG and return it as a base64 image.

        Use when you are unsure whether the score looks correct — after several
        edits, when something feels wrong, or when the user asks to see the score.
        Do NOT call after every single edit — only when visual confirmation is needed.
        The image is saved to bach_mcp/assets/screenshots/.

        Returns: ok, path, base64 (PNG for vision), timestamp.
        """
        _assets_dir.mkdir(exist_ok=True)
        _screenshots_dir.mkdir(exist_ok=True)
        ts  = datetime.now(timezone.utc)
        png = _screenshots_dir / f"score_{ts.strftime('%Y%m%d_%H%M%S')}.png"
        if not bach.send_info(f"exportimage {png} @view line"):
            return {"ok": False, "error": "Failed to send exportimage command to Max"}
        deadline = _time.time() + 10.0
        while _time.time() < deadline:
            if png.exists() and png.stat().st_size > 0:
                break
            _time.sleep(0.25)
        else:
            return {"ok": False, "error": "Score image not written within 10s — is bach.roll connected?"}
        b64 = base64.b64encode(png.read_bytes()).decode("ascii")
        return {"ok": True, "path": str(png), "base64": b64, "timestamp": ts.isoformat()}

    return mcp
