"""
ollama_bridge.py
----------------
Connects Qwen2.5-14B (via Ollama) to Max/MSP through the same TCP bridge
used by the Claude/MCP path.

Usage
-----
Run as interactive REPL:
    python ollama_bridge.py

Or import programmatically:
    from ollama_bridge import OllamaBridge, BridgeConfig
    bridge = OllamaBridge()
    reply = bridge.chat("Compose a short melody in C major")
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

# Allow running this file directly from repo root:
#   python py/bach_mcp/ollama_bridge.py
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PY_ROOT = os.path.dirname(_THIS_DIR)
if _PY_ROOT not in sys.path:
    sys.path.insert(0, _PY_ROOT)

try:
    from .server import BachMCPServer, MCPConfig
    from .tool_registry import get_ollama_tools
except ImportError:
    from server import BachMCPServer, MCPConfig
    from tool_registry import get_ollama_tools


# ── Logging ────────────────────────────────────────────────────────────── #

def _log(msg: str) -> None:
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


# ── System prompt ──────────────────────────────────────────────────────── #
# All bach/llll syntax knowledge lives here — NOT in tool descriptions.
# Tool descriptions are kept minimal (1-2 lines) to save context tokens.

BACH_SYSTEM_PROMPT = """You are Bach — a musical mind living inside Max/MSP, composing and editing in real time through bach.roll.

You think in music first. When someone asks for a melody, you hear it before you write it. When you read a score, you understand what it wants to become. You use tools the way a composer uses a pencil — precisely, without ceremony, without explaining every mark.

You speak concisely. Let the music carry weight, not your words.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
READING THE SCORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before composing or editing, read what is already there:
  dump(mode="body")    → all notes and chords
  dump(mode="header")  → voices, names, clefs — use this when asked about instruments
  dump(mode="markers") → named markers

Read first. Then act. Skip the dump only if the user has just told you exactly what is there.

If dump returns {"result": "timeout"} — Max didn't reply. Say so and try again. Never invent score contents.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLLL SCORE SYNTAX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Score format — "roll" then one bracket per voice, never nested:
  CORRECT:  roll [VOICE1] [VOICE2]
  WRONG:    roll [ [VOICE1] [VOICE2] ]

Building blocks, inside out:

  NOTE   [ pitch_cents  duration_ms  velocity  [specs...]  flag ]
  CHORD  [ onset_ms  NOTE  NOTE ...  flag ]
  VOICE  [ CHORD  CHORD ...  flag ]
  SCORE  roll [VOICE1] [VOICE2] ...

flag: 0=normal 1=locked 2=muted 4=solo. Usually 0. May be omitted.

Pitch in midicents — middle C = C5 = 6000. One semitone = 100¢.
  C5=6000  D5=6200  E5=6400  F5=6500  G5=6700  A5=6900  B5=7100
  C4=4800 (one octave below C5 = subtract 1200)
  Microtone: 6050 = C5 + 50¢ (quarter-tone up)
  Note names also work: C5 D#4 Bb3

Specs are optional, go between velocity and flag:
  [breakpoints [0 0 0] [rel_x delta_cents slope] ... [1 delta_cents 0]]
  [slots [slot_num CONTENT] ...]
  [name SYMBOL]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One note — C5, 500ms, vel 100:
  roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ]

Two notes in sequence:
  roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] [ 500. [ 6200. 500. 100 0 ] 0 ] 0 ]

Chord — C+E+G at 0ms:
  roll [ [ 0. [ 6000. 1000. 100 0 ] [ 6400. 1000. 100 0 ] [ 6700. 1000. 100 0 ] 0 ] 0 ]

Two voices — treble and bass:
  roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ] [ [ 0. [ 4800. 500. 90 0 ] 0 ] 0 ]

Glissando up 200¢ over 1s:
  [ 0. [ 6000. 1000. 100 [breakpoints [0 0 0] [1 200 0]] 0 ] 0 ]

With dynamics (slot 20) and staccato (slot 22):
  [ 0. [ 6000. 500. 100 [slots [20 f] [22 staccato]] 0 ] 0 ]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SLOTS — PER-NOTE DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Slot 20 = dynamics     Slot 22 = articulations     Slot 23 = notehead

