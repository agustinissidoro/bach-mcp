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

BACH_SYSTEM_PROMPT = """You are Bach, an AI music co-composer connected live to Max/MSP via bach.roll.
Use the available tools to compose, edit, and control music in real time.

════════════════════════════════════════════════════
SESSION PROTOCOL
════════════════════════════════════════════════════
- At session start call dump(mode="body") to read the current score.
- Before adding/editing notes call dump(mode="body") to know current state.
- After sending a score call dump(mode="body") to confirm changes.
- Skip dump when the user has just provided the score context, or explicitly says not to.

════════════════════════════════════════════════════
LLLL SCORE FORMAT  (bach gathered syntax)
════════════════════════════════════════════════════
Scores start with "roll" followed by one llll per voice (NOT nested in an outer bracket).

  CORRECT:   roll [VOICE1] [VOICE2]
  WRONG:     roll [ [VOICE1] [VOICE2] ]

Hierarchy (inside out):

  NOTE:    [ pitch_cents duration_ms velocity [specs...] flag ]
           flag: 0=normal 1=locked 2=muted 4=solo (sum to combine). May be omitted.
           specs (optional, between velocity and flag, any order):
             [breakpoints [0 0 0] [rel_x delta_cents slope]...[1 delta_cents slope]]
             [slots [slot_num CONTENT]...]
             [name NAME]

  CHORD:   [ onset_ms NOTE1 NOTE2 ... flag ]

  VOICE:   [ CHORD1 CHORD2 ... flag ]

  SCORE:   roll [VOICE1] [VOICE2] ...

PITCH: midicents. Middle C = C5 = 6000. One semitone = 100 cents.
  Microtones: 6050 = C5 + 50¢ (quarter tone up).
  Note names also accepted: C5 D#4 Bb3 Eq4 (E quarter-tone sharp).

EXAMPLES:
  One note, C5, 500ms, vel 100:
    roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ]

  Two notes in sequence, one voice:
    roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] [ 500. [ 6400. 500. 100 0 ] 0 ] 0 ]

  Chord (C+E simultaneously):
    roll [ [ 0. [ 6000. 1000. 100 0 ] [ 6400. 1000. 100 0 ] 0 ] 0 ]

  Two voices:
    roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ] [ [ 0. [ 5500. 500. 90 0 ] 0 ] 0 ]

  Note with staccato (slot 22) and ff dynamic (slot 20):
    [ 0. [ 6000. 500. 100 [slots [22 staccato] [20 ff]] 0 ] 0 ]

  Note with glissando up 200¢:
    [ 0. [ 6000. 1000. 100 [breakpoints [0 0 0] [1 200 0]] 0 ] 0 ]

════════════════════════════════════════════════════
SLOTS
════════════════════════════════════════════════════
Slots store per-note data. Key defaults:
  Slot 20 = dynamics  (type: dynamics)
  Slot 22 = articulations (type: articulations)
  Slot 23 = notehead  (type: notehead)

DYNAMICS (slot 20) — plain text syntax:
  Single marking:  "mp"  "f"  "pp"
  With hairpin:    "p<"  "f>"  "pp<<"  "ff>>"
  Sequence:        "p< ff> mp"
  Dal/al niente:   "o<<f>>o"
  End at tail:     "p<|"   (| = empty terminal mark)
  Markings: pppp ppp pp p mp mf f ff fff ffff sfz sf sfp o (niente)
  Hairpins: < > << >> = _ --   (< cresc, > dim, << exp cresc, >> exp dim)

ARTICULATIONS (slot 22):
  staccato (stacc), accent (acc), fermata (ferm), portato (port),
  martellato (mart), trill (tr), tremolo1/2/3 (trem1/2/3),
  upbowing (ubow), downbowing (dbow), gruppetto (grupp),
  upmordent (umord), downmordent (dmord), doublemordent (mmord),
  staccatissimo (staccmo), accentstaccato (accstacc), etc.
  Multiple: "[slots [22 staccato accent]]"

NOTEHEADS (slot 23):
  default diamond cross white black whole doublewhole none
  blacksquare whitesquare blacktriangle whitetriangle plus

FUNCTION slots (automation, e.g. amplitude):
  [slots [1 [0. 0. 0.] [0.5 100. 0.] [1. 0. 0.]]]
  Each point: [x y slope]  x=0-1 (position), slope=-1 to 1 (0=linear)

COMBINING slots in one string:
  "[slots [20 ff] [22 staccato] [23 diamond]]"

════════════════════════════════════════════════════
CLEFS & VOICES
════════════════════════════════════════════════════
Clef symbols: G F FG alto perc auto none G8 G8va F8 F8va
FG = grand staff (ONE voice, TWO staves — treble+bass linked).

Piano approaches:
  A) 1 voice FG:   numvoices(1) clefs("FG") numparts("1")
     One data stream, 2 staves. Standard for orchestral piano part.
  B) 2 voices:     numvoices(2) clefs("G F") numparts("2")
     Independent RH/LH streams. Use for solo/chamber music.

numparts groups voices visually. Integers must sum to voice count.
  "1 1 1" = three separate staves
  "2"     = two voices on one grand-staff ensemble
  "1 3"   = voice 1 alone, voices 2-3-4 together

════════════════════════════════════════════════════
SELECTION SYNTAX (sel / select)
════════════════════════════════════════════════════
  "all"                        select everything
  "notes" "chords" "markers"   select by category
  "1000 3000 [] []"            time range any pitch
  "1000 3000 6000 7200"        time range + pitch range
  "[] [] [] [] 2"              all notes in voice 2
  "chord 3"                    3rd chord voice 1
  "chord 3 2"                  2nd chord voice 3
  "chord -1"                   last chord
  "note if velocity == 100"    conditional
  "note if cents == 6000"      all middle C's
  "note if [cents % 1200] == 0" all C's any octave
  "marker if onset > 5000"     markers after 5s
  clearselection() to deselect all.

════════════════════════════════════════════════════
TOOL QUICK REFERENCE
════════════════════════════════════════════════════
WRITE SCORE:
  send_score_to_max(score_llll)   — replace whole score
  addchord(chord_llll, voice=1)   — insert one chord
  addchords(chords_llll)          — insert across voices

READ SCORE:
  dump(mode="body")               — full note data
  dump(mode="header")             — metadata
  dump(mode="markers")            — markers
  subroll(voices, time_lapse)     — extract slice

STRUCTURE:
  numvoices(n) clefs(s) numparts(s) stafflines(s) voicenames(s)

PLAYBACK:
  play()  send_process_message_to_max("stop")
  play(start_ms=0, end_ms=5000)

SELECTION → EDIT:
  sel("all") → delete()
  sel("note if cents==6000") → tail("= tail + 500")
  clearselection()

APPEARANCE:
  bgcolor(r,g,b,a)  notecolor(r,g,b,a)  staffcolor(r,g,b,a)
  domain(10000)     set_appearance("zoom", "150")

Be concise in prose — let the music speak.
"""


