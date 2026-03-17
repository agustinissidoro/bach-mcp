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
        "Valid symbols (case-sensitive): G  G8va (up)  G8 (down)  F  F8va (up)  F8 (down) "
        "Alto Tenor Soprano Mezzo Barytone Percussion None "
        "FG FFG FGG FFGG (multi-staff: ONE voice, multiple staves). "
        "WRONG: perc alto G8vb — use exact symbols as listed.",
        {"value": _s("e.g. 'G'  or  'G F'  or  'FG'  or  'Percussion'  or  'FFGG'")},
        ["value"]),

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
# Layout, markers, save, memory. Recommended for 14 B+ models.
# Kept intentionally small — every tool costs context tokens every request.
# ══════════════════════════════════════════════════════════════════════════

EXTENDED_TOOLS: List[Dict[str, Any]] = [

    # ── Voice count query ──────────────────────────────────────────────── #

    _tool("getnumvoices", "Return current voice count.",
        {"timeout_seconds": _n("Default 10")}, []),

    # ── Layout ─────────────────────────────────────────────────────────── #

    _tool("numparts",
        "Group voices into bracket groups. Ints must sum to numvoices. "
        "'1 1'=separate. '2'=two voices share one grand staff.",
        {"parts": _s("e.g. '1'  '1 1'  '2 2 1'")},
        ["parts"]),

    _tool("stafflines",
        "Set staff line count per voice. 5=standard, 1=single-line, 0=invisible.",
        {"value": _s("e.g. '5'  or  '5 5 1'")},
        ["value"]),

    _tool("voicenames",
        "Set voice name labels. Space-separate; use [] to skip a voice.",
        {"value": _s("e.g. 'Violin Cello'  or  '[RH LH] Bass'")},
        ["value"]),

    _tool("insertvoice",
        "Insert a new empty voice at position (1-indexed).",
        {
            "voice_number": _i("Insertion position"),
            "voice_or_ref": _s("Empty=blank, int=copy props from that voice"),
        },
        ["voice_number"]),

    _tool("deletevoice",
        "Delete a voice and all its content (destructive).",
        {"voice_number": _i("1-indexed voice to delete")},
        ["voice_number"]),

    # ── Markers ────────────────────────────────────────────────────────── #

    _tool("addmarker",
        "Add a named marker at a time position.",
        {
            "position":      _s("Time in ms, 'cursor', or 'end'"),
            "name_or_names": _s("Marker name e.g. 'intro'"),
        },
        ["position", "name_or_names"]),

    _tool("deletemarker",
        "Delete the first marker matching the given name.",
        {"marker_names": _s("Name to match")},
        ["marker_names"]),

    # ── Save ───────────────────────────────────────────────────────────── #

    _tool("write",
        "Save the score to disk in native llll format. "
        "Leave filename empty to open a save dialog.",
        {"filename": _s("e.g. 'score.llll' (empty = dialog)")},
        []),

    _tool("exportmidi",
        "Export the score as a MIDI file. Leave filename empty to open a dialog.",
        {
            "filename":   _s("e.g. 'score.mid' (empty = dialog)"),
            "voices":     _s("Voices to export e.g. '1 3' (empty = all)"),
            "format":     _i("0=single-track  1=multi-track (default)"),
            "resolution": _i("Ticks per beat (default 960)"),
        },
        []),

    # ── Memory ─────────────────────────────────────────────────────────── #

    _tool("project_memory_read",
        "Read persistent project memory across sessions. "
        "Call at session start when working on a named project. "
        "Leave project empty to list all known projects.",
        {"project": _s("Project name, or empty to list all")},
        []),

    _tool("project_memory_write",
        "Save intent, workflow, or notes for a project. "
        "Merges — only supplied fields are updated.",
        {
            "project":  _s("Project name (required)"),
            "intent":   _s("Mood, form, concept"),
            "workflow": _s("Compositional approach"),
            "notes":    _s("Voice roles, decisions, open questions"),
        },
        ["project"]),

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
