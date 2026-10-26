"""
docs.py
-------
Adds the instrument docs (`docs/`) to the conversation, with no tool call.

Each user message is searched for the names of instruments and families (the
`aliases` of each file). Every file it names, with its family file, is
appended to that message as a reference block. The block is a pure function of
the conversation: the same messages always give the same blocks, so the
prompt prefix stays identical between requests and the model server can reuse
its cache. A file is added only once, at its first mention.

Matching is by keyword: case-insensitive whole words, the longest alias first,
so "alto flute" finds the alto flute and not also the flute.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
FAMILY_FILE = "_family.md"
_HEADER = "Reference for this request (every pitch is sounding pitch, in midicents):"


@dataclass(frozen=True)
class Doc:
    key: str           # "strings/cello"
    family: str        # "strings"
    aliases: Tuple[str, ...]
    text: str          # what the model sees: the body without front matter or the clefs line

    @property
    def is_family(self) -> bool:
        return self.key.endswith("/_family")


def _parse(path: str) -> Doc:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
    if not m:
        raise ValueError(f"{path}: no front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    aliases = tuple(a.strip().lower() for a in meta.get("aliases", "").strip("[]").split(",") if a.strip())
    # bach.roll has one clef per voice and the translator picks it: the line is for the code only.
    body = re.sub(r"^clefs:.*\n", "", m.group(2), flags=re.M).strip()
    folder = os.path.basename(os.path.dirname(path))
    name = os.path.splitext(os.path.basename(path))[0]
    return Doc(key=f"{folder}/{name}", family=meta.get("family", folder), aliases=aliases, text=body)


class DocLibrary:
    """The docs folder, indexed by alias."""

    def __init__(self, docs_dir: str = DOCS_DIR) -> None:
        paths = sorted(glob.glob(os.path.join(docs_dir, "*", "*.md")))
        self.docs: Dict[str, Doc] = {}
        for path in paths:
            doc = _parse(path)
            self.docs[doc.key] = doc
        by_alias = {a: doc for doc in self.docs.values() for a in doc.aliases}
        # Longest first, so a longer name claims its words before a shorter one can.
        self._aliases = sorted(by_alias.items(), key=lambda item: -len(item[0]))
        self._patterns = [(re.compile(rf"(?<![\w]){re.escape(a)}(?![\w])", re.I), doc) for a, doc in self._aliases]

    def family_doc(self, family: str) -> Optional[Doc]:
        return self.docs.get(f"{family}/_family")

    def find(self, text: str) -> List[Doc]:
        """The docs named in `text`, each instrument preceded by its family, in order of first mention."""
        claimed = [False] * len(text)
        hits: List[Tuple[int, Doc]] = []
        for pattern, doc in self._patterns:
            for m in pattern.finditer(text):
                if any(claimed[m.start():m.end()]):
                    continue
                claimed[m.start():m.end()] = [True] * (m.end() - m.start())
                hits.append((m.start(), doc))
        found: List[Doc] = []
        for _, doc in sorted(hits, key=lambda h: h[0]):
            family = self.family_doc(doc.family)
            for d in (family, doc):
                if d is not None and d not in found:
                    found.append(d)
        return found

    def block(self, docs: Iterable[Doc]) -> str:
        parts = [doc.text for doc in docs]
        return "\n\n".join([_HEADER] + parts) if parts else ""

    def augment(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Return a copy of OpenAI-style `messages` with references appended to the user messages.

        Also returns the keys added to the LAST user message, for logging.
        """
        seen: Set[str] = set()
        out: List[Dict[str, Any]] = []
        last_added: List[str] = []
        for msg in messages:
            if msg.get("role") != "user":
                out.append(msg)
                continue
            text, _, previous = message_text(msg).partition(_HEADER)
            if previous:
                # Already augmented upstream (the terminal agent does it itself): keep it as it is.
                seen.update(d.key for d in self.find(text))
                out.append(msg)
                last_added = []
                continue
            new = [d for d in self.find(text) if d.key not in seen]
            seen.update(d.key for d in new)
            last_added = [d.key for d in new]
            out.append(with_text_appended(msg, self.block(new)) if new else msg)
        return out, last_added

    def augment_text(self, text: str, seen: Set[str]) -> Tuple[str, List[str]]:
        """Append the references for `text` that are not in `seen` (which is updated)."""
        new = [d for d in self.find(text) if d.key not in seen]
        seen.update(d.key for d in new)
        return (f"{text}\n\n{self.block(new)}" if new else text), [d.key for d in new]


def message_text(msg: Dict[str, Any]) -> str:
    content = msg.get("content")
    if isinstance(content, list):
        return "\n".join(str(p.get("text", "")) for p in content if isinstance(p, dict) and p.get("type") == "text")
    return str(content or "")


def with_text_appended(msg: Dict[str, Any], extra: str) -> Dict[str, Any]:
    content = msg.get("content")
    if isinstance(content, list):
        return {**msg, "content": [*content, {"type": "text", "text": extra}]}
    return {**msg, "content": f"{content or ''}\n\n{extra}"}


__all__ = ["DocLibrary", "Doc", "DOCS_DIR"]