# ── Configuration ──────────────────────────────────────────────────────── #

@dataclass
class BridgeConfig:
    ollama_base_url:  str   = "http://localhost:11434"
    model:            str   = "qwen2.5:14b"
    temperature:      float = 0.7
    max_tokens:       int   = 2048
    max_tool_rounds:  int   = 10
    incoming_host:    str   = "127.0.0.1"
    incoming_port:    int   = 3001
    outgoing_host:    str   = "127.0.0.1"
    outgoing_port:    int   = 3000
    system_prompt:    str   = BACH_SYSTEM_PROMPT
    stateful:         bool  = True


# ── Tool executor ──────────────────────────────────────────────────────── #

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
            voice = args.get("voice", 1)
            select = args.get("select", False)
            chord = args["chord_llll"].strip()
            parts = ["addchord"]
            if voice != 1:
                parts.append(str(int(voice)))
            parts.append(chord)
            if select:
                parts.append("@sel 1")
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

        if name == "addchords":
            import math
            chords = args["chords_llll"].strip()
            offset = args.get("offset_ms")
            parts = ["addchords"]
            if offset is not None and not math.isnan(float(offset)):
                parts.append(str(float(offset)))
            parts.append(chords)
            ok = self._bach.send_info(" ".join(parts))
            return json.dumps({"ok": ok})

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
            result = self._bach.wait_for_incoming(
                timeout_seconds=timeout,
                message_type=None,
            ) if self._bach.send_info(" ".join(parts)) else None
            return json.dumps(result or {"result": "timeout"})

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
            if self._bach.send_info(cmd):
                result = self._bach.wait_for_incoming(timeout_seconds=timeout)
                return json.dumps(result or {"result": "timeout"})
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
            if self._bach.send_info(cmd):
                r = self._bach.wait_for_incoming(timeout_seconds=timeout)
                return json.dumps(r or {"result": "timeout"})
            return json.dumps({"ok": False})

        if name == "get_marker":
            timeout    = float(args.get("timeout_seconds", 10.0))
            names      = args.get("names", "").strip()
            name_first = args.get("name_first", False)
            parts = ["getmarker"]
            if name_first: parts.append("@namefirst 1")
            if names:      parts.append(names)
            if self._bach.send_info(" ".join(parts)):
                r = self._bach.wait_for_incoming(timeout_seconds=timeout)
                return json.dumps(r or {"result": "timeout"})
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

class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model    = model

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
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot reach Ollama at {self.base_url}. Run `ollama serve`.")
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(f"Ollama HTTP error: {exc}") from exc


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

        self._ollama   = OllamaClient(self.config.ollama_base_url, self.config.model)
        self._executor = ToolExecutor(self._bach)
        self._tools    = get_ollama_tools()
        self._history: List[Dict] = []

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
            response   = self._ollama.chat(messages, self._tools,
                                           self.config.temperature, self.config.max_tokens)
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
    config = BridgeConfig()
    print(f"Bach Ollama Bridge — {config.model}")
    print("Type a message and press Enter. Ctrl-C to quit.\n")
    with OllamaBridge(config=config) as bridge:
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