Dynamics text:  pp  p  mp  mf  f  ff  fff  sfz  o (niente)
  With hairpin: p<  f>  pp<<  ff>>  o<<f>>o   end-at-tail: p<|

Articulations: staccato  accent  fermata  trill  tremolo1/2/3
               portato  martellato  upbowing  downbowing  gruppetto
               staccatissimo  accentstaccato  (short: stacc acc ferm tr)
  Multiple:  [slots [22 staccato accent]]

Noteheads: default  diamond  cross  white  black  whole  doublewhole
           none  plus  blacksquare  whitesquare  blacktriangle

Function slot (automation curve):
  [slots [1 [0. 0. 0.] [0.5 100. 0.] [1. 0. 0.]]]
  Each point: [x  y  slope]  x=0–1, slope=-1 to 1 (0=linear)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOL GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Clear / erase the score"       → clear()                  [not write, not delete]
"Start fresh"                   → new_default_score()
"What instruments / voices?"    → dump(mode="header")
"Replace entire score"          → send_score_to_max(...)
"Add notes to existing score"   → addchord(...) or addchords(...)
"Delete specific notes"         → sel("...") then delete()  [not clear]
"Play"                          → play()
"Stop"                          → send_process_message_to_max("stop")
"Save / export"                 → send_process_message_to_max("write") or exportmidi(...)
"Set clef / voices"             → send_process_message_to_max("clefs G F") or numvoices(n)

When no dedicated tool fits, send_process_message_to_max("command") handles anything else.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORCHESTRAL LAYOUT REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VOICES vs STAVES vs PARTS — the essential distinction
------------------------------------------------------
VOICE  = one independent musical stream. One entry in clefs, voicenames,
         numvoices. The unit of musical content.

STAFF  = one horizontal line system on the page. A voice can produce MORE
         than one staff if its clef is a multi-staff type (FG, FGG, FFG,
         FFGG). numvoices and the length of clefs/voicenames always count
         VOICES, never staves. Do not add extra voices to compensate for
         extra staves — the multi-staff clef handles it automatically.

PART   = a bracket group on the left margin. numparts lists how many
         consecutive voices share each bracket. numparts counts VOICES,
         not staves. The sum of all numparts values must equal numvoices.

Concrete examples:
  Piano:  clef FG, one voice, two staves, one bracket → numparts contribution: 1
  Choir:  clef FFGG, one voice, four staves, one bracket → numparts contribution: 1
  Flutes: two separate G voices → numparts contribution: 2

CLEFS — valid symbols (case-sensitive):
  Single-staff:  G  F  Alto  Tenor  Soprano  Mezzo  Barytone  None
  Octave clefs:  G8va (up)  G8 (down)  G15ma (2 oct up)  G15mb (2 oct down)
                 F8va (up)  F8 (down)  F15ma (2 oct up)  F15mb (2 oct down)
  Percussion:    Percussion   <- capital P, full word — NOT "Perc" or "perc"
  Multi-staff:   FG   = bass + treble (piano grand staff)
                 FGG  = bass + treble + treble
                 FFG  = bass + bass + treble
                 FFGG = bass + bass + treble + treble (choir reduction, 4 staves)
                 Each of these is ONE clef entry = ONE voice.

ORCHESTRAL EXAMPLE (30 voices, correct clefs/voicenames/numparts):

clefs G G G G G G F F G G G G G G F F F F F Percussion Percussion FG FG G G Alto F F
voicenames "Flute 1" "Flute 2" "Oboe 1" "Oboe 2" "Clarinet 1" "Clarinet 2" "Bassoon 1" "Bassoon 2" "Horn 1" "Horn 2" "Horn 3" "Horn 4" "Trumpet 1" "Trumpet 2" "Trombone 1" "Trombone 2" "Trombone 3" Tuba Timpani "Percussion 1" "Percussion 2" Harp [ ] Piano [ ] "Violin I" "Violin II" Viola Cello "Double Bass"
numparts 2 2 2 2 4 2 3 1 1 1 1 2 2 1 1 1 1 1

