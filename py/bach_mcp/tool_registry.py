"""
tool_registry.py
----------------
Lean tool schemas for Ollama/Qwen.
Claude/MCP uses mcp_app.py unchanged — this file is Qwen-only.

Design principle: descriptions are 1-2 lines max. All syntax knowledge
lives in the system prompt (ollama_bridge.py). Tools just say
what they do and what args they take.

TWO TIERS
─────────
CORE (default, ~12 tools)
    Covers ~90 % of real use-cases. Recommended for 7 B–14 B models.
    Small models hallucinate badly with 40+ tools; the core set keeps
    the decision space tractable.

EXTENDED (full set, ~40 tools)
    Adds slot editing, markers, export, voice management, appearance,
    dynamics conversion, etc. Recommended for 32 B+ models, or when
    the user explicitly needs advanced features.

Usage
─────
    from tool_registry import get_ollama_tools

    tools = get_ollama_tools()              # core only (default)
    tools = get_ollama_tools(extended=True) # full set
"""

from __future__ import annotations
from typing import Any, Dict, List


# ── Schema helpers ─────────────────────────────────────────────────────── #

def _tool(name: str, desc: str, props: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }

def _s(d: str) -> Dict: return {"type": "string",  "description": d}
def _n(d: str) -> Dict: return {"type": "number",  "description": d}
def _i(d: str) -> Dict: return {"type": "integer", "description": d}
def _b(d: str) -> Dict: return {"type": "boolean", "description": d}


# ══════════════════════════════════════════════════════════════════════════
# CORE TOOLS  (~12)
# Everyday composition and score-reading. Default for all model sizes.
# ══════════════════════════════════════════════════════════════════════════

CORE_TOOLS: List[Dict[str, Any]] = [

    # ── Read score state ───────────────────────────────────────────────── #

    _tool("dump",
        "READ the current score from bach.roll. "
        "Always call this before editing so you know what is already there. "
        "mode='body' → notes/chords (default). "
        "mode='header' → voice count, names, clefs, instruments. "
        "mode='markers' → named markers. "
        "NOT for writing, clearing, or saving — read-only.",
        {
            "mode":            _s("'body' (default) | 'header' | 'pitches' | 'onsets' | 'markers' | 'slotinfo'"),
            "timeout_seconds": _n("Seconds to wait for Max reply (default 15)"),
        },
        []),

    # ── Write score ────────────────────────────────────────────────────── #

    _tool("send_score_to_max",
        "REPLACE the entire score with a new llll. "
        "Wipes everything that was there before. "
        "Format: 'roll [VOICE1] [VOICE2] ...' — one llll bracket per voice.",
        {"score_llll": _s("Full score string, e.g. 'roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ]'")},
        ["score_llll"]),

    _tool("addchord",
        "INSERT one chord into the score without replacing anything. "
        "Use when adding notes to an existing score. "
        "Format: '[onset_ms [pitch_cents dur_ms vel] ...]'",
        {
            "chord_llll": _s("e.g. '[1000 [6000 500 100] [6400 500 90]]'"),
            "voice":      _i("Target voice, 1-indexed (default 1)"),
            "select":     _b("Also select the added chord"),
        },
        ["chord_llll"]),

    _tool("addchords",
        "INSERT chords across multiple voices at once without replacing the score. "
        "Supply one voice-llll per voice; use [] to skip a voice.",
        {
            "chords_llll": _s("e.g. '[[0 [6000 500 100]] [500 [6200 500 100]]] []'"),
            "offset_ms":   _n("Shift all onsets by this many ms"),
        },
        ["chords_llll"]),

    # ── Erase / reset ──────────────────────────────────────────────────── #

    _tool("clear",
        "ERASE the entire score — removes all notes, chords, and markers. "
        "Destructive and immediate. "
        "NOT for saving, NOT for writing to disk — use this only to wipe content. "
        "Does NOT change voice count, clefs, or appearance.",
        {}, []),

    _tool("new_default_score",
        "Full reset: clears content AND resets to 1 treble voice, white background, "
        "black notes, 10-second domain. Use when starting from scratch.",
        {}, []),

    # ── Playback ───────────────────────────────────────────────────────── #

    _tool("play",
        "Start playback. Omit start/end to play from the cursor to the end.",
        {
            "start_ms": _n("Start position in ms"),
            "end_ms":   _n("End position in ms"),
        },
        []),

    # ── Structure ──────────────────────────────────────────────────────── #

    _tool("numvoices",
        "Set the number of voices. Reducing the count DELETES content in removed voices.",
        {"count": _i("Number of voices, must be > 0")},
        ["count"]),

    _tool("clefs",
        "Set clef for each voice. Space-separate for multiple voices. "
        "Symbols: G F FG alto perc auto none G8 G8va F8 F8va. "
        "FG = grand staff (1 voice, 2 staves).",
        {"clefs_list": _s("e.g. 'G'  or  'G F'  or  'FG'")},
        ["clefs_list"]),

    # ── Selection → edit ───────────────────────────────────────────────── #

    _tool("sel",
        "Select items in the score. Must be called before delete/tail/legato/etc. "
        "Examples: 'all'  'notes'  'chord 3'  '1000 3000 [] []'  "
        "'note if cents==6000'  '[] [] [] [] 2' (voice 2).",
        {"arguments": _s("Selection expression — see system prompt for full syntax")},
        ["arguments"]),

    _tool("delete",
        "Delete currently SELECTED items. "
        "Call sel() first to choose what to delete. "
        "NOT for clearing the whole score — use clear() for that.",
        {
            "transferslots": _s("Slots to transfer to neighbour: '' | 'all' | 'auto' | '20 21'"),
            "empty":         _b("Also transfer empty slots"),
        },
        []),

    # ── Fallback ───────────────────────────────────────────────────────── #

    _tool("send_process_message_to_max",
        "Send any raw command string to Max (fire-and-forget). "
        "Use a dedicated tool when one exists; this is the last resort. "
        "Examples: 'stop'  'clefs G F'  'stafflines 5'",
        {"message": _s("Raw command string")},
        ["message"]),
]


