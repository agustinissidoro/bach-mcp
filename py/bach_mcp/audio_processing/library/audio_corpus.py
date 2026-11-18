"""audio_corpus: the sound database (bachmcp.database's file) read from Python (`import audio_corpus`).

    corpus = audio_corpus.corpus()                # the database of bachmcp.toml [audio] (or Corpus(path))
    hits = corpus.find(text="a metal plate struck", level="event", where={"duration_ms": [200, 2000]}, limit=20)
    s = hits[0].sound(sr)                         # an audio_compose.Sound: the samples, and where they come from

find() speaks the query language of bachmcp.database (query.cpp), with words added:

    text     words: the files that sound most like them (CLAP, the database's own; the first
             `text_files` of them), then their units at `level`. Each unit has `similarity`, its
             file's cosine to the words (-1..1; compare within one search, not between searches).
    like     samples or a Sound: the files that sound most like it (the same CLAP, sound against
             sound), used as `text` is. With both, the two similarities are averaged.
             corpus.timbre(x, sr) gives {"mfcc_mean": ...} of any samples, for `near`: units with
             the timbre of a sound that is not in the database (a layer, a result, the source).
    level    "file", "section", "event", "phase", "grid", or a list of them (default: all)
    where    {key: condition}, all must hold: a number or a text (equal), [min, max] (None: no bound),
             ["a", "b"] (one of these texts), {"min": .., "max": ..}. Keys: any descriptor,
             start_ms, end_ms, duration_ms, level, parent, file, id, "path" (the file's path
             contains it), "name" (the file's name is it).
    near     {"unit": <id or Unit>, "by": ["mfcc_mean", ...]} units like that one (default by
             mfcc_mean: timbre), or {key: number or [numbers]} units near these values. Each key is
             standardized over the candidates. Each unit has `distance`.
    order    "key" (rising), "-key" (falling), "random" (give rng for the same choice each time);
             default: by distance with near, by similarity with text, else as stored
    limit    how many (20)
    per_file at most so many units of one file (None: no bound). With words, the best files have
             many units each: per_file=1 or 2 spreads a search over more files.
    fields   descriptors to bring along ("all": every one); a unit always has id, file, path, name,
             level, parent, start_ms, end_ms, duration_ms, and the keys the query names

A unit's descriptors are read as unit["pitch"], unit["streams"] ...; one the unit does not have
(a texture descriptor of a short unit, the pitch of a noise) is None. A file not analysed with the
database's current core has none of the newer descriptors: `where` on them leaves it out.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if PY not in sys.path:
    sys.path.insert(1, PY)   # bach_mcp (listen.py's CLAP, the config's model folders)

LEVELS = ("file", "section", "event", "phase", "grid")
BASE = ("id", "file", "level", "parent", "start_ms", "end_ms", "duration_ms")
CANDIDATES = 200000   # the most units a near or random search looks at


class CorpusError(Exception):
    pass


class Unit:
    """One unit of the database: a span of a file, with the descriptors asked for."""

    def __init__(self, corpus: "Corpus", row: Dict[str, Any]) -> None:
        self.corpus = corpus
        self.id, self.file, self.level, self.parent = row["id"], row["file"], row["level"], row["parent"]
        self.path, self.name = row["path"], row["name"]
        self.start_ms, self.end_ms = float(row["start_ms"]), float(row["end_ms"])
        self.duration_ms = self.end_ms - self.start_ms
        self.values = {k: v for k, v in row.items() if k not in ("path", "name")}
        self.similarity: Optional[float] = None
        self.distance: Optional[float] = None

    def __getitem__(self, key: str) -> Any:
        if key not in self.values:
            self.values.update(self.corpus._row(self.id, [key]))
        return self.values.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        value = self[key] if key in self.corpus.columns else None
        return default if value is None else value

    def source(self) -> Dict[str, Any]:
        """Where this sound comes from, for a manifest."""
        return {"unit": self.id, "level": self.level, "path": self.path, "start_ms": self.start_ms, "end_ms": self.end_ms}

    def samples(self, sr: float = 48000, before_ms: float = 0.0, after_ms: float = 0.0) -> np.ndarray:
        """The unit's samples at sr, (frames, channels), with so much of the file before and after it."""
        return read_span(self.path, self.start_ms - before_ms, self.end_ms + after_ms, sr)

    def sound(self, sr: float = 48000, before_ms: float = 0.0, after_ms: float = 0.0):
        import audio_compose
        source = self.source()
        if before_ms or after_ms:
            source["start_ms"], source["end_ms"] = max(0.0, self.start_ms - before_ms), self.end_ms + after_ms
        return audio_compose.Sound(self.samples(sr, before_ms, after_ms), sr, [source])

    def children(self, level: Optional[str] = None, fields: Union[str, Sequence[str], None] = None) -> List["Unit"]:
        where: Dict[str, Any] = {"parent": self.id}
        return self.corpus.find(level=level, where=where, order="start_ms", limit=100000, fields=fields)

    def __repr__(self) -> str:
        extra = "" if self.similarity is None else f" similarity {self.similarity:.3f}"
        extra += "" if self.distance is None else f" distance {self.distance:.3f}"
        return f"<{self.level} {self.id} {self.name} {self.start_ms:.0f}-{self.end_ms:.0f} ms{extra}>"