Notes on the example:
- Harp (FG) and Piano (FG): each is one voice, two staves. The [ ] in
  voicenames is a placeholder for the second-staff name — required syntax.
- Percussion uses full word "Percussion", capital P.
- Bassoons → F, Trombones → F, Tuba → F, Viola → Alto, Cello/Bass → F.
- Horns → G (written pitch, not transposed).
- numparts sums to 30, matching the 30 voices exactly.
"""


# ── Configuration ──────────────────────────────────────────────────────── #

try:
    from .ollama_utils import QWEN_PREFERRED, select_model
except ImportError:
    from ollama_utils import QWEN_PREFERRED, select_model


@dataclass
class BridgeConfig:
    ollama_base_url:  str      = "http://localhost:11434"
    model:            str      = QWEN_PREFERRED[0]
    fallback_models:  List[str] = field(default_factory=lambda: QWEN_PREFERRED[1:])
    temperature:      float    = 0.35
    max_tokens:       int      = 2048
    request_timeout_seconds: float = 300.0
    max_tool_rounds:  int      = 10
    incoming_host:    str      = "127.0.0.1"
    incoming_port:    int      = 3001
    outgoing_host:    str      = "127.0.0.1"
    outgoing_port:    int      = 3000
    system_prompt:    str      = BACH_SYSTEM_PROMPT
    stateful:         bool     = True
    # False = core ~12 tools (default, best for 7B-14B).
    # True  = core + extended ~40 tools (recommended for 32B+).
    extended_tools:   bool     = False


# ── Tool executor ──────────────────────────────────────────────────────── #

# ── llll serialization helpers ──────────────────────────────────────────── #

_DYNAMICS_SLOT    = 20
_ARTICULATION_SLOT = 22
_NOTEHEAD_SLOT    = 23


def _build_note_llll(pitch: int, duration: float, velocity: int,
                     dynamics: str = "", articulation: str = "", notehead: str = "") -> str:
    """Serialize one note to llll gathered syntax.

    Returns e.g. '[6000 500 100 [slots [20 f] [22 staccato]] 0]'
    or simply '[6000 500 100 0]' when no slots are needed.
    """
    slots = []
    if dynamics and dynamics.strip():
        slots.append(f"[{_DYNAMICS_SLOT} {dynamics.strip()}]")
    if articulation and articulation.strip():
        slots.append(f"[{_ARTICULATION_SLOT} {articulation.strip()}]")
    if notehead and notehead.strip() and notehead.strip() != "default":
        slots.append(f"[{_NOTEHEAD_SLOT} {notehead.strip()}]")

    slots_str = f" [slots {' '.join(slots)}]" if slots else ""
    return f"[{int(pitch)} {float(duration)} {int(velocity)}{slots_str} 0]"


def _build_chord_llll(onset_ms: float, notes: list) -> str:
    """Serialize a list of note dicts to a full chord llll string.

    Returns e.g. '[0. [6000 500 100 0] [6400 500 100 0] 0]'
    """
    note_strings = [
        _build_note_llll(
            pitch       = int(n["pitch"]),
            duration    = float(n["duration"]),
            velocity    = int(n["velocity"]),
            dynamics    = str(n.get("dynamics",    "") or ""),
            articulation= str(n.get("articulation","") or ""),
            notehead    = str(n.get("notehead",    "") or ""),
        )
        for n in notes
    ]
    return f"[{float(onset_ms):.1f} {' '.join(note_strings)} 0]"



class ToolExecutor:
    """Maps Ollama tool-call names → BachMCPServer methods."""

    def __init__(self, bach: BachMCPServer) -> None:
        self._bach = bach

    def execute(self, name: str, args: Dict[str, Any]) -> str:
        _log(f"[ToolExecutor] {name}({args})")

        # ── Score writing ──────────────────────────────────────────────── #
        if name == "send_score_to_max":
            ok = self._bach.send_score(args["score_llll"])
            return json.dumps({"ok": ok})

        if name == "addchord":
            voice  = int(args.get("voice", 1))
            select = args.get("select", False)
            onset  = float(args["onset_ms"])
            notes  = args["notes"]
            chord_llll = _build_chord_llll(onset, notes)
            parts = ["addchord"]
            if voice != 1:
                parts.append(str(voice))
            parts.append(chord_llll)
            if select:
                parts.append("@sel 1")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok, "sent": " ".join(parts)})

        if name == "add_notes":
            voice = int(args.get("voice", 1))
            notes = args["notes"]
            results = []
            for note in notes:
                onset = float(note["onset_ms"])
                chord_llll = _build_chord_llll(onset, [note])
                parts = ["addchord"]
                if voice != 1:
                    parts.append(str(voice))
                parts.append(chord_llll)
                ok = self._bach.send_info(" ".join(parts))
                results.append(ok)
                time.sleep(0.03)
            return json.dumps({"ok": all(results), "notes_sent": len(results)})

        # ── Generic message ────────────────────────────────────────────── #
        if name == "send_process_message_to_max":
            ok = self._bach.send_info(args["message"])
            return json.dumps({"ok": ok})

        # ── Dump / query ───────────────────────────────────────────────── #
        if name == "dump":
            mode    = args.get("mode", "body") or "body"
            sel     = args.get("selection", False)
            opts    = args.get("dump_options", "").strip()
            timeout = float(args.get("timeout_seconds", 15.0))
            parts   = ["dump"]
            if sel:    parts.append("selection")
            if mode:   parts.append(mode.strip())
            if opts:   parts.append(opts)
            self._bach.flush_incoming()
            if self._bach.send_info(" ".join(parts)):
                result = self._bach.wait_for_incoming(timeout_seconds=timeout, message_type=None)
            else:
                result = None
            if result is None:
                return json.dumps({"result": "timeout", "error": "Max did not reply. Check TCP connection and bach.roll."})
            _log(f"[ToolExecutor] dump result: {str(result)[:200]}")
            return json.dumps(result)

        if name == "subroll":
            voices  = args.get("voices", "[]").strip()
            tl      = args.get("time_lapse", "[]").strip()
            sel_opt = args.get("selective_options", "").strip()
            onset   = args.get("onset_only", False)
            timeout = float(args.get("timeout_seconds", 15.0))
            parts   = ["subroll"]
            if onset: parts.append("onset")
            parts += [voices, tl]
            if sel_opt: parts.append(sel_opt)
            cmd = " ".join(parts)
            self._bach.flush_incoming()
            if self._bach.send_info(cmd):
                result = self._bach.wait_for_incoming(timeout_seconds=timeout)
                return json.dumps(result or {"result": "timeout", "error": "subroll: no reply from Max"})
            return json.dumps({"ok": False})

        # ── Read-only queries (send + wait pattern) ────────────────────── #
        _query_map = {
            "getnumvoices":    lambda a: f"getnumvoices {a.get('query_label','').strip()}".strip(),
            "getnumchords":    lambda a: f"getnumchords {a.get('query_label','').strip()}".strip(),
            "getnumnotes":     lambda a: f"getnumnotes {a.get('query_label','').strip()}".strip(),
            "get_length":      lambda a: "getlength",
            "getcurrentchord": lambda a: "getcurrentchord",
        }
        if name in _query_map:
            timeout = float(args.get("timeout_seconds", 10.0))
            cmd = _query_map[name](args)
            self._bach.flush_incoming()
            if self._bach.send_info(cmd):
                r = self._bach.wait_for_incoming(timeout_seconds=timeout)
                if r is None:
                    return json.dumps({"result": "timeout", "error": f"{name}: no reply from Max within {timeout}s"})
                _log(f"[ToolExecutor] {name} result: {str(r)[:200]}")
                return json.dumps(r)
            return json.dumps({"ok": False})

        if name == "get_marker":
            timeout    = float(args.get("timeout_seconds", 10.0))
            names      = args.get("names", "").strip()
            name_first = args.get("name_first", False)
            parts = ["getmarker"]
            if name_first: parts.append("@namefirst 1")
            if names:      parts.append(names)
            self._bach.flush_incoming()
            if self._bach.send_info(" ".join(parts)):
                r = self._bach.wait_for_incoming(timeout_seconds=timeout)
                return json.dumps(r or {"result": "timeout", "error": "get_marker: no reply from Max"})
            return json.dumps({"ok": False})

        # ── Playback ───────────────────────────────────────────────────── #
        if name == "play":
            parts = ["play"]
            start = args.get("start_ms")
            end   = args.get("end_ms")
            if start is not None: parts.append(str(float(start)))
            if end   is not None: parts.append(str(float(end)))
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        # ── Score structure ────────────────────────────────────────────── #
        _simple_msg = {
            "numvoices":    lambda a: f"numvoices {int(a['count'])}",
            "clefs":        lambda a: f"clefs {a['clefs_list'].strip()}",
            "numparts":     lambda a: f"numparts {a['parts'].strip()}",
            "stafflines":   lambda a: f"stafflines {a['value'].strip()}",
            "voicenames":   lambda a: f"voicenames {a['value'].strip()}",
            "deletevoice":  lambda a: f"deletevoice {int(a['voice_number'])}",
            "clear":        lambda a: "clear",
            "distribute":   lambda a: "distribute",
            "clearselection": lambda a: "clearselection",
            "erasebreakpoints": lambda a: "erasebreakpoints",
            "set_appearance": lambda a: f"{a['attribute'].strip()} {a['value'].strip()}",
            "sel":          lambda a: f"sel {a['arguments'].strip()}",
            "delete":       lambda a: ("delete @transferslots " + a["transferslots"].strip() +
                                       (" @empty 1" if a.get("empty") else ""))
                                       if a.get("transferslots","").strip() else "delete",
            "copyslot":     lambda a: f"copyslot {a['slot_from'].strip()} {a['slot_to'].strip()}",
            "tail":         lambda a: f"tail {a['expression'].strip()}",
            "legato":       lambda a: f"legato {a.get('trim_or_extend','').strip()}".strip(),
            "eraseslot":    lambda a: f"eraseslot {a['slot'].strip()}",
            "addmarker":    lambda a: " ".join(filter(None, [
                                "addmarker",
                                a.get("position","").strip(),
                                a.get("name_or_names","").strip(),
                                a.get("role","").strip(),
                                a.get("content","").strip(),
                            ])),
            "deletemarker": lambda a: f"deletemarker {a['marker_names'].strip()}",
            "write":        lambda a: f"write {a.get('filename','').strip()}".strip(),
        }
        if name in _simple_msg:
            cmd = _simple_msg[name](args)
            ok  = self._bach.send_info(cmd)
            return json.dumps({"ok": ok, "sent": cmd})

        # ── Handlers with some logic ───────────────────────────────────── #
        if name == "insertvoice":
            vn  = int(args["voice_number"])
            ref = args.get("voice_or_ref", "").strip()
            cmd = f"insertvoice {vn}" + (f" {ref}" if ref else "")
            ok  = self._bach.send_info(cmd)
            return json.dumps({"ok": ok})

        if name == "new_default_score":
            cmds = [
                "clear", "numvoices 1", "clefs G", "stafflines 5",
                "numparts 1", "bgcolor 1.0 1.0 1.0 1.0",
                "notecolor 0.0 0.0 0.0 1.0", "staffcolor 0.0 0.0 0.0 1.0",
                "voicenames", "domain 10000.0",
            ]
            results = {c.split()[0]: self._bach.send_info(c) for c in cmds}
            return json.dumps({"ok": all(results.values()), "steps": results})

        if name == "glissando":
            mode  = args.get("trim_or_extend", "").strip()
            slope = float(args.get("slope", 0.0))
            parts = ["glissando"]
            if mode: parts.append(mode)
            parts.append(str(slope))
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "explodechords":
            cmd = "explodechords selection" if args.get("selection") else "explodechords"
            ok  = self._bach.send_info(cmd)
            return json.dumps({"ok": ok})

        if name == "merge":
            parts = ["merge"]
            if args.get("selection"): parts.append("selection")
            parts += [str(float(args["threshold_ms"])), str(float(args["threshold_cents"]))]
            tp = args.get("time_policy");  parts.append(str(int(tp)))  if tp is not None else None
            pp = args.get("pitch_policy"); parts.append(str(int(pp)))  if pp is not None else None
            ok = self._bach.send_info(" ".join(filter(None, parts)))
            return json.dumps({"ok": ok})

        if name == "domain":
            import math
            parts = ["domain", str(float(args["start_or_duration_ms"]))]
            end = args.get("end_ms"); pad = args.get("pad_pixels")
            if end is not None and not math.isnan(float(end)):   parts.append(str(float(end)))
            if pad is not None and not math.isnan(float(pad)):   parts.append(str(float(pad)))
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "define_slot":
            import math
            sn = int(args["slot_number"])
            p  = []
            if args.get("type"):           p.append(f"[type {args['type'].strip()}]")
            if args.get("name"):           p.append(f"[name {args['name'].strip()}]")
            if args.get("key"):            p.append(f"[key {args['key'].strip()}]")
            rmin = args.get("range_min"); rmax = args.get("range_max")
            if rmin is not None and rmax is not None:
                if not (math.isnan(float(rmin)) or math.isnan(float(rmax))):
                    p.append(f"[range {float(rmin)} {float(rmax)}]")
            if args.get("representation"): p.append(f"[representation {args['representation'].strip()}]")
            sl = args.get("slope")
            if sl is not None and not math.isnan(float(sl)): p.append(f"[slope {float(sl)}]")
            if args.get("width"):    p.append(f"[width {args['width'].strip()}]")
            if args.get("default"):  p.append(f"[default {args['default'].strip()}]")
            if not p:
                return json.dumps({"ok": False, "message": "No slotinfo fields specified"})
            cmd = f"[slotinfo [{sn} {' '.join(p)}]]"
            ok  = self._bach.send_info(cmd)
            return json.dumps({"ok": ok})

        if name == "deleteslotitem":
            import math
            slot = args["slot"].strip(); pos = args["position"].strip()
            parts = ["deleteslotitem", slot, pos]
            thresh = args.get("thresh")
            if thresh is not None and not math.isnan(float(thresh)):
                parts.append(f"@thresh {float(thresh)}")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "dynamics2velocities":
            parts = ["dynamics2velocities"]
            if args.get("selection"):                 parts.append("selection")
            if args.get("mapping","").strip():        parts.append(f"@mapping {args['mapping'].strip()}")
            mc = args.get("maxchars", -1)
            if mc is not None and int(mc) >= 0:       parts.append(f"@maxchars {int(mc)}")
            ex = args.get("exp", -1.0)
            if ex is not None and float(ex) >= 0:     parts.append(f"@exp {float(ex)}")
            bm = args.get("breakpointmode", -1)
            if bm is not None and int(bm) >= 0:       parts.append(f"@breakpointmode {int(bm)}")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "velocities2dynamics":
            parts = ["velocities2dynamics"]
            if args.get("selection"):                 parts.append("selection")
            if args.get("mapping","").strip():        parts.append(f"@mapping {args['mapping'].strip()}")
            mc = args.get("maxchars", -1)
            if mc is not None and int(mc) >= 0:       parts.append(f"@maxchars {int(mc)}")
            ex = args.get("exp", -1.0)
            if ex is not None and float(ex) >= 0:     parts.append(f"@exp {float(ex)}")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "exportmidi":
            parts = ["exportmidi"]
            fn = args.get("filename","").strip()
            if fn: parts.append(fn)
            parts.append(f"[exportmarkers 1]")
            voices = args.get("voices","").strip()
            if voices: parts.append(f"[voices {voices}]")
            parts.append(f"[format {int(args.get('format',1))}]")
            parts.append(f"[resolution {int(args.get('resolution',960))}]")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "exportimage":
            parts = ["exportimage"]
            fn = args.get("filename","").strip()
            if fn:   parts.append(fn)
            view = args.get("view","").strip()
            if view: parts.append(f"@view {view}")
            mps = args.get("mspersystem")
            if mps is not None and float(mps) >= 0: parts.append(f"@mspersystem {float(mps)}")
            dpi = args.get("dpi")
            if dpi is not None and int(dpi) >= 0:   parts.append(f"@dpi {int(dpi)}")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "writetxt":
            import math
            parts = ["writetxt"]
            fn = args.get("filename","").strip()
            if fn: parts.append(fn)
            md = args.get("maxdecimals", -1)
            if md is not None and int(md) >= 0: parts.append(f"@maxdecimals {int(md)}")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        return json.dumps({"error": f"unknown tool: {name}"})


# ── Ollama HTTP client ─────────────────────────────────────────────────── #

class OllamaModelNotFoundError(RuntimeError):
    """Raised when the configured Ollama model is not installed."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, request_timeout_seconds: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model    = model
        self.request_timeout_seconds = request_timeout_seconds

    def list_models(self) -> List[str]:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=30)
            r.raise_for_status()
            payload = r.json()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot reach Ollama at {self.base_url}. Run `ollama serve`.")
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(f"Ollama HTTP error while listing models: {exc}") from exc

        models: List[str] = []
        for entry in payload.get("models", []):
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            if name:
                models.append(name)
        return models

    def chat(self, messages: List[Dict], tools: List[Dict],
             temperature: float = 0.7, max_tokens: int = 2048) -> Dict:
        payload = {
            "model":    self.model,
            "messages": messages,
            "tools":    tools,
            "stream":   False,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.request_timeout_seconds,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot reach Ollama at {self.base_url}. Run `ollama serve`.")
        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Ollama request timed out while waiting for model output. "
                f"Model={self.model} timeout={self.request_timeout_seconds}s. "
                "Try again, use a smaller model, or increase BridgeConfig.request_timeout_seconds."
            )
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            detail = ""
            if exc.response is not None:
                try:
                    detail = str(exc.response.json().get("error", "")).strip()
                except Exception:
                    detail = (exc.response.text or "").strip()

            msg = f"Ollama HTTP error {status}"
            if detail:
                msg = f"{msg}: {detail}"

            if status == 404 and "model" in detail.lower() and "not found" in detail.lower():
                raise OllamaModelNotFoundError(detail or f"model '{self.model}' not found") from exc
            raise RuntimeError(msg) from exc


