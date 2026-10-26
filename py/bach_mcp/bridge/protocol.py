"""
protocol.py
-----------
The one form every message takes, whoever sends it (Max over UDP, the chat
page over HTTP, the terminal): a line of words separated by spaces.

    scales1 prompt "a scale that turns around"
    set_active_instance scales1

A word with spaces, quotes or backslashes in it is written between double
quotes, with \\" and \\\\ inside; a single quote is an ordinary character. A
double quote that is never closed takes the rest of the line. Max sends a text
either as one quoted symbol or as many words: both read the same, because a
command that takes a text (prompt) joins the words it is given.

    words(text)      a line -> its words
    line(*words)     words -> a line (numbers as they are)
    word(text)       one word, quoted if it needs to be
"""

from __future__ import annotations

from typing import List, Union

Word = Union[str, int, float]

_PLAIN = set("\"\\'")


def word(text: str) -> str:
    """One word as it is written in a line: quoted when it holds spaces, quotes or backslashes, or is empty."""
    if text and not any(ch.isspace() or ch in _PLAIN for ch in text):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def line(*words: Word) -> str:
    """A line from words: numbers as they are, every text one word."""
    return " ".join(str(w) if isinstance(w, (int, float)) and not isinstance(w, bool) else word(str(w)) for w in words)


def words(text: str) -> List[str]:
    """The words of a line. Never fails: an unclosed quote takes the rest of the line."""
    out: List[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        if text[i] == '"':
            i += 1
            chars: List[str] = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n and text[i + 1] in '"\\':
                    i += 1
                chars.append(text[i])
                i += 1
            i += 1  # the closing quote
            out.append("".join(chars))
        else:
            start = i
            while i < n and not text[i].isspace():
                i += 1
            out.append(text[start:i])
    return out


__all__ = ["words", "line", "word", "Word"]