def read_span(path: str, start_ms: float, end_ms: float, sr: float) -> np.ndarray:
    """A span of a sound file at sr, float32 (frames, channels)."""
    import soundfile
    start_ms = max(0.0, float(start_ms))
    try:
        with soundfile.SoundFile(path) as f:
            rate = f.samplerate
            a, b = int(round(start_ms * rate / 1000.0)), min(f.frames, int(round(end_ms * rate / 1000.0)))
            f.seek(min(a, f.frames))
            x = f.read(max(0, b - a), dtype="float32", always_2d=True)
    except Exception:  # noqa: BLE001 — a format libsndfile does not read (m4a): librosa's readers
        import librosa
        y, rate = librosa.load(path, sr=None, mono=False, offset=start_ms / 1000.0, duration=max(0.0, end_ms - start_ms) / 1000.0)
        x = np.atleast_2d(y).T.astype(np.float32)
    if int(rate) != int(sr) and len(x):
        import soxr
        x = soxr.resample(x, rate, sr, quality="HQ").astype(np.float32)
    return np.ascontiguousarray(x, dtype=np.float32)


class Corpus:
    def __init__(self, path: str) -> None:
        if not os.path.isfile(path):
            raise CorpusError(f"no database at {path}")
        self.path = os.path.abspath(path)
        self.db = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.columns = {r["name"]: (r["type"] or "").upper() for r in self.db.execute("PRAGMA table_info(units)")}
        meta = {r["key"]: r["value"] for r in self.db.execute("SELECT key, value FROM meta")}
        self.settings: Dict[str, Any] = json.loads(meta.get("settings", "{}"))
        self.dtype = "<f2" if meta.get("vectors") == "float16" else "<f4"
        self._clap = None          # the loaded CLAP (listen.Clap)
        self._embeddings = None    # (file ids, unit embeddings of the file units)
        self._texts: Dict[str, np.ndarray] = {}

    # ── Reading ── #

    def _value(self, key: str, value: Any) -> Any:
        if isinstance(value, bytes):
            return np.frombuffer(value, dtype=self.dtype).astype(np.float32)
        if key in ("tags",) and isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return value
        return value

    def _row(self, unit_id: int, keys: Iterable[str]) -> Dict[str, Any]:
        keys = [k for k in keys if k in self.columns]
        if not keys:
            return {}
        row = self.db.execute(f"SELECT {', '.join(_q(k) for k in keys)} FROM units WHERE id = ?", (unit_id,)).fetchone()
        return {} if row is None else {k: self._value(k, row[k]) for k in keys}

    def unit(self, unit_id: int, fields: Union[str, Sequence[str], None] = None) -> Unit:
        found = self._units([int(unit_id)], self._fields(fields, []))
        if not found:
            raise CorpusError(f"no unit {unit_id}")
        return found[0]

    def _fields(self, fields: Union[str, Sequence[str], None], named: Iterable[str]) -> List[str]:
        if fields == "all":
            return list(self.columns)
        wanted = list(BASE) + [k for k in list(fields or []) + list(named) if k not in BASE]
        unknown = [k for k in wanted if k not in self.columns]
        if unknown:
            raise CorpusError(f"no descriptor {', '.join(unknown)} in this database")
        return list(dict.fromkeys(wanted))

    def _units(self, ids: Sequence[int], fields: List[str]) -> List[Unit]:
        out: Dict[int, Unit] = {}
        for at in range(0, len(ids), 500):
            chunk = list(ids[at:at + 500])
            sql = (f"SELECT {', '.join('u.' + _q(k) for k in fields)}, f.path AS path, f.name AS name FROM units u "
                   f"JOIN files f ON f.id = u.file WHERE u.id IN ({', '.join('?' * len(chunk))})")
            for r in self.db.execute(sql, chunk):
                row = {k: self._value(k, r[k]) for k in fields}
                row["path"], row["name"] = r["path"], r["name"]
                out[r["id"]] = Unit(self, row)
        return [out[i] for i in ids if i in out]

    # ── Searching ── #

    def _where(self, level, where: Optional[Dict[str, Any]]) -> tuple:
        clauses, args = ["f.state = 'ok'"], []
        rules = (_scope or {}).get(self.path)
        if rules:  # the instance's soundfile_sources: only these folders, never those
            if rules["in"]:
                clauses.append("(" + " OR ".join("f.path LIKE ?" for _ in rules["in"]) + ")")
                args += [_folder_like(f) for f in rules["in"]]
            for folder in rules["out"]:
                clauses.append("f.path NOT LIKE ?")
                args.append(_folder_like(folder))
        if level:
            levels = [level] if isinstance(level, str) else list(level)
            bad = [l for l in levels if l not in LEVELS]
            if bad:
                raise CorpusError(f"no level {', '.join(bad)} ({' '.join(LEVELS)})")
            clauses.append(f"u.level IN ({', '.join('?' * len(levels))})")
            args += levels
        for key, cond in (where or {}).items():
            if key == "path":
                clauses.append("f.path LIKE ?")
                args.append(f"%{cond}%")
                continue
            if key == "name":
                clauses.append("f.name = ?")
                args.append(cond)
                continue
            if key not in self.columns:
                raise CorpusError(f"where: no descriptor {key} in this database")
            col = "u." + _q(key)
            if isinstance(cond, dict):
                cond = [cond.get("min"), cond.get("max")]
            if isinstance(cond, (list, tuple)):
                if cond and all(isinstance(c, str) for c in cond):
                    clauses.append(f"{col} IN ({', '.join('?' * len(cond))})")
                    args += list(cond)
                elif len(cond) == 2:
                    lo, hi = cond
                    if lo is not None:
                        clauses.append(f"{col} >= ?")
                        args.append(lo)
                    if hi is not None:
                        clauses.append(f"{col} <= ?")
                        args.append(hi)
                    if lo is None and hi is None:
                        clauses.append(f"{col} IS NOT NULL")
                else:
                    raise CorpusError(f"where {key}: a range is [min, max]")
            else:
                clauses.append(f"{col} = ?")
                args.append(cond)
        return " AND ".join(clauses), args

    def clap(self):
        """The database's CLAP (listen.Clap), which gave its files their embeddings."""
        if self._clap is None:
            name = str(self.settings.get("clap", "none"))
            if name in ("", "none"):
                raise CorpusError("this database has no CLAP: no search by words (analysis clap <name> in Max)")
            from bach_mcp.audio_processing import listen
            from bach_mcp.config import AudioConfig
            folder = AudioConfig().model_path(name)
            if not listen.available(folder):
                raise CorpusError(f"the database's CLAP, {name}, is not downloaded (python py/main.py download {name})")
            self._clap = listen.Clap(folder)
        return self._clap

    def text_embedding(self, text: str) -> np.ndarray:
        if text not in self._texts:
            self._texts[text] = np.asarray(self.clap().embed_text(text), dtype=np.float32)
        return self._texts[text]

    def sound_embedding(self, sound, sr: Optional[float] = None) -> np.ndarray:
        samples, rate = (sound.samples, sound.sr) if hasattr(sound, "samples") else (np.asarray(sound, dtype=np.float32), sr)
        if rate is None:
            raise CorpusError("like: samples need their rate: find(like=samples, sr=sr), or give a Sound")
        e = self.clap().embed(samples, rate)
        if e is None:
            raise CorpusError("like: the sound is empty")
        return np.asarray(e, dtype=np.float32)

    def timbre(self, x, sr: float) -> Dict[str, np.ndarray]:
        """{"mfcc_mean": ...} of any samples, computed as the database computes it (librosa's MFCC at the
        database's settings): for find(near=corpus.timbre(x, sr))."""
        import librosa
        s = self.settings
        rate = float(s.get("rate") or sr)
        a = np.asarray(x.samples if hasattr(x, "samples") else x, dtype=np.float32)
        mono = a.mean(axis=1) if a.ndim == 2 else a
        if int(sr) != int(rate) and len(mono):
            mono = librosa.resample(mono, orig_sr=float(sr), target_sr=rate)
        if len(mono) < 64:
            raise CorpusError("timbre: the sound is too short")
        m = librosa.feature.mfcc(y=mono, sr=rate, n_mfcc=int(s.get("n_mfcc", 20)), n_fft=int(s.get("n_fft", 2048)),
                                 hop_length=int(s.get("hop", 512)), n_mels=int(s.get("n_mels", 128)))
        if not hasattr(self, "_mfcc_size"):   # as many coefficients as the database keeps
            row = self.db.execute("SELECT mfcc_mean FROM units WHERE mfcc_mean IS NOT NULL LIMIT 1").fetchone()
            self._mfcc_size = len(np.frombuffer(row[0], dtype=self.dtype)) if row else m.shape[0]
        return {"mfcc_mean": m.mean(axis=1)[:self._mfcc_size].astype(np.float32)}

    def files_like(self, text, limit: int = 200) -> List[tuple]:
        """[(file id, similarity), ...]: the files that sound most like the words (or like an embedding),
        best first. Files whose embedding is another CLAP's (a database being reanalysed with a new one)
        are left out."""
        e = self.text_embedding(text) if isinstance(text, str) else np.asarray(text, dtype=np.float32)
        if self._embeddings is None or self._embeddings[1].shape[1] != len(e):
            ids, rows = [], []
            for r in self.db.execute("SELECT u.file, u.clap FROM units u JOIN files f ON f.id = u.file "
                                     "WHERE u.level = 'file' AND u.clap IS NOT NULL AND f.state = 'ok'"):
                v = np.frombuffer(r["clap"], dtype=self.dtype)
                if len(v) == len(e):
                    ids.append(r["file"])
                    rows.append(v)
            if not rows:
                raise CorpusError("no file of this database has an embedding of its CLAP yet (reanalyse it)")
            self._embeddings = (np.array(ids), np.stack(rows).astype(np.float32))
        ids, matrix = self._embeddings
        sims = matrix @ e
        best = np.argsort(-sims)[:limit]
        return [(int(ids[i]), float(sims[i])) for i in best]

    def find(self, text: Optional[str] = None, level=None, where: Optional[Dict[str, Any]] = None,
             near: Optional[Dict[str, Any]] = None, order: Optional[str] = None, limit: int = 20,
             fields: Union[str, Sequence[str], None] = None, text_files: int = 200, rng=None,
             per_file: Optional[int] = None, like=None, sr: Optional[float] = None) -> List[Unit]:
        clause, args = self._where(level, where)

        def spread(order: Sequence[int], file_of) -> List[int]:
            """The first `limit` of `order`, at most per_file of each file."""
            if not per_file:
                return list(order[:limit])
            kept, count = [], {}
            for i in order:
                f = file_of(i)
                if count.get(f, 0) < per_file:
                    count[f] = count.get(f, 0) + 1
                    kept.append(i)
                    if len(kept) >= limit:
                        break
            return kept

        similarity: Dict[int, float] = {}
        if like is not None:
            e = self.sound_embedding(like, sr)
            if text:
                e = e + self.text_embedding(text)
                e = e / max(float(np.linalg.norm(e)), 1e-12)
            text = e   # an embedding from here on, used as the words' is
        if text is not None and (not isinstance(text, str) or text):
            similarity = dict(self.files_like(text, text_files))
            if not similarity:
                return []
            clause += f" AND u.file IN ({', '.join(str(i) for i in similarity)})"
        named = [k for k in (where or {}) if k in self.columns]
        base = f"FROM units u JOIN files f ON f.id = u.file WHERE {clause}"

        if near:
            by, target = self._near_target(near)
            named += by
            rows = self.db.execute(f"SELECT u.id, u.file, {', '.join('u.' + _q(k) for k in by)} {base} "
                                   f"AND {' AND '.join('u.' + _q(k) + ' IS NOT NULL' for k in by)} LIMIT {CANDIDATES}", args).fetchall()
            skip = near.get("unit")
            skip = skip.id if isinstance(skip, Unit) else skip
            rows = [r for r in rows if r["id"] != skip]
            if not rows:
                return []
            total = np.zeros(len(rows))
            for k in by:
                m = np.stack([np.atleast_1d(self._value(k, r[k])).astype(np.float64) for r in rows])
                z = (m - np.atleast_1d(target[k])[None, :]) / np.maximum(m.std(axis=0), 1e-9)[None, :]
                total += (z ** 2).mean(axis=1)
            dist = np.sqrt(total / len(by))
            pick = spread(np.argsort(dist), lambda i: rows[i]["file"])
            units = self._units([rows[i]["id"] for i in pick], self._fields(fields, named))
            for u, i in zip(units, pick):
                u.distance = float(dist[i])
        elif order == "random" or (similarity and not order and level not in (None, "file")):
            ids = [(r[0], r[1]) for r in self.db.execute(f"SELECT u.id, u.file {base} LIMIT {CANDIDATES}", args)]
            if order == "random":
                rng = np.random.default_rng() if rng is None else rng
                pick = spread(rng.permutation(len(ids)), lambda i: ids[i][1])
            else:   # by the file's similarity to the words, then as stored
                pick = spread(sorted(range(len(ids)), key=lambda i: -similarity[ids[i][1]]), lambda i: ids[i][1])
            units = self._units([ids[i][0] for i in pick], self._fields(fields, named))
        else:
            sort = ""
            if order:
                key = order.lstrip("-")
                if key not in self.columns:
                    raise CorpusError(f"order: no descriptor {key}")
                named.append(key)
                sort = f" ORDER BY u.{_q(key)} IS NULL, u.{_q(key)} {'DESC' if order.startswith('-') else 'ASC'}"
            cap = CANDIDATES if similarity else int(limit) * (50 if per_file else 1)
            found = [(r[0], r[1]) for r in self.db.execute(f"SELECT u.id, u.file {base}{sort} LIMIT {cap}", args)]
            if similarity and not order:
                found.sort(key=lambda r: -similarity[r[1]])
            pick = spread(range(len(found)), lambda i: found[i][1])
            units = self._units([found[i][0] for i in pick], self._fields(fields, named))
        for u in units:
            if u.file in similarity:
                u.similarity = similarity[u.file]
        return units

    def _near_target(self, near: Dict[str, Any]) -> tuple:
        if "unit" in near:
            by = list(near.get("by") or ["mfcc_mean"])
            by = [by] if isinstance(by, str) else by
            ref = near["unit"]
            ref = ref if isinstance(ref, Unit) else self.unit(int(ref))
            target = {k: ref[k] for k in by}
            missing = [k for k in by if target[k] is None]
            if missing:
                raise CorpusError(f"near: unit {ref.id} has no {', '.join(missing)}")
        else:
            by = list(near)
            target = {k: np.asarray(v, dtype=np.float64) for k, v in near.items()}
        unknown = [k for k in by if k not in self.columns]
        if unknown:
            raise CorpusError(f"near: no descriptor {', '.join(unknown)} in this database")
        return by, target

    def close(self) -> None:
        self.db.close()


