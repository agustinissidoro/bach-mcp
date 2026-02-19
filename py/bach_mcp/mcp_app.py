"""FastMCP app factory and tool/resource registration."""

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

    @mcp.tool()
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
        """Send a single note to bach.roll via llll gathered syntax.

        GATHERED SYNTAX OVERVIEW:
        In bach.roll, the full note definition is:
        [ pitch_cents duration_ms velocity [SPECIFICATIONS...] note_flag ]

        Specifications are optional llll blocks inserted between velocity and note_flag,
        in any order. Each has the form [ specification_name CONTENT ].

        This tool builds that syntax from its arguments. For multi-note chords or
        complex multi-voice scores, use send_score_to_max() with a raw llll string.

        ─────────────────────────────────────────────────────────────
        SLOTS
        ─────────────────────────────────────────────────────────────
        Slots are per-note containers for additional data: automation curves,
        articulations, noteheads, dynamics, text, colors, and more.
        Each note can have multiple slots, each identified by a slot number.

        Pass slots as a raw llll string in the form:
        [slots [slot_number CONTENT] [slot_number CONTENT] ...]

        Slot content syntax by type:
        - function:     [x y slope] [x y slope] ...
                        x and y are coordinates, slope is -1 to 1 (0 = linear)
        - int/float:    a single number
        - intlist/floatlist: number1 number2 ...
        - text:         a single symbol (no spaces unless quoted)
        - llll:         [ WRAPPED_LLLL ]
        - articulations: symbols from the standard list, e.g. "staccato accent trill"
                        shortcuts: stacc, acc, ferm, port, mart, tr, ubow, dbow,
                        trem1, trem2, trem3, grupp, umord, dmord, mmord, lhpiz
        - notehead:     a single symbol, e.g. "default", "diamond", "cross", "white",
                        "black", "whole", "doublewhole", "none", "plus", "blacksquare",
                        "whitesquare", "blacktriangle", "whitetriangle", "blackrhombus",
                        "whiterhombus"
        - color:        red green blue alpha (floats 0.0 to 1.0)
        - spat:         [t radius angle interp_type] [t radius angle interp_type] ...
        - filter:       filtertype cutoff_Hz gain_dB Q  (e.g. "lowpass 440 0 1")
                        or biquad coefficients: a0 a1 a2 b1 b2

        Example slots strings:
        - "[slots [1 [0. 0. 0.] [0.5 200. 0.] [1. 0. 0.]]]"  (function in slot 1)
        - "[slots [2 staccato accent]]"                        (articulations in slot 2)
        - "[slots [3 diamond]]"                                (notehead in slot 3)
        - "[slots [1 [0. 0. 0.] [1. 100. 0.]] [2 staccato]]"  (two slots)

        ─────────────────────────────────────────────────────────────
        SLOTS — ARTICULATIONS (slot 22 by default)
        ─────────────────────────────────────────────────────────────
        Articulations are stored in slot 22 by default in all bach notation objects.
        The slot type is "articulations". Unlike noteheads, multiple articulations
        can be assigned to a single note simultaneously.

        STANDARD ARTICULATION SYMBOLS (full name / short name):
        - "staccato"           / "stacc"      staccato
        - "staccatissimo"      / "staccmo"    staccatissimo
        - "fermata"            / "ferm"       fermata
        - "portato"            / "port"       portato
        - "accent"             / "acc"        accent
        - "accentstaccato"     / "accstacc"   accent + staccato
        - "accentportato"      / "accport"    accent + portato
        - "portatostaccato"    / "portstacc"  portato + staccato
        - "martellato"         / "mart"       martellato
        - "martellatostaccato" / "martstacc"  martellato + staccato
        - "lefthandpizzicato"  / "lhpizz"     left hand pizzicato
        - "trill"              / "tr"         trill
        - "trill#"             / "tr#"        trill sharp
        - "trillb"             / "trb"        trill flat
        - "trillx"             / "trx"        trill double sharp
        - "trillbb"            / "trbb"       trill double flat
        - "gruppetto"          / "grupp"      gruppetto
        - "upmordent"          / "umord"      upward mordent
        - "downmordent"        / "dmord"      downward mordent
        - "doublemordent"      / "mmord"      double mordent
        - "upbowing"           / "ubow"       upward bowing
        - "downbowing"         / "dbow"       downward bowing
        - "tremolo3"           / "trem3"      3-slash tremolo
        - "tremolo2"           / "trem2"      2-slash tremolo
        - "tremolo1"           / "trem1"      1-slash tremolo

        Multiple articulations can be combined in a single slot by listing them
        space-separated. Order does not matter.

        Examples:
        - slots="[slots [22 staccato]]"              single staccato
        - slots="[slots [22 accent staccato]]"       accent + staccato
        - slots="[slots [22 fermata]]"               fermata
        - slots="[slots [22 trill]]"                 trill
        - slots="[slots [22 trem3]]"                 3-slash tremolo
        - slots="[slots [22 ubow trem2]]"            upbowing + 2-slash tremolo
        - slots="[slots [22 port ferm]]"             portato + fermata

        Combining articulations and dynamics in one slots string:
        - slots="[slots [22 staccato] [20 p<]]"      staccato with crescendo from p
        - slots="[slots [22 accent] [20 ff]]"        accent with ff dynamic

        ─────────────────────────────────────────────────────────────
        SLOTS — NOTEHEADS (slot 23 by default)
        ─────────────────────────────────────────────────────────────
        Noteheads are stored in slot 23 by default in all bach notation objects.
        The slot type is "notehead". Only one notehead can be assigned per note.

        STANDARD NOTEHEAD SYMBOLS:
        - "default"       standard notehead (quarter note)
        - "doublewhole"   double whole note (breve)
        - "whole"         whole note
        - "white"         half note (open)
        - "black"         filled/quarter notehead
        - "diamond"       harmonics notehead
        - "cross"         x-shaped notehead
        - "plus"          plus-shaped notehead
        - "none"          invisible notehead
        - "accent"        slap or pizzicato notehead
        - "blacksquare"   filled square
        - "whitesquare"   open square
        - "square"        black or white depending on note duration (bach.score only)
        - "blacktriangle" filled triangle
        - "whitetriangle" open triangle
        - "triangle"      black or white depending on note duration (bach.score only)
        - "blackrhombus"  filled rhombus
        - "whiterhombus"  open rhombus
        - "rhombus"       black or white depending on note duration (bach.score only)

        Note: in bach.roll, "square", "triangle" and "rhombus" always use
        their black (filled) flavour regardless of duration.

        Examples:
        - slots="[slots [23 diamond]]"       harmonics notehead
        - slots="[slots [23 cross]]"         x notehead (col legno, etc.)
        - slots="[slots [23 none]]"          invisible notehead
        - slots="[slots [23 blacksquare]]"   square notehead

        Combining notehead, articulations and dynamics in one slots string:
        - slots="[slots [23 diamond] [22 trill] [20 mp]]"
          harmonics notehead, trill articulation, mp dynamic

        ─────────────────────────────────────────────────────────────
        SLOTS — DYNAMICS (slot 20 by default)
        ─────────────────────────────────────────────────────────────
        Dynamics are stored in slot 20 by default in all bach.roll objects.
        The slot type is "text" and the content is a dynamics marking string.

        DYNAMIC SYMBOLS:
        pppp, ppp, pp, p, mp, mf, f, ff, fff, ffff  (and more p's/f's)
        sfz, sf, sffz
        sfp, sfmp, sfmf  (and variants: sfppp, sfpp, sfppppp, etc.)
        sfzp, sfzmp, sfzmf (and variants: sfzppp, sfzpp, sfzppppp, etc.)
        o  — zero dynamic (dal niente / al niente)
        Any unrecognized text is displayed as a textual expression in roman italics:
        e.g. "subito", "cresc", "sempre p" — useful for performance instructions.

        HAIRPIN SYMBOLS:
        =    no hairpin (steady, explicit)
        <    crescendo
        >    diminuendo
        v    crescendo (alternative symbol)
        ^    diminuendo (alternative symbol)
        <<   exponential crescendo
        >>   exponential diminuendo
        _    dashed line (instead of hairpin)
        --   dashed line (alternative)

        PLAIN SYNTAX:
        A space-separated sequence of markings and hairpins.
        A number (0.0-1.0) before a marking sets its relative position.
        Elements can also be given as llll with spaces between them.
        Dynamics are evenly spaced inside the chord duration by default.

        Basic examples:
        - "mp"                  single marking
        - "f< ff> mp"           crescendo to ff then diminuendo to mp
        - "pp subito"           pp with textual expression "subito" in italics
        - "p cresc"             p with textual "cresc" in italics
        - "pp<"                 crescendo from pp continuing to next note's marking
        - "pp<|"                crescendo ending at note tail (| = empty terminal mark)
        - "pp<<"                exponential crescendo
        - "o<<f>>o"             dal niente, exp. crescendo to f, exp. diminuendo al niente
        - "p<ff=ff>p"           crescendo to ff, steady ff, diminuendo to p
        - "p<ff>>mp<"           combine all: crescendo, exp. diminuendo, crescendo

        UNDERSCORE FOR DASHED LINES:
        Use "_" after a marking to connect to the next with a dashed line instead
        of a hairpin. Useful for "al niente", "sempre", etc.:
        - "f_ al_ niente"       f, dashed to "al", dashed to "niente"

        HAIRPIN ENDING RULES:
        - A trailing hairpin (e.g. "p<") continues to the next note with a marking
        - Use "|" to end the hairpin at the note tail:
          "p<|" — crescendo ends at this note's tail, does not continue
        - Use "=" to concatenate dynamics without any hairpin:
          "p<ff=ff>p" — crescendo to ff, then ff again without hairpin, then diminuendo

        ATTACHING DYNAMICS TO BREAKPOINTS (plain syntax):
        Use @N instead of a relative position to attach a marking to the Nth
        breakpoint after the notehead. Negative numbers count backwards.
        Example: "f> @1 p< @2 ff_ @3 al_ niente"
        - f>          at auto position, with diminuendo
        - @1 p<       attached to breakpoint 1, with crescendo
        - @2 ff_      attached to breakpoint 2, with dashed line
        - @3 al_      attached to breakpoint 3, with dashed line
        - niente      final marking at auto position

        STRUCTURED LLLL SYNTAX:
        [ relpos marking(s) hairpin ] [ relpos marking(s) hairpin ] ...
        - relpos:     0.0 to 1.0, or "auto" for equal spacing,
                      or [breakpoint N] to attach to the Nth breakpoint
        - marking(s): single symbol or llll of symbols e.g. [fff tenuto]
        - hairpin:    any hairpin symbol from the list above

        Examples:
        "[auto p <] [auto [fff tenuto] =] [0.8 [] >] [auto mp =]"
        — p crescendo, fff tenuto steady, empty mark starting diminuendo at 0.8, mp

        "[auto f >] [[breakpoint 1] p <] [[breakpoint 2] ff _] [[breakpoint 3] al _] [auto niente =]"
        — dynamics attached to breakpoints

        Note: [] is an empty marking — useful to start a hairpin at a precise
        position without placing a dynamic symbol there.

        FULL SYNTAX (output form from bach):
        When bach outputs dynamics it uses the full structured form including
        both the breakpoint index and its current relative position:
        [breakpoint N relativeposition]
        Example: "[[auto 0 0.] f >] [[breakpoint 1 0.306] p <] [[breakpoint 2 0.631] ff _]"
        You can use this form for input; relativeposition is ignored at input
        and substituted with the actual breakpoint position.

        MULTI-NOTE DYNAMICS PATTERNS:
        Simple crescendo p to f across two notes:
        - Note 1: slots="[slots [20 p<]]"
        - Note 2: slots="[slots [20 f]]"

        Diminuendo f to p:
        - Note 1: slots="[slots [20 f>]]"
        - Note 2: slots="[slots [20 p]]"

        Crescendo then diminuendo (p < fff > mp) across three notes:
        - Note 1: slots="[slots [20 p<]]"
        - Note 2: slots="[slots [20 fff>]]"
        - Note 3: slots="[slots [20 mp]]"

        Dal niente to f and back al niente:
        - Note 1: slots="[slots [20 o<<]]"
        - Note 2: slots="[slots [20 f>>]]"
        - Note 3: slots="[slots [20 o]]"

        Crescendo ending at note tail (not continuing to next note):
        - Note 1: slots="[slots [20 p<|]]"

        ─────────────────────────────────────────────────────────────
        BREAKPOINTS
        ─────────────────────────────────────────────────────────────
        Breakpoints define pitch glissandi along the note duration line.
        Two breakpoints are always implicit: (0 0 0) at the notehead and
        [1 delta_midicents slope] at the tail. You only need to provide them
        explicitly if the note has a glissando.

        Pass breakpoints as a raw llll string in the form:
        [breakpoints [0 0 0] [rel_x delta_cents slope] ... [1 delta_cents slope]]

        - rel_x: position along the note, 0.0 = notehead, 1.0 = tail
        - delta_cents: pitch difference in midicents from the base note pitch
        - slope: curvature of the preceding segment, -1 to 1 (0 = linear)

        The first breakpoint must always be [0 0 0].
        The last breakpoint must always start with 1.

        Example breakpoint strings:
        - "[breakpoints [0 0 0] [1 200 0]]"             glissando up 200 cents, linear
        - "[breakpoints [0 0 0] [1 -100 0]]"            glissando down 100 cents
        - "[breakpoints [0 0 0] [0.5 200 0] [1 0 0.5]]" up then back down, curved descent

        ─────────────────────────────────────────────────────────────
        NAME
        ─────────────────────────────────────────────────────────────
        Assign one or more names to the note as an llll:
        - Single name:    "pippo"              -> [name pippo]
        - Multiple names: "[high 1] [low 2]"   -> [name [high 1] [low 2]]

        ─────────────────────────────────────────────────────────────
        NOTE FLAG
        ─────────────────────────────────────────────────────────────
        Optional bitfield:
        - 0 = normal (default)
        - 1 = locked
        - 2 = muted
        - 4 = solo
        Combine by summing: 3 = locked + muted, 6 = muted + solo, etc.

        ─────────────────────────────────────────────────────────────
        PITCH
        ─────────────────────────────────────────────────────────────
        Pitch in midicents: middle C = 6000, one semitone = 100 cents.
        Microtones are expressed as fractions: 6050 = C + 50 cents (quarter tone up).

        ─────────────────────────────────────────────────────────────
        EXAMPLES
        ─────────────────────────────────────────────────────────────
        Simple note, middle C:
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100)

        Note with glissando up 200 cents:
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100,
                        breakpoints="[breakpoints [0 0 0] [1 200 0]]")

        Note with articulation in slot 2:
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100,
                        slots="[slots [2 staccato]]")

        Note with function in slot 1 and a name:
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100,
                        slots="[slots [1 [0. 0. 0.] [1. 100. 0.]]]",
                        name="pippo")

        Note in voice 2, muted:
        add_single_note(onset_ms=0, pitch_cents=6000, duration_ms=1000, velocity=100,
                        voice=2, note_flag=2)
        """
        if duration_ms <= 0:
            return {"ok": False, "message": "duration_ms must be > 0"}
        if velocity < 0 or velocity > 127:
            return {"ok": False, "message": "velocity must be between 0 and 127"}
        if voice <= 0:
            return {"ok": False, "message": "voice must be > 0"}

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
        """Send a raw llll score string directly to bach.roll to set its notation content.

        IMPORTANT: This is the PRIMARY and PREFERRED way to write any score to bach.roll.
        Always use this tool when writing notes, chords, or multi-voice content.
        Do NOT use add_single_note() for score writing — use this tool instead.
        add_single_note() exists only as a convenience for quick single-note testing.

        SCORE FORMAT:
        Bach.roll scores use the llll (lisp-like linked list) format. The full score
        is prefixed with "roll" followed by one llll per voice. Each voice contains
        chords, and each chord contains notes.

        Hierarchy:
        roll [ VOICE1 ] [ VOICE2 ] [ VOICE3 ] ...

        Each VOICE is:
        [ CHORD1 CHORD2 ... 0 ]

        Each CHORD is:
        [ onset_ms [ pitch_cents duration_ms velocity note_flag ] 0 ]

        For chords with multiple notes:
        [ onset_ms [ pitch1 dur1 vel1 flag1 ] [ pitch2 dur2 vel2 flag2 ] ... 0 ]

        Pitch in midicents: middle C = 6000, one semitone = 100 cents.
        Duration in milliseconds.
        Velocity: 1 to 127.
        note_flag: 0 = normal, 1 = locked, 2 = muted, 4 = solo (sum to combine).
        The trailing 0 after the last chord in a voice is required.

        EXAMPLES:

        Single note, middle C, one voice:
        "roll [ [ 0. [ 6000. 673. 100 0 ] 0 ] 0 ]"

        Many notes, one voice:
        "roll [ [ 214.775391 [ 6100. 673. 100 0 ] 0 ] [ 244.775391 [ 5400. 673. 100 0 ] 0 ] [ 1124.775391 [ 6100. 673. 100 0 ] 0 ] [ 2584.775391 [ 7100. 673. 100 0 ] 0 ] [ 3204.775391 [ 6200. 673. 100 0 ] 0 ] [ 4234.775391 [ 6000. 673. 100 0 ] 0 ] [ 5054.775391 [ 5000. 673. 100 0 ] 0 ] [ 5714.775391 [ 6000. 673. 100 0 ] 0 ] 0 ]"

        Three voices:
        "roll [ [ 0. [ 6000. 673. 100 0 ] 0 ] [ 5574.775391 [ 5900. 654. 100 0 ] 0 ] 0 ] [ [ 2724.775391 [ 6000. 654. 100 0 ] 0 ] [ 4424.775391 [ 6000. 654. 100 0 ] 0 ] 0 ] [ [ 544.775391 [ 5700. 654. 100 0 ] 0 ] [ 1214.775391 [ 9600. 654. 100 0 ] 0 ] [ 1214.775391 [ 7300. 654. 100 0 ] 0 ] [ 2524.775391 [ 6500. 654. 100 0 ] 0 ] [ 3554.775391 [ 6300. 654. 100 0 ] 0 ] [ 5394.775391 [ 5900. 654. 100 0 ] 0 ] 0 ]"

        NOTE: The score string must start with "roll" followed by the voice lllls.
        This is what bach.roll expects — it is NOT the same as the raw llll body
        returned by dump(mode="body"), which omits the "roll" prefix and the header.

        A full dump() includes slotinfo, clefs, voicenames, markers, and other header
        data in addition to the score body. send_score_to_max() only sets the notation
        content (notes, chords, voices) — it does not affect slotinfo or other header fields.

        Use dump(mode="body") to retrieve the current score body from bach.roll.
        Use send_process_message_to_max() for commands like play, dump, clefs, etc.
        """
        score_llll = score_llll.strip()
        if not score_llll:
            return "Rejected empty llll score"
        success = bach.send_score(score_llll)
        return "Sent llll score to Max" if success else "Failed to send llll score"

    @mcp.tool()
    def send_process_message_to_max(message: str) -> str:
        """Send a plain command or instruction to bach.roll in Max/MSP (non-score text).

        Use this for any message that is not notation data — i.e., anything that is
        not an llll score. This includes commands like play, stop, clefs, bgcolor,
        numvoices, and so on.

        Unlike send_score_to_max() (which sets notation content via llll) and dump()
        (which requests data back from Max), this tool is fire-and-forget:
        it sends the command but does not wait for or return any response.

        Examples:
        - "play"
        - "stop"
        - "clefs G F"

        Prefer the dedicated tools (play, clefs, bgcolor, etc.) when available,
        and fall back to this tool for commands that don't have a dedicated wrapper.
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
    def bgcolor(r: float = 1.0, g: float = 1.0, b: float = 1.0, a: float = 1.0) -> Dict[str, Any]:
        """Set bach.roll background color in RGBA format.

        All values are floats in the range 0.0 to 1.0 (not 0-255).
        Default is white (1.0, 1.0, 1.0, 1.0). Alpha 0.0 is fully transparent.

        Example: bgcolor(r=0.0, g=0.0, b=0.0, a=1.0) -> solid black background.
        """
        return _send_max_message(f"bgcolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def clefs(clefs_list: str = "G") -> Dict[str, Any]:
        """Set the clef for each voice in bach.roll.

        Clefs are provided as a space-separated list of symbols, one per voice.
        If fewer clefs than voices are provided, the last clef is repeated.

        Available clef symbols:
        - "G"     — treble clef
        - "G8va"  — treble clef 8va alta (one octave up)
        - "G8"    — treble clef 8va bassa (one octave down)
        - "F"     — bass clef
        - "F8va"  — bass clef 8va alta (one octave up)
        - "F8"    — bass clef 8va bassa (one octave down)
        - "alto"  — alto C clef
        - "perc"  — percussion clef
        - "auto"  — bach chooses automatically based on pitch content
        - "none"  — no clef displayed

        For grand staff (piano-style), wrap multiple clefs for a single voice in brackets:
        "[G F]" means treble + bass for one voice.

        Examples (exact string sent to Max):
        - clefs("G")          -> all voices use treble clef
        - clefs("G F")        -> voice 1 treble, voice 2 bass
        - clefs("auto G F")   -> voice 1 auto, voice 2 treble, voice 3 bass
        - clefs("[G F]")      -> voice 1 is a grand staff (treble + bass)
        """
        clefs_list = clefs_list.strip()
        if not clefs_list:
            return {"ok": False, "message": "clefs_list cannot be empty"}
        return _send_max_message(f"clefs {clefs_list}")

    @mcp.tool()
    def notecolor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> Dict[str, Any]:
        """Set the default color for all notes drawn in bach.roll.

        All values are floats in the range 0.0 to 1.0 (not 0-255).
        Default is black (0.0, 0.0, 0.0, 1.0). Alpha 0.0 is fully transparent.

        This sets the global note color. Individual notes may override this
        if they have a color slot assigned.

        Example: notecolor(r=1.0, g=0.0, b=0.0, a=1.0) -> all notes drawn in red.
        """
        return _send_max_message(f"notecolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def numparts(parts: str = "1") -> Dict[str, Any]:
        """Set the part grouping for voices in bach.roll.

        Defines how voices are grouped into shared staves (called "staff ensembles").
        Each integer in the list specifies how many consecutive voices are displayed
        on the same staff. The integers must sum to the total number of voices.

        For instance, with 4 voices:
        - "1 1 1 1" — each voice on its own staff (4 separate staves)
        - "2 2"     — voices 1+2 share a staff, voices 3+4 share a staff
        - "1 3"     — voice 1 alone, voices 2+3+4 share a staff
        - "4"       — all four voices on a single shared staff

        Examples (exact string sent to Max):
        - numparts("1 1 1 1")  -> four separate staves
        - numparts("2 2")      -> two staff ensembles of two voices each
        - numparts("1 3")      -> one solo staff, one ensemble of three
        - numparts("4")        -> all voices on one staff
        """
        parts = parts.strip()
        if not parts:
            return {"ok": False, "message": "parts cannot be empty"}
        return _send_max_message(f"numparts {parts}")

    @mcp.tool()
    def numvoices(count: int) -> Dict[str, Any]:
        """Set the number of voices (staves) in bach.roll.

        Each voice corresponds to one staff line in the score. Adding voices
        adds empty staves; removing voices will delete the content of the
        removed staves, so use with caution.

        count must be greater than 0.

        Examples (exact string sent to Max):
        - numvoices(1) -> single staff (monophonic or chordal)
        - numvoices(4) -> four staves (e.g. SATB voices)
        """
        if count <= 0:
            return {"ok": False, "message": "count must be > 0"}
        return _send_max_message(f"numvoices {int(count)}")

    @mcp.tool()
    def staffcolor(r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> Dict[str, Any]:
        """Set the color of the staff lines in bach.roll.

        All values are floats in the range 0.0 to 1.0 (not 0-255).
        Default is black (0.0, 0.0, 0.0, 1.0). Alpha 0.0 is fully transparent.

        This affects the color of the staff lines themselves, not the notes.
        Use notecolor() to change note color, bgcolor() to change the background.

        Example: staffcolor(r=0.5, g=0.5, b=0.5, a=1.0) -> grey staff lines.
        """
        return _send_max_message(f"staffcolor {float(r)} {float(g)} {float(b)} {float(a)}")

    @mcp.tool()
    def stafflines(value: str) -> Dict[str, Any]:
        """Set the staff lines for each voice in bach.roll.

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
        """Delete the first marker in bach.roll that matches the given name.

        Only the first matching marker is deleted. If multiple markers share
        the same name, call this repeatedly to delete them one by one.

        marker_names: the name of the marker to delete, as a symbol or llll.

        Examples (exact string sent to Max):
        - deletemarker("intro")   -> deletes first marker named "intro"
        - deletemarker("A")       -> deletes first marker named "A"
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
        """Return the current number of voices (staves) in bach.roll.

        Sends "getnumvoices" to Max and waits for a response.
        Returns a single integer value.

        Useful for querying the score structure before performing operations
        that depend on voice count, such as setting clefs or voicenames.

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

        Use select() for involutive (toggle) selection with the same syntax.
        Use unselect() to deselect a time range.
        Use clearselection() to deselect everything.
        """
        arguments = arguments.strip()
        if not arguments:
            return {"ok": False, "message": "arguments cannot be empty"}
        return _send_max_message(f"sel {arguments}")

    @mcp.tool()
    def select(arguments: str) -> Dict[str, Any]:
        """Involutive selection in bach.roll — same syntax as sel() but toggles selection state.

        Items that are already selected become deselected, and unselected items become
        selected. This mirrors shift-clicking a selection rectangle in the UI.

        The syntax is identical to sel() in every way, with one exception:
        "select all" always selects everything (non-involutive).

        Refer to sel() for the full syntax documentation and examples.

        Examples (exact string sent to Max):
        - select(arguments="all")                   -> "select all" (always selects all)
        - select(arguments="note if voice == 2")    -> toggle notes in voice 2
        - select(arguments="1000 3000 [] []")       -> toggle notes between 1-3s
        - select(arguments="chord 3")               -> toggle 3rd chord of voice 1
        """
        arguments = arguments.strip()
        if not arguments:
            return {"ok": False, "message": "arguments cannot be empty"}
        return _send_max_message(f"select {arguments}")

    @mcp.tool()
    def unselect(start_ms: float, end_ms: float) -> Dict[str, Any]:
        """Deselect all notation items within a time range in bach.roll.

        Always deselects items in the given range, regardless of their current
        selection state. Items outside the range are unaffected.

        Use sel() to select a range, select() to toggle selection in a range,
        and clearselection() to deselect everything at once.

        Examples (exact string sent to Max):
        - unselect(0, 1000)    -> "unsel 0.0 1000.0"
        - unselect(500, 2000)  -> "unsel 500.0 2000.0"
        """
        return _send_max_message(f"unsel {float(start_ms)} {float(end_ms)}")

    @mcp.tool()
    def clearselection() -> Dict[str, Any]:
        """Deselect all currently selected notation items in bach.roll.

        Clears the entire selection at once, with no arguments.
        Use this when you want to reset the selection state entirely.

        Use unselect() to deselect items in a specific time range instead.

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
        composition when the rest of the score should be preserved.

        The chord is given in gathered syntax llll form:
        [ onset_ms NOTE1 NOTE2 ... chord_flag ]

        Each NOTE is:
        [ pitch_cents duration_ms velocity [specifications...] note_flag ]

        Specifications (optional, between velocity and note_flag, any order):
        - [breakpoints [0 0 0] [rel_x delta_cents slope] ... [1 delta_cents slope]]
        - [slots [slot_number CONTENT] ...]
        - [name NAME_OR_NAMES]
        - [graphic displayed_midicents displayed_accidental]

        Pitch can be given as midicents (e.g. 6000) or note name (e.g. C5, D#4, Bb3).
        Middle C = C5 = 6000 midicents.
        Accidentals: # sharp, b flat, x double sharp, q quartertone sharp,
                     d quartertone flat, ^ eighth-tone sharp, v eighth-tone flat.

        chord_flag (optional bitfield): 0=normal, 1=locked, 2=muted, 4=solo

        Parameters:
        - chord_llll: the chord in gathered syntax llll form (see above)
        - voice: voice number to add the chord to (1-indexed, default: 1)
        - select: if True, also select the added chord (default: False)

        Examples (exact string sent to Max):
        - addchord("[1000 [6000 500 50]]")
          -> "addchord [1000 [6000 500 50]]"
          (middle C at 1s, 500ms, velocity 50, voice 1)

        - addchord("[1000 [6000 500 50]]", voice=2)
          -> "addchord 2 [1000 [6000 500 50]]"

        - addchord("[1000 [6000 500 50]]", voice=2, select=True)
          -> "addchord 2 [1000 [6000 500 50]] @sel 1"

        - addchord("[1000 [6000 500 50] [7200 500 50]]")
          -> "addchord [1000 [6000 500 50] [7200 500 50]]"
          (chord with two notes: middle C and G above)

        - addchord("[2000 [6000 1000 100 [slots [22 staccato] [20 ff]]]]")
          -> chord with staccato articulation and ff dynamic

        - addchord("[500 [7000 500 127] [7200 1200 100] [name paul] 0]")
          -> named chord with two notes
        """
        chord_llll = chord_llll.strip()
        if not chord_llll:
            return {"ok": False, "message": "chord_llll cannot be empty"}
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
        parts = ["addchords"]
        if not math.isnan(offset_ms):
            parts.append(str(float(offset_ms)))
        parts.append(chords_llll)
        return _send_max_message(" ".join(parts))

    @mcp.tool()
    def copy(mode: str = "") -> Dict[str, Any]:
        """Copy selected content or slot data to the global clipboard in bach.roll.

        If no mode is given, copies the current selection.

        Parameters:
        - mode: what to copy. Options:
            - ""                  copy current selection (default)
            - "durationline"      copy the duration line
            - "slot active"       copy content of the currently open slot window
            - "slot N"            copy content of slot N (e.g. "slot 1")
            - "slot all"          copy content of all slots
            - "slotinfo N"        copy the slotinfo (structure) of slot N
            - "slotinfo active"   copy the slotinfo of the active slot

        Examples (exact string sent to Max):
        - copy()                    -> "copy"
        - copy("durationline")      -> "copy durationline"
        - copy("slot 1")            -> "copy slot 1"
        - copy("slot active")       -> "copy slot active"
        - copy("slot all")          -> "copy slot all"
        - copy("slotinfo 3")        -> "copy slotinfo 3"
        """
        mode = mode.strip()
        command = f"copy {mode}" if mode else "copy"
        return _send_max_message(command)

    @mcp.tool()
    def cut(mode: str = "") -> Dict[str, Any]:
        """Cut selected content or slot data to the global clipboard in bach.roll.

        Identical to copy() but also deletes the copied content afterwards.
        If no mode is given, cuts the current selection.

        Parameters:
        - mode: what to cut. Options:
            - ""                  cut current selection (default)
            - "durationline"      cut the duration line
            - "slot active"       cut content of the currently open slot window
            - "slot N"            cut content of slot N (e.g. "slot 1")
            - "slot all"          cut content of all slots

        Examples (exact string sent to Max):
        - cut()                 -> "cut"
        - cut("durationline")   -> "cut durationline"
        - cut("slot 1")         -> "cut slot 1"
        - cut("slot active")    -> "cut slot active"
        - cut("slot all")       -> "cut slot all"
        """
        mode = mode.strip()
        command = f"cut {mode}" if mode else "cut"
        return _send_max_message(command)

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
    def deletemarker(names: str) -> Dict[str, Any]:
        """Delete the first marker matching the given name(s) in bach.roll.

        If multiple markers match, only the first one (in temporal order) is deleted.
        To delete by multiple names, provide them space-separated — only markers
        having ALL the given names will match.

        Parameters:
        - names: one or more marker names, space-separated.

        Examples (exact string sent to Max):
        - deletemarker("Ringo")         -> "deletemarker Ringo"
        - deletemarker("Ringo Starr")   -> "deletemarker Ringo Starr"
        """
        names = names.strip()
        if not names:
            return {"ok": False, "message": "names cannot be empty"}
        return _send_max_message(f"deletemarker {names}")

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

    return mcp
