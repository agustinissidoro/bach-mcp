"""
tool_registry.py
----------------
Lean tool schemas for Ollama/Qwen.
Claude/MCP uses mcp_app.py unchanged — this file is Qwen-only.

Design principle: descriptions are 1-2 lines max. All syntax knowledge
lives in the system prompt (ollama_bridge.py). Tools just say
what they do and what args they take.
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


# ── Tool definitions ───────────────────────────────────────────────────── #

OLLAMA_TOOLS: List[Dict[str, Any]] = [

    # Score writing
    _tool("send_score_to_max",
        "Send complete llll score to bach.roll (replaces whole score). "
        "Must start with 'roll' then one llll per voice.",
        {"score_llll": _s("e.g. 'roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ]'")},
        ["score_llll"]),

    _tool("addchord",
        "Insert one chord into existing score without replacing it. "
        "Format: [ onset_ms [ pitch_cents dur_ms vel ] ... ]",
        {
            "chord_llll": _s("e.g. '[1000 [6000 500 100]]'"),
            "voice":      _i("Target voice 1-indexed (default 1)"),
            "select":     _b("Also select the added chord"),
        },
        ["chord_llll"]),

    _tool("addchords",
        "Insert chords across multiple voices without replacing score. "
        "One voice-llll per voice, [] to skip a voice.",
        {
            "chords_llll": _s("e.g. '[[0 [6000 500 100]] [500 [6200 500 100]]] []'"),
            "offset_ms":   _n("Shift all onsets by this many ms"),
        },
        ["chords_llll"]),

    # Generic process message
    _tool("send_process_message_to_max",
        "Send any plain command to Max (fire-and-forget). "
        "Use dedicated tools when available; this is the fallback.",
        {"message": _s("Command string e.g. 'play', 'stop', 'clefs G F'")},
        ["message"]),

    # Dump / query
    _tool("dump",
        "Request bach.roll state. Call before editing to read current score. "
        "mode: 'body'=notes, 'header', 'pitches', 'onsets', 'markers', 'slotinfo'.",
        {
            "mode":            _s("'body' (default) 'header' 'pitches' 'onsets' 'markers' 'slotinfo' ''"),
            "selection":       _b("Dump only selected items"),
            "dump_options":    _s("Raw extra options e.g. 'keys clefs body'"),
            "timeout_seconds": _n("Max wait (default 15)"),
        },
        []),

    _tool("subroll",
        "Extract a time/voice slice of score as llll (read-only).",
        {
            "voices":            _s("Voice list e.g. '[1 2]', '[]'=all"),
            "time_lapse":        _s("Time range e.g. '[1000 3000]', '[]'=all"),
            "selective_options": _s("e.g. '[body]' or '[clefs markers body]'"),
            "onset_only":        _b("Only extract notes whose onset is inside range"),
            "timeout_seconds":   _n("Max wait (default 15)"),
        },
        []),

    # Read-only queries
    _tool("getnumvoices",      "Return voice count.",                  {"timeout_seconds": _n("Default 15")}, []),
    _tool("getnumchords",      "Return chord count per voice.",        {"timeout_seconds": _n("Default 15")}, []),
    _tool("getnumnotes",       "Return note count per chord per voice.", {"timeout_seconds": _n("Default 15")}, []),
    _tool("get_length",        "Return total score duration ms.",      {"timeout_seconds": _n("Default 10")}, []),
    _tool("getcurrentchord", "Return pitches/vels at cursor.",       {"timeout_seconds": _n("Default 10")}, []),

    _tool("get_marker",
        "Query markers. Empty names returns all.",
        {
            "names":           _s("Space-separated names to look up (empty=all)"),
            "name_first":      _b("Output name before position"),
            "timeout_seconds": _n("Default 10"),
        },
        []),

    # Playback
    _tool("play",
        "Start playback. Omit start/end to play from cursor to end.",
        {"start_ms": _n("Start ms"), "end_ms": _n("End ms")},
        []),

    # Score structure
    _tool("numvoices",
        "Set voice count. Removing voices deletes their content.",
        {"count": _i("Number of voices >0")},
        ["count"]),

    _tool("clefs",
        "Set clef per voice. "
        "Symbols: G F FG alto perc auto none G8 G8va F8 F8va. "
        "FG=grand staff (1 voice, 2 staves). Space-separate for multiple.",
        {"clefs_list": _s("e.g. 'G', 'G F', 'FG', 'G F F'")},
        ["clefs_list"]),

    _tool("numparts",
        "Group voices into ensemble staves. Ints sum to voice count. "
        "'1 1'=separate staves, '2'=grand staff ensemble.",
        {"parts": _s("e.g. '1', '1 1', '2 2', '3'")},
        ["parts"]),

    _tool("stafflines",
        "Set staff line count per voice. 5=standard, 1=single-line, 0=invisible.",
        {"value": _s("e.g. '5', '1 5 5'")},
        ["value"]),

    _tool("voicenames",
        "Set voice name labels. Space-separated, [] to skip.",
        {"value": _s("e.g. 'Violin', 'Violin Cello', '[RH LH] Bass'")},
        ["value"]),

    _tool("insertvoice",
        "Insert a new voice at a given position (1-indexed).",
        {
            "voice_number": _i("Insertion position"),
            "voice_or_ref": _s("Empty=empty, int=copy props of that voice, or llll content"),
        },
        ["voice_number"]),

    _tool("deletevoice",
        "Delete a voice and all its content (destructive).",
        {"voice_number": _i("1-indexed voice to delete")},
        ["voice_number"]),

    _tool("new_default_score",
        "Reset to a clean score: 1 treble voice, white bg, black notes, 10s domain.",
        {}, []),

    _tool("clear", "Erase entire score (destructive).", {}, []),

    _tool("domain",
        "Set visible time window. One arg=total duration, two args=start+end ms.",
        {
            "start_or_duration_ms": _n("Total duration OR start of range"),
            "end_ms":               _n("End of range (omit for duration mode)"),
            "pad_pixels":           _n("Ending pad pixels"),
        },
        ["start_or_duration_ms"]),

    _tool("set_appearance",
        "Set any display attribute by name. "
        "Common: ruler zoom vzoom showmarkers showdurations showvelocity showgroups "
        "selectioncolor voicespacing showaccidentalspreferences.",
        {
            "attribute": _s("Attribute name e.g. 'ruler', 'zoom'"),
            "value":     _s("Value e.g. '1', '100', '0.8 0. 0.8 1.'"),
        },
        ["attribute", "value"]),

    # Selection
    _tool("sel",
        "Select items. Examples: 'all' 'notes' 'chord 3' 'note if cents==6000' "
        "'1000 3000 [] []'. See system prompt for full syntax.",
        {"arguments": _s("Selection expression")},
        ["arguments"]),

    _tool("clearselection", "Deselect everything.", {}, []),

    # Editing
    _tool("delete",
        "Delete selected items. transferslots: '' 'all' 'auto' '20 21' etc.",
        {
            "transferslots": _s("Slots to transfer to neighbour on delete"),
            "empty":         _b("Also transfer empty slots"),
        },
        []),

    _tool("copyslot",
        "Copy slot content between slots for selected notes.",
        {
            "slot_from": _s("Source: number, name, or 'active'"),
            "slot_to":   _s("Destination: number, name, or 'active'"),
        },
        ["slot_from", "slot_to"]),

    _tool("tail",
        "Set/modify note end positions for selected notes. "
        "Expressions: '1000', '= tail + 500', '= onset + duration * 2'.",
        {"expression": _s("Value or equation")},
        ["expression"]),

    _tool("legato",
        "Make selected notes legato.",
        {"trim_or_extend": _s("'' (full), 'trim', or 'extend'")},
        []),

    _tool("glissando",
        "Apply glissando to selected notes.",
        {
            "trim_or_extend": _s("'' 'trim' 'extend'"),
            "slope":          _n("Curve -1 to 1 (0=straight)"),
        },
        []),

    _tool("distribute",
        "Evenly space onsets of selected items.",
        {}, []),

    _tool("explodechords",
        "Split polyphonic chords into single-note chords.",
        {"selection": _b("True=selected only")},
        []),

    _tool("merge",
        "Merge nearby chords/notes. -1 to skip either dimension.",
        {
            "threshold_ms":    _n("Time threshold ms (-1=skip)"),
            "threshold_cents": _n("Pitch threshold cents (-1=skip)"),
            "selection":       _b("Selected only"),
            "time_policy":     _i("-1=leftmost 0=avg 1=rightmost"),
            "pitch_policy":    _i("-1=bottom 0=avg 1=top"),
        },
        ["threshold_ms", "threshold_cents"]),

    # Markers
    _tool("addmarker",
        "Add a named marker at a time position.",
        {
            "position":      _s("Time ms, 'cursor', or 'end'"),
            "name_or_names": _s("Marker name e.g. 'intro'"),
            "role":          _s("Optional role"),
            "content":       _s("Optional llll content"),
        },
        ["position", "name_or_names"]),

    _tool("deletemarker",
        "Delete first marker matching name.",
        {"marker_names": _s("Name to match")},
        ["marker_names"]),

    # Slots
    _tool("define_slot",
        "Configure a slot. Default: 20=dynamics 22=articulations 23=notehead. "
        "Types: function int float text articulations notehead dynamics color spat etc.",
        {
            "slot_number":    _i("Slot index 1+"),
            "type":           _s("Slot type"),
            "name":           _s("Display name"),
            "key":            _s("Hotkey char"),
            "range_min":      _n("Y min"),
            "range_max":      _n("Y max"),
            "representation": _s("Unit label e.g. 'Hz'"),
            "slope":          _n("0=linear 0.5=log-like"),
            "width":          _s("Pixels or 'temporal'"),
            "default":        _s("Default value"),
        },
        ["slot_number"]),

    _tool("eraseslot",
        "Clear slot data for selected notes. slot: number, name, 'active', or 'all'.",
        {"slot": _s("Slot id")},
        ["slot"]),

    _tool("erasebreakpoints",
        "Remove all pitch breakpoints (glissandi) from selected notes.",
        {}, []),

    _tool("deleteslotitem",
        "Delete one item from a slot for selected notes.",
        {
            "slot":     _s("Slot number or name"),
            "position": _s("Index or wrapped X e.g. '[0.7]'"),
            "thresh":   _n("X-matching tolerance (omit for exact)"),
        },
        ["slot", "position"]),

    # Dynamics
    _tool("dynamics2velocities",
        "Convert slot 20 dynamics to MIDI velocities.",
        {
            "selection":      _b("Selected only"),
            "mapping":        _s("Custom map e.g. '[pp 40] [p 55] [ff 115]'"),
            "maxchars":       _i("Spectrum width (default 4=pppp-ffff)"),
            "exp":            _n("Curve exponent (1=linear, 0.8=default)"),
            "breakpointmode": _i("0=keep bkpts 1=add bkpts (default) 2=clear+add"),
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

    # Export / save
    _tool("exportmidi",
        "Export as MIDI. Empty filename opens dialog.",
        {
            "filename":   _s("e.g. 'score.mid' (empty=dialog)"),
            "voices":     _s("Voices to export e.g. '1 3' (empty=all)"),
            "format":     _i("0=single-track 1=multi-track (default)"),
            "resolution": _i("Ticks/beat (default 960)"),
        },
        []),

    _tool("exportimage",
        "Export as PNG. view: 'line' (default) 'raw' 'multiline' 'scroll'.",
        {
            "filename":    _s("e.g. '/tmp/score.png' (empty=dialog)"),
            "view":        _s("'line' 'raw' 'multiline' 'scroll'"),
            "mspersystem": _n("System length ms (multiline/scroll)"),
            "dpi":         _i("DPI (default 72)"),
        },
        []),

    _tool("write",
        "Save score in native llll format. Empty filename opens dialog.",
        {"filename": _s("e.g. 'score.llll'")},
        []),

    _tool("writetxt",
        "Save score as readable text. Empty filename opens dialog.",
        {
            "filename":    _s("e.g. 'score.txt'"),
            "maxdecimals": _i("Float precision (-1=default 10)"),
        },
        []),
]


def get_ollama_tools() -> List[Dict[str, Any]]:
    """Return all tools in Ollama/OpenAI schema format."""
    return OLLAMA_TOOLS