_open: Dict[str, Corpus] = {}
_scope: Optional[Dict[str, Dict[str, List[str]]]] = None  # None: every database, all of it


def set_scope(scope: Optional[Dict[str, Any]]) -> None:
    """The buffer instance's soundfile_sources (the worker sets it before each run):
    {"databases": {path ("": bachmcp.toml's): {"in": folders (none: all), "out": folders}}}."""
    global _scope
    if scope is None:
        _scope = None
        return
    out: Dict[str, Dict[str, List[str]]] = {}
    for path, rules in (scope.get("databases") or {}).items():
        if not path:
            try:
                path = database_path()
            except CorpusError:
                continue
        out[os.path.abspath(path)] = {"in": list(rules.get("in") or []), "out": list(rules.get("out") or [])}
    _scope = out


def _folder_like(folder: str) -> str:
    return (folder.rstrip("/") + "/%") if os.path.isabs(folder) else f"%{folder.strip('/')}/%"


def database_path() -> str:
    """The database a process file reads: BACHMCP_DATABASE, else bachmcp.toml [audio] database, else
    the one .db file of the package's databases/ folder."""
    named = os.environ.get("BACHMCP_DATABASE", "")
    if not named:
        try:
            from bach_mcp.config import load_config
            named = getattr(load_config().audio, "database", "") or ""
        except Exception:  # noqa: BLE001 — no config: the folder
            named = ""
    repo = os.path.abspath(os.path.join(PY, ".."))
    if named:
        return named if os.path.isabs(named) else os.path.join(repo, named)
    folder = os.path.join(repo, "databases")
    found = sorted(f for f in os.listdir(folder) if f.endswith(".db")) if os.path.isdir(folder) else []
    if len(found) != 1:
        raise CorpusError(("no database in databases/" if not found else f"several databases in databases/ ({', '.join(found)})")
                          + ': name one in bachmcp.toml, [audio] database = "databases/<name>.db"')
    return os.path.join(folder, found[0])


def corpus(path: Optional[str] = None) -> Corpus:
    """The sound database, opened once (its CLAP too): the one of bachmcp.toml, or the file at `path`."""
    if _scope is not None:
        allowed = sorted(_scope)
        if not allowed:
            raise CorpusError("no database is among this instance's soundfile_sources")
        if path is None:
            try:
                default = os.path.abspath(database_path())
            except CorpusError:
                default = ""
            path = default if default in _scope else allowed[0] if len(allowed) == 1 else None
            if path is None:
                raise CorpusError("this instance has several databases: name one, corpus(path), of "
                                  + ", ".join(allowed))
        elif os.path.abspath(path) not in _scope:
            raise CorpusError(f"{path} is not among this instance's soundfile_sources ({', '.join(allowed)})")
    path = os.path.abspath(path or database_path())
    if path not in _open:
        _open[path] = Corpus(path)
    return _open[path]


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


__all__ = ["corpus", "Corpus", "Unit", "CorpusError", "read_span", "database_path", "set_scope", "LEVELS"]
