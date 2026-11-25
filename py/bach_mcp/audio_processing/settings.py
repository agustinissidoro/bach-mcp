"""
settings.py
-----------
The settings of a buffer instance, set from Max one at a time:

    <name> buffer_settings soundfile_sources database freesound <path> ...
    <name> buffer_settings soundfile_sources_exclude none | <source> ...
    <name> buffer_settings fx all | <audio_treat function> ...
    <name> buffer_settings fx_exclude none | <audio_treat function> ...
    <name> buffer_settings variations <int>

soundfile_sources   where the sound may come from, any of them together:
                      database               the database of bachmcp.toml (audio_corpus.corpus())
                      mine.db                a database by name, in <playground>/databases/
                      /path/to/mine.db       a database by its full path (absolute or ~/...)
                      <database>/<folder>    only the sounds of that database under that folder
                                             (database/drums, mine.db/perc/metal)
                      freesound              the freesound tool
                      any other path         sound files, or folders of them
                    Default: database freesound. none: only x.
soundfile_sources_exclude  taken out of the sources, the same words: a whole database, a folder
                    of one (mine.db/takes/bad), freesound, a path. Default: none.
fx                  the audio_treat functions the code may call. Default: all.
fx_exclude          the ones it may not, taken out of fx. Default: none.
variations          how many versions each run makes (1 by default): the same code with
                    p["variation"] = 1 .. N, each into <target>.<n> of a bachmcp.pshmbuffer~
                    named as the target.

They shape what the model is told (prompt_block), what send_buffer_process's check refuses
(buffer_process_tools.static_check), what the freesound tool refuses, and how the runner runs.
No numpy here: the hub reads it.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

KEYS = ("soundfile_sources", "soundfile_sources_exclude", "fx", "fx_exclude", "variations")
DEFAULT_DB = ""  # the database of bachmcp.toml, found by the worker (audio_corpus.database_path)
MAX_VARIATIONS = 64
_TREAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library", "audio_treat.py")


def treatments() -> Tuple[str, ...]:
    """audio_treat's functions (its __all__), read without importing it."""
    with open(_TREAT, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    return ()


_MAX_VOLUME = re.compile(r"^[^/:]+:(/.*)$")  # "Macintosh HD:/Users/...", as Max writes a path


def local_path(word: str) -> str:
    """A path as Max or a person writes it, as this machine reads it: without a Max volume, ~
    expanded (not made absolute: a relative path stays relative). As tools/playground.local_path."""
    m = _MAX_VOLUME.match(word.strip())
    return os.path.expanduser(m.group(1) if m else word.strip())


Source = Tuple[str, str, str]  # ("freesound", "", "") | ("db", <path or DEFAULT_DB>, <folder or "">) | ("path", <path>, "")


def parse_source(word: str, playground: str = "") -> Source:
    """One word of soundfile_sources(_exclude). Raises ValueError when it names nothing there."""
    word = local_path(word) if _MAX_VOLUME.match(word.strip()) else word
    low = word.lower()
    if low == "freesound":
        return ("freesound", "", "")
    if low == "database" or low.startswith("database/"):
        return ("db", DEFAULT_DB, word[len("database/"):].strip("/") if "/" in word else "")
    at = low.find(".db")
    if at >= 0 and (at + 3 == len(low) or low[at + 3] == "/"):
        db, folder = word[:at + 3], word[at + 4:].strip("/")
        full = os.path.expanduser(db)
        if os.path.isabs(full):          # a full path: that file
            place = full
        elif playground:                 # a name: always in the playground
            place = os.path.join(playground, "databases", db)
        else:
            raise ValueError(f"no database {db}: no playground yet, or give a full path")
        if not os.path.isfile(place):
            raise ValueError(f"no database {db} ({os.path.abspath(place)})")
        return ("db", os.path.abspath(place), folder)
    path = os.path.abspath(os.path.expanduser(word))
    if not os.path.exists(path):
        raise ValueError(f"no such file or folder: {word}")
    return ("path", path, "")


def _db_name(path: str) -> str:
    return "the database of bachmcp.toml" if path == DEFAULT_DB else os.path.basename(path)


@dataclass
class BufferSettings:
    sources: List[Source] = field(default_factory=lambda: [("db", DEFAULT_DB, ""), ("freesound", "", "")])
    exclude: List[Source] = field(default_factory=list)
    fx: Optional[FrozenSet[str]] = None          # None: all
    fx_exclude: FrozenSet[str] = frozenset()
    variations: int = 1

    # ── What the sources come to ── #

    @property
    def freesound(self) -> bool:
        return ("freesound", "", "") in self.sources and ("freesound", "", "") not in self.exclude

    def databases(self) -> Dict[str, Dict[str, List[str]]]:
        """{database path (DEFAULT_DB: bachmcp.toml's): {"in": folders (none: all of it), "out": folders}}."""
        out: Dict[str, Dict[str, List[str]]] = {}
        whole_out = {p for k, p, f in self.exclude if k == "db" and not f}
        for kind, path, folder in self.sources:
            if kind != "db" or path in whole_out:
                continue
            rules = out.setdefault(path, {"in": [], "out": [], "all": False})
            if folder:
                rules["in"].append(folder)
            else:
                rules["all"] = True
        for rules in out.values():
            if rules.pop("all"):
                rules["in"] = []
        for kind, path, folder in self.exclude:
            if kind == "db" and folder and path in out:
                out[path]["out"].append(folder)
        return out

    @property
    def database(self) -> bool:
        return bool(self.databases())

    def paths(self) -> List[str]:
        gone = [p for k, p, _ in self.exclude if k == "path"]
        return [p for k, p, _ in self.sources if k == "path" and p not in gone]

    def excluded_paths(self) -> List[str]:
        return [p for k, p, _ in self.exclude if k == "path"]

    def scope(self) -> Dict[str, Any]:
        """What the worker gives audio_corpus.set_scope."""
        return {"databases": self.databases()}

    # ── Setting ── #

    def set(self, key: str, words: List[str], playground: str = "") -> Optional[str]:
        """Apply one setting. None when done, else why not (nothing changed). playground: where
        a database named without a full path is looked for (<playground>/databases/)."""
        words = [w for w in words if w != ""]
        low = [w.lower() for w in words]
        if key in ("soundfile_sources", "soundfile_sources_exclude"):
            if not words and key == "soundfile_sources":
                return "soundfile_sources needs database, a .db, freesound, paths or none"
            if not words or low == ["none"]:
                if key == "soundfile_sources":
                    self.sources = []
                else:
                    self.exclude = []
                return None
            try:
                parsed = [parse_source(w, playground) for w in words]
            except ValueError as exc:
                return f"{key}: {exc}"
            if key == "soundfile_sources":
                self.sources = parsed
            else:
                self.exclude = parsed
            return None
        if key in ("fx", "fx_exclude"):
            known = treatments()
            if key == "fx" and (not words or low == ["all"]):
                self.fx = None
                return None
            if key == "fx_exclude" and (not words or low == ["none"]):
                self.fx_exclude = frozenset()
                return None
            unknown = [w for w in words if w not in known]
            if unknown:
                return f"{key}: {', '.join(unknown)} not in audio_treat (one of {', '.join(known)})"
            if key == "fx":
                self.fx = frozenset(words)
            else:
                self.fx_exclude = frozenset(words)
            return None
        if key == "variations":
            try:
                n = int(float(words[0]))
            except (IndexError, ValueError):
                return "variations needs a number"
            if not 1 <= n <= MAX_VARIATIONS:
                return f"variations is 1 to {MAX_VARIATIONS}"
            self.variations = n
            return None
        return f"unknown buffer setting {key} (one of {', '.join(KEYS)})"

    def refused_fx(self) -> FrozenSet[str]:
        """The audio_treat functions the code may not call."""
        everything = frozenset(treatments())
        allowed = everything if self.fx is None else self.fx
        return (everything - allowed) | self.fx_exclude

    def is_default(self) -> bool:
        return self == BufferSettings()

    def prompt_block(self) -> str:
        """What the model is told of them, with each prompt ("" when all are at their defaults)."""
        if self.is_default():
            return ""
        rows = []
        sources = []
        for path, rules in self.databases().items():
            how = "audio_corpus.corpus()" if path == DEFAULT_DB else f"audio_corpus.corpus({path!r})"
            text = f"{_db_name(path)}, {how}"
            if rules["in"]:
                text += ", only the sounds under " + ", ".join(rules["in"])
            if rules["out"]:
                text += ", not those under " + ", ".join(rules["out"])
            sources.append(text)
        if self.freesound:
            sources.append("Freesound (the freesound tool)")
        if self.paths():
            text = "these files and folders, read with soundfile or librosa: " + ", ".join(self.paths())
            if self.excluded_paths():
                text += " (but not " + ", ".join(self.excluded_paths()) + ")"
            sources.append(text)
        rows.append("Sound you may use besides x: " + ("; ".join(sources) if sources else "none, only x")
                    + ". Do not use any other.")
        refused = sorted(self.refused_fx())
        if refused:
            rows.append("audio_treat functions you may NOT call: " + ", ".join(refused) + ".")
        if self.variations > 1:
            rows.append(f"Each run makes {self.variations} variations: the same code with p['variation'] = 1 .. "
                        f"{self.variations} (audio_compose.rng(p) follows it). Make the variations differ in a way "
                        "that matters musically: take the chances from rng(p), or read p.get('variation', 1).")
        return "[The settings of this buffer instance, set by the user in Max]\n" + "\n".join(rows)


__all__ = ["BufferSettings", "parse_source", "local_path", "DEFAULT_DB", "KEYS", "MAX_VARIATIONS", "treatments"]