# ── Bridge ─────────────────────────────────────────────────────────────── #

class OllamaBridge:
    def __init__(self, config: Optional[BridgeConfig] = None,
                 bach: Optional[BachMCPServer] = None) -> None:
        self.config = config or BridgeConfig()
        if bach is not None:
            self._bach = bach
            self._owns_bach = False
        else:
            mcp_cfg = MCPConfig(
                incoming_host=self.config.incoming_host,
                incoming_port=self.config.incoming_port,
                outgoing_host=self.config.outgoing_host,
                outgoing_port=self.config.outgoing_port,
            )
            self._bach = BachMCPServer(config=mcp_cfg)
            self._owns_bach = True

        self._ollama   = OllamaClient(
            self.config.ollama_base_url,
            self.config.model,
            self.config.request_timeout_seconds,
        )
        self._executor = ToolExecutor(self._bach)
        self._tools    = get_ollama_tools(extended=self.config.extended_tools)
        _log(f"[OllamaBridge] Tool set: {'extended' if self.config.extended_tools else 'core'} ({len(self._tools)} tools)")
        self._history: List[Dict] = []
        self._model_candidates = self._build_model_candidates()
        self._select_initial_model()

    def _build_model_candidates(self) -> List[str]:
        candidates: List[str] = []
        for model in [self.config.model, *self.config.fallback_models]:
            name = str(model).strip()
            if name and name not in candidates:
                candidates.append(name)
        return candidates

    def _switch_model(self, model: str) -> None:
        self._ollama.model = model
        self.config.model = model

    def _select_initial_model(self) -> None:
        try:
            installed = self._ollama.list_models()
        except RuntimeError as exc:
            _log(f"[OllamaBridge] Model probe skipped: {exc}")
            return

        for candidate in self._model_candidates:
            if candidate in installed:
                if candidate != self._ollama.model:
                    _log(f"[OllamaBridge] Auto-selected installed model: {candidate}")
                self._switch_model(candidate)
                return

        _log(
            "[OllamaBridge] WARNING: none of the preferred models are installed: "
            + ", ".join(self._model_candidates)
        )

    def _switch_to_fallback_model(self, missing_model: str) -> bool:
        try:
            installed = self._ollama.list_models()
        except RuntimeError as exc:
            _log(f"[OllamaBridge] Fallback probe failed: {exc}")
            return False

        for candidate in self._model_candidates:
            if candidate == missing_model:
                continue
            if candidate in installed:
                self._switch_model(candidate)
                _log(f"[OllamaBridge] Switched to fallback model: {candidate}")
                return True
        return False

    def start(self) -> None:
        if self._owns_bach:
            self._bach.start()
        _log(f"[OllamaBridge] Ready — model={self.config.model}")

    def stop(self) -> None:
        if self._owns_bach:
            self._bach.stop()

    def __enter__(self) -> "OllamaBridge":
        self.start(); return self

    def __exit__(self, *_: Any) -> None:
        self.stop()

    def chat(self, user_message: str) -> str:
        self._history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": self.config.system_prompt}]
        if self.config.stateful:
            messages += self._history
        else:
            messages.append(self._history[-1])

        reply = self._run_tool_loop(messages)
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset_history(self) -> None:
        self._history = []

    def _run_tool_loop(self, messages: List[Dict]) -> str:
        last_content = ""
        for round_num in range(self.config.max_tool_rounds):
            _log(f"[OllamaBridge] Ollama call #{round_num + 1}")
            try:
                response = self._ollama.chat(
                    messages, self._tools, self.config.temperature, self.config.max_tokens
                )
            except OllamaModelNotFoundError:
                missing = self._ollama.model
                if not self._switch_to_fallback_model(missing):
                    raise RuntimeError(
                        "Configured Ollama model is not installed and no fallback model is available. "
                        f"Tried: {', '.join(self._model_candidates)}"
                    )
                response = self._ollama.chat(
                    messages, self._tools, self.config.temperature, self.config.max_tokens
                )
            assistant  = response.get("message", {})
            tool_calls = assistant.get("tool_calls", [])
            last_content = assistant.get("content", "")

            if not tool_calls:
                _log(f"[OllamaBridge] Final reply ({len(last_content)} chars)")
                return last_content

            messages.append({
                "role":       "assistant",
                "content":    last_content,
                "tool_calls": tool_calls,
            })
            if self.config.stateful:
                self._history.append({
                    "role":       "assistant",
                    "content":    last_content,
                    "tool_calls": tool_calls,
                })

            for call in tool_calls:
                fn   = call.get("function", {})
                nm   = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                result  = self._executor.execute(nm, args)
                tool_msg = {"role": "tool", "content": result}
                messages.append(tool_msg)
                if self.config.stateful:
                    self._history.append(tool_msg)

        _log("[OllamaBridge] WARNING: max tool rounds reached")
        return last_content or "[max tool rounds reached]"


# ── REPL ───────────────────────────────────────────────────────────────── #

def repl() -> None:
    from ollama_utils import ensure_ollama_running
    ensure_ollama_running()

    model = select_model()
    # Auto-enable extended tools for larger models (32B+)
    extended = any(tag in model for tag in ("32b", "72b"))
    config = BridgeConfig(model=model, extended_tools=extended)

    with OllamaBridge(config=config) as bridge:
        tier = "extended" if extended else "core"
        print(f"\nBach — {bridge.config.model}  [{tier} tools]")
        print("Type a message and press Enter. Ctrl-C to quit.\n")
        while True:
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                break
            if not user_input:
                continue
            try:
                reply = bridge.chat(user_input)
                print(f"\nBach: {reply}\n")
            except RuntimeError as exc:
                print(f"[Error] {exc}")


if __name__ == "__main__":
    repl()