# ══════════════════════════════════════════════════════════════════════════
# EXTENDED TOOLS  (added on top of CORE when extended=True)
# Slots, markers, export, appearance, voice management, dynamics, etc.
# Recommended for 32 B+ models.
# ══════════════════════════════════════════════════════════════════════════

EXTENDED_TOOLS: List[Dict[str, Any]] = [

    # ── More score queries ─────────────────────────────────────────────── #

    _tool("subroll",
        "Extract a time/voice slice of the score as llll (read-only).",
        {
            "voices":            _s("Voice list e.g. '[1 2]', '[]'=all"),
            "time_lapse":        _s("Time range e.g. '[1000 3000]', '[]'=all"),
            "selective_options": _s("e.g. '[body]' or '[clefs markers body]'"),
            "onset_only":        _b("Only notes whose onset is inside range"),
            "timeout_seconds":   _n("Max wait (default 15)"),
        },
        []),

    _tool("getnumvoices",    "Return voice count.",                     {"timeout_seconds": _n("Default 15")}, []),
    _tool("getnumchords",    "Return chord count per voice.",           {"timeout_seconds": _n("Default 15")}, []),
    _tool("getnumnotes",     "Return note count per chord per voice.",  {"timeout_seconds": _n("Default 15")}, []),
    _tool("get_length",      "Return total score duration in ms.",      {"timeout_seconds": _n("Default 10")}, []),
    _tool("getcurrentchord", "Return pitches/velocities at cursor.",    {"timeout_seconds": _n("Default 10")}, []),

    _tool("get_marker",
        "Query markers by name. Empty names returns all.",
        {
            "names":           _s("Space-separated names to look up (empty=all)"),
            "name_first":      _b("Output name before position"),
            "timeout_seconds": _n("Default 10"),
        },
        []),

    # ── Voice management ───────────────────────────────────────────────── #

    _tool("numparts",
        "Group voices into ensemble staves. Ints must sum to voice count. "
        "'1 1'=separate staves. '2'=two voices share one grand staff.",
        {"parts": _s("e.g. '1'  '1 1'  '2 2'  '3'")},
        ["parts"]),

    _tool("stafflines",
        "Set staff line count per voice. 5=standard, 1=single-line, 0=invisible.",
        {"value": _s("e.g. '5'  or  '1 5 5'")},
        ["value"]),

    _tool("voicenames",
        "Set voice name labels shown on the score. Space-separate; use [] to skip a voice.",
        {"value": _s("e.g. 'Violin'  or  'Violin Cello'  or  '[RH LH] Bass'")},
        ["value"]),

    _tool("insertvoice",
        "Insert a new empty voice at position (1-indexed).",
        {
            "voice_number": _i("Insertion position"),
            "voice_or_ref": _s("Empty=blank, int=copy props from that voice, or llll content"),
        },
        ["voice_number"]),

    _tool("deletevoice",
        "Delete a voice and all its content (destructive).",
        {"voice_number": _i("1-indexed voice to delete")},
        ["voice_number"]),

    # ── Appearance ─────────────────────────────────────────────────────── #

    _tool("domain",
        "Set the visible time window. "
        "One arg = total duration in ms. Two args = start + end ms.",
        {
            "start_or_duration_ms": _n("Total duration OR range start"),
            "end_ms":               _n("Range end (omit for duration mode)"),
            "pad_pixels":           _n("Ending pad in pixels"),
        },
        ["start_or_duration_ms"]),

    _tool("set_appearance",
        "Set a display attribute by name. "
        "Common names: ruler zoom vzoom showmarkers showdurations showvelocity "
        "showgroups selectioncolor voicespacing showaccidentalspreferences.",
        {
            "attribute": _s("Attribute name e.g. 'zoom'"),
            "value":     _s("Value e.g. '150'  or  '0.8 0. 0.8 1.'"),
        },
        ["attribute", "value"]),

    # ── Selection extras ───────────────────────────────────────────────── #

    _tool("clearselection", "Deselect everything.", {}, []),

    # ── Note editing ───────────────────────────────────────────────────── #

    _tool("tail",
        "Set or modify note end positions for selected notes. "
        "Expressions: '1000'  '= tail + 500'  '= onset + duration * 2'.",
        {"expression": _s("Value or equation")},
        ["expression"]),

    _tool("legato",
        "Make selected notes legato (extend each note to the next onset).",
        {"trim_or_extend": _s("'' (full legato) | 'trim' | 'extend'")},
        []),

    _tool("glissando",
        "Apply a glissando to selected notes.",
        {
            "trim_or_extend": _s("'' | 'trim' | 'extend'"),
            "slope":          _n("Curve slope: -1 to 1 (0 = straight)"),
        },
        []),

    _tool("distribute",
        "Evenly redistribute the onsets of selected items between first and last.",
        {}, []),

    _tool("explodechords",
        "Split polyphonic chords into single-note chords.",
        {"selection": _b("True = selected only")},
        []),

    _tool("merge",
        "Merge nearby chords/notes. Pass -1 to skip a dimension.",
        {
            "threshold_ms":    _n("Time threshold in ms (-1=skip)"),
            "threshold_cents": _n("Pitch threshold in cents (-1=skip)"),
            "selection":       _b("Selected only"),
            "time_policy":     _i("-1=leftmost  0=average  1=rightmost"),
            "pitch_policy":    _i("-1=bottom  0=average  1=top"),
        },
        ["threshold_ms", "threshold_cents"]),

    # ── Markers ────────────────────────────────────────────────────────── #

    _tool("addmarker",
        "Add a named marker at a time position.",
        {
            "position":      _s("Time in ms, 'cursor', or 'end'"),
            "name_or_names": _s("Marker name e.g. 'intro'"),
            "role":          _s("Optional role string"),
            "content":       _s("Optional llll content"),
        },
        ["position", "name_or_names"]),

    _tool("deletemarker",
        "Delete the first marker that matches the given name.",
        {"marker_names": _s("Name to match")},
        ["marker_names"]),

    # ── Slots ──────────────────────────────────────────────────────────── #

    _tool("define_slot",
        "Configure a slot. Defaults: 20=dynamics 22=articulations 23=notehead. "
        "Types: function int float text articulations notehead dynamics color spat etc.",
        {
            "slot_number":    _i("Slot index (1+)"),
            "type":           _s("Slot type"),
            "name":           _s("Display name"),
            "key":            _s("Hotkey character"),
            "range_min":      _n("Y-axis minimum"),
            "range_max":      _n("Y-axis maximum"),
            "representation": _s("Unit label e.g. 'Hz'"),
            "slope":          _n("0=linear  0.5=log-like"),
            "width":          _s("Pixels or 'temporal'"),
            "default":        _s("Default value"),
        },
        ["slot_number"]),

    _tool("copyslot",
        "Copy slot content from one slot to another for selected notes.",
        {
            "slot_from": _s("Source: number, name, or 'active'"),
            "slot_to":   _s("Destination: number, name, or 'active'"),
        },
        ["slot_from", "slot_to"]),

    _tool("eraseslot",
        "Clear slot data for selected notes. slot: number, name, 'active', or 'all'.",
        {"slot": _s("Slot identifier")},
        ["slot"]),

    _tool("erasebreakpoints",
        "Remove all pitch breakpoints (glissandi) from selected notes.",
        {}, []),

    _tool("deleteslotitem",
        "Delete one item from a slot for selected notes.",
        {
            "slot":     _s("Slot number or name"),
            "position": _s("Integer index or wrapped X e.g. '[0.7]'"),
            "thresh":   _n("X-matching tolerance (omit for exact)"),
        },
        ["slot", "position"]),

    # ── Dynamics ───────────────────────────────────────────────────────── #

    _tool("dynamics2velocities",
        "Convert slot 20 dynamics markings to MIDI velocities.",
        {
            "selection":      _b("Selected only"),
            "mapping":        _s("Custom map e.g. '[pp 40] [p 55] [ff 115]'"),
            "maxchars":       _i("Spectrum width (default 4 = pppp–ffff)"),
            "exp":            _n("Curve exponent (1=linear, 0.8=default)"),
            "breakpointmode": _i("0=keep  1=add (default)  2=clear+add"),
        },
        []),

    _tool("velocities2dynamics",
        "Infer dynamics from MIDI velocities and write to slot 20.",
        {
            "selection": _b("Selected only"),
            "mapping":   _s("Custom map e.g. '[pp 20] [p 40] [ff 125]'"),
            "maxchars":  _i("Spectrum width (default 4)"),
            "exp":       _n("Curve exponent (default 0.8)"),
        },
        []),

    # ── Export / save ──────────────────────────────────────────────────── #

    _tool("exportmidi",
        "Export the score as a MIDI file. Leave filename empty to open a dialog.",
        {
            "filename":   _s("e.g. 'score.mid' (empty = dialog)"),
            "voices":     _s("Voices to export e.g. '1 3' (empty = all)"),
            "format":     _i("0=single-track  1=multi-track (default)"),
            "resolution": _i("Ticks per beat (default 960)"),
        },
        []),

    _tool("exportimage",
        "Export the score as a PNG image. view: 'line' (default) 'raw' 'multiline' 'scroll'.",
        {
            "filename":    _s("e.g. '/tmp/score.png' (empty = dialog)"),
            "view":        _s("'line' | 'raw' | 'multiline' | 'scroll'"),
            "mspersystem": _n("System length in ms (multiline/scroll)"),
            "dpi":         _i("DPI (default 72)"),
        },
        []),

    _tool("write",
        "SAVE the score to disk in native llll format. "
        "Leave filename empty to open a save dialog. "
        "NOT for clearing or erasing — use clear() for that.",
        {"filename": _s("e.g. 'score.llll' (empty = dialog)")},
        []),

    _tool("writetxt",
        "Save the score to disk as human-readable text. Leave filename empty for dialog.",
        {
            "filename":    _s("e.g. 'score.txt' (empty = dialog)"),
            "maxdecimals": _i("Float precision (-1 = default 10)"),
        },
        []),
]


# ══════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════

def get_ollama_tools(extended: bool = False) -> List[Dict[str, Any]]:
    """Return tool list for Ollama/Qwen.

    Args:
        extended: If False (default), return only the ~12 core tools.
                  If True, return core + extended (~40 tools total).
                  Use extended=True only with 32 B+ models.

    Returns:
        List of tool dicts in Ollama/OpenAI function-calling schema.
    """
    if extended:
        return CORE_TOOLS + EXTENDED_TOOLS
    return CORE_TOOLS


def get_tool_names(extended: bool = False) -> List[str]:
    """Return just the tool names (useful for logging/debugging)."""
    return [t["function"]["name"] for t in get_ollama_tools(extended=extended)]
