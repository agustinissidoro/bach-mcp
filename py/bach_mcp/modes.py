"""
modes.py
--------
Two modes, chosen by the user with a prefix at the start of a message:

    /score   the model writes the notes, as JSON (write_score)        default
    /algo    the model writes the algorithm that generates them (send_algorithm)

A mode lasts until the other prefix appears. Each mode gets only its own part
of the skill and only its own tools, so the model reads less and nothing that
does not apply.

The skill file marks its parts with lines of their own:
    <!-- algo -->    what follows is for algorithm mode only
    <!-- score -->   for score mode only
    <!-- both -->    for both (the default at the top of the file)
Without a mode (the MCP server's instructions, e.g. for Claude Desktop) the
whole file is used, markers removed.

The mode is a pure function of the conversation (the prefixes in its user
messages), so every request of a conversation carries the same system prompt
and tools, and the model server can keep reusing what it has already read.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

MODES = ("score", "algo")
DEFAULT_MODE = "score"
MODE_TOOLS = {
    "score": ("write_score", "read_score", "clear_score"),
    "algo": ("send_algorithm",),
}
BACH_TOOLS = frozenset(name for names in MODE_TOOLS.values() for name in names)

_PREFIX = re.compile(r"^\s*/(algo|score)\b[ \t]*\n?", re.I)
_MARKER = re.compile(r"^<!--\s*(algo|score|both)\s*-->[ \t]*\n?", re.M)


def split_prefix(text: str) -> Tuple[Optional[str], str]:
    """'/algo a canon' -> ('algo', 'a canon'); text without a prefix -> (None, text)."""
    m = _PREFIX.match(text or "")
    if not m:
        return None, text
    rest = text[m.end():]
    return m.group(1).lower(), rest if rest.strip() else text


def skill_for(text: str, mode: Optional[str] = None) -> str:
    """The parts of a skill file for this mode (None: all of it), markers removed."""
    out: List[str] = []
    current = "both"
    pos = 0
    for m in _MARKER.finditer(text):
        if current == "both" or mode is None or current == mode:
            out.append(text[pos:m.start()])
        current, pos = m.group(1), m.end()
    if current == "both" or mode is None or current == mode:
        out.append(text[pos:])
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip() + "\n"


def base_name(tool_name: str) -> str:
    """A tool's own name, without the server prefix a host may add ("bach__write_score")."""
    return re.split(r"__|[.:/]", tool_name)[-1]


def tools_for(tools: List[Any], mode: str, name_of=lambda t: t["function"]["name"]) -> List[Any]:
    """Keep the tools of this mode, and any tool that is not one of the moded bach tools."""
    keep = []
    for tool in tools:
        name = base_name(name_of(tool))
        if name not in BACH_TOOLS or name in MODE_TOOLS[mode]:
            keep.append(tool)
    return keep


def _text(content: Any) -> str:
    if isinstance(content, list):
        return "\n".join(str(p.get("text", "")) for p in content if isinstance(p, dict) and p.get("type") == "text")
    return str(content or "")


def _strip_prefix(msg: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    content = msg.get("content")
    if isinstance(content, list):
        for i, part in enumerate(content):
            if isinstance(part, dict) and part.get("type") == "text":
                mode, rest = split_prefix(str(part.get("text", "")))
                if mode is None:
                    return None, msg
                parts = list(content)
                parts[i] = {**part, "text": rest}
                return mode, {**msg, "content": parts}
        return None, msg
    mode, rest = split_prefix(str(content or ""))
    return (mode, {**msg, "content": rest}) if mode else (None, msg)


def mode_of(messages: List[Dict[str, Any]]) -> str:
    """The mode of a conversation: the last prefix in its user messages, else the default."""
    mode = DEFAULT_MODE
    for msg in messages:
        if msg.get("role") == "user":
            found, _ = split_prefix(_text(msg.get("content")))
            mode = found or mode
    return mode


def apply_mode(body: Dict[str, Any], full_skill: str, raw_skill: str) -> Tuple[Dict[str, Any], str]:
    """Return a chat request in its mode, and the mode.

    The prefixes are taken out of the user messages; the system message, when it is
    the whole skill (`full_skill`), becomes this mode's part of `raw_skill`; the
    tools are those of the mode.
    """
    messages = body.get("messages")
    if not isinstance(messages, list):
        return body, DEFAULT_MODE
    mode = mode_of(messages)
    out = []
    for msg in messages:
        if msg.get("role") == "user":
            _, msg = _strip_prefix(msg)
        elif msg.get("role") == "system" and _text(msg.get("content")).strip() == full_skill.strip():
            msg = {**msg, "content": skill_for(raw_skill, mode)}
        out.append(msg)
    body = {**body, "messages": out}
    if isinstance(body.get("tools"), list):
        body["tools"] = tools_for(body["tools"], mode)
    return body, mode


__all__ = ["MODES", "DEFAULT_MODE", "MODE_TOOLS", "split_prefix", "skill_for", "tools_for", "mode_of", "apply_mode"]
