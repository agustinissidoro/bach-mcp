"""recompose: a recipe rendered to sound files, in N variations, each with its manifest and
its measures. For trying, outside Max, the code a buffer instance runs (send_buffer_process).

    python py/bach_mcp/audio_processing/recompose.py <file.py> [--n 8] [--seed 0] [--source <sound file>]
        [--db databases/mydatabase.db] [--out playground/renders] [--set name=value ...] [--no-measure]

The file defines `process(x, sr, p)` as any recipe does (a buffer instance's code is a recipe too,
recipes/<name>.py). What the recipe declares is in <file>.json next to it:

    {"description": "...",                         the panel's title line
     "params": {"tail_ms": {...}, ...},            the panel's declarations, as send_buffer_process takes them
     "spread": {"tail_ms": [5000, 10000], ...},    optional: see below
     "prompt": "a struck metal sound ..."}         optional: the words the renders are measured against

x is the sound of --source (the reference a variation, a continuation or a repair starts from),
or no sound at all.

Variation i runs with p["variation"] = i and p["seed"] = --seed: a file that draws its chances
from audio_compose.rng(p) gives a different sound each time, and the same one again for the same
two numbers. "spread" names parameters that should differ between variations: each variation
gets its own value in the range.

--set name=value fixes a parameter for all of them.

What is written, in <out>/<file's name>-<seed>/:

    v01.wav ...    the variations
    v01.json ...   each one's manifest: its parameter values and, when process returned a Canvas or
                   a Sound, every sound placed, with the database units it comes from (file, start,
                   end) and what was done to them
    set.json       the parameters, and for each variation its files and its measures: the
                   database's own descriptors of the result (loudness, brightness, width, streams,
                   complexity, pitch ...) and, with a "prompt", how close it is to those
                   words (CLAP, the database's)
    recipe.py      the file as it was run, and recipe.json its parameters
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "library"))
sys.path.insert(1, os.path.abspath(os.path.join(HERE, "..", "..")))

import numpy as np  # noqa: E402

import audio_corpus  # noqa: E402
from bach_mcp.audio_processing import worker  # noqa: E402

CHECK = os.path.join(REPO, "sources", "bachmcp.database", "build", "bachmcp_database_check")
MEASURES = ("lufs", "peak_db", "centroid_mean", "flatness_mean", "harmonic_share", "onset_density", "width",
            "roughness_mean", "mod_depth", "streams", "spectral_shapes", "sparsity", "complexity", "regularity",
            "states", "periodicity_mean", "pitched", "pitch", "pitch_std")


class RecipeError(Exception):
    pass


def recipe_json(path: str) -> Dict[str, Any]:
    """The .json next to the recipe ({} when there is none)."""
    panel = os.path.splitext(path)[0] + ".json"
    if not os.path.exists(panel):
        return {}
    with open(panel, encoding="utf-8") as f:
        found = json.load(f)
    if not isinstance(found, dict):
        raise RecipeError(f"{os.path.basename(panel)} must hold an object")
    return found


def declared(path: str, fn: Callable[..., Any]) -> Dict[str, Any]:
    """The file's parameters: "params" of the .json next to it (none: no parameters)."""
    return dict(recipe_json(path).get("params") or {})


def values_for(params: Dict[str, Any], spread: Dict[str, Any], fixed: Dict[str, Any], rng: np.random.Generator) -> Dict[str, Any]:
    """What one variation sets: the fixed values, and a value in its range for each spread parameter."""
    out: Dict[str, Any] = {}
    for name, (low, high) in spread.items():
        value = float(rng.uniform(low, high))
        whole = isinstance(params.get(name, {}).get("value"), int) and not isinstance(params.get(name, {}).get("value"), bool)
        out[name] = int(round(value)) if whole else round(value, 4)
    out.update(fixed)
    return out


def render(recipe: str, out: str, n: int = 8, seed: int = 0, fixed: Optional[Dict[str, Any]] = None,
           source: Optional[str] = None, sr: float = 48000, measure_them: bool = True,
           corpus: Optional[audio_corpus.Corpus] = None, say: Callable[[str], None] = print) -> Dict[str, Any]:
    """The file's N variations into a folder of `out`; returns set.json's content (and "folder")."""
    import soundfile
    recipe = os.path.abspath(recipe)
    fn = worker.load(recipe)
    params = declared(recipe, fn)
    about = recipe_json(recipe)
    spread = dict(about.get("spread") or {})
    prompt = str(about.get("prompt") or "")
    unknown = [k for k in list(fixed or {}) + list(spread) if k not in params]
    if unknown:   # before anything is written
        raise RecipeError(f"the file declares no parameter {', '.join(unknown)} (it has: {', '.join(params) or 'none'})")
    if source:
        x, sr = soundfile.read(source, dtype="float32", always_2d=True)
    else:
        x = np.zeros((0, 1), dtype=np.float32)
    name = os.path.splitext(os.path.basename(recipe))[0]
    folder = os.path.join(out, f"{name}-{seed}")
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        if old.startswith("v") and old[1:3].isdigit():
            os.remove(os.path.join(folder, old))
    shutil.copy(recipe, os.path.join(folder, "recipe.py"))
    if os.path.exists(os.path.splitext(recipe)[0] + ".json"):
        shutil.copy(os.path.splitext(recipe)[0] + ".json", os.path.join(folder, "recipe.json"))
    made: List[Dict[str, Any]] = []
    for i in range(1, int(n) + 1):
        entry: Dict[str, Any] = {"name": f"v{i:02d}"}
        started = time.time()
        try:
            values = values_for(params, spread, fixed or {}, np.random.default_rng([int(seed), i, 77]))
            p = worker.parameters(params, values)
            p["seed"], p["variation"] = int(seed), i
            entry["values"] = p
            y, out_sr, warnings = worker.output(worker.call(fn, recipe, x.copy(), float(sr), p), float(sr))
            manifest = dict(worker._made)
            soundfile.write(os.path.join(folder, entry["name"] + ".wav"), y, int(out_sr), subtype="PCM_24")
            with open(os.path.join(folder, entry["name"] + ".json"), "w", encoding="utf-8") as f:
                json.dump({"recipe": name, "prompt": prompt, "source": source, **entry, **manifest}, f, indent=1, default=str)
            of = worker._made_of(manifest) or {}
            entry.update(file=entry["name"] + ".wav", manifest=entry["name"] + ".json", duration_ms=round(len(y) * 1000.0 / out_sr, 2),
                         sounds=of.get("sounds", 0), units=of.get("units", 0), files=of.get("files", 0),
                         seconds=round(time.time() - started, 2), **({"warnings": warnings} if warnings else {}))
            say(f"{entry['name']}: {entry['duration_ms'] / 1000:.1f} s, {entry['sounds']} sounds from {entry['units']} units of "
                f"{entry['files']} files, {entry['seconds']} s" + "".join(f"; {w}" for w in warnings))
        except worker.ProcessError as exc:   # the file's code: the other variations go on
            entry["error"] = str(exc) + (f" (line {exc.line})" if exc.line else "")
            say(f"{entry['name']}: {entry['error']}")
        made.append(entry)
    result = {"recipe": name, "prompt": prompt, "seed": int(seed), "source": source, "params": params, "spread": spread,
              "variations": made}
    if measure_them:
        measures = measure(folder, [m["file"] for m in made if "file" in m], prompt, corpus, say)
        for m in made:
            if m.get("file") in measures:
                m["measures"] = measures[m["file"]]
    with open(os.path.join(folder, "set.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, default=str)
    result["folder"] = folder
    return result


def measure(folder: str, files: List[str], prompt: str = "", corpus: Optional[audio_corpus.Corpus] = None,
            say: Callable[[str], None] = print) -> Dict[str, Dict[str, Any]]:
    """Each file's measures: the database core's descriptors of the whole sound (the same numbers the
    corpus has, so a result can be compared with its material), and its closeness to the prompt."""
    out: Dict[str, Dict[str, Any]] = {name: {} for name in files}
    if not files:
        return out
    if os.path.exists(CHECK):
        with tempfile.TemporaryDirectory(prefix="bachmcp-measure-") as tmp:
            sounds = os.path.join(tmp, "sounds")
            os.makedirs(sounds)
            for name in files:
                os.symlink(os.path.join(os.path.abspath(folder), name), os.path.join(sounds, name))
            db = os.path.join(tmp, "measure.db")
            settings = json.dumps({"levels": ["file"], "tagger": "none", "clap": "none"})
            ran = subprocess.run([CHECK, "db", "build", db, settings, "0", sounds], capture_output=True, text=True)
            if os.path.exists(db):
                con = sqlite3.connect(db)
                con.row_factory = sqlite3.Row
                have = {r[1] for r in con.execute("PRAGMA table_info(units)")}
                keys = [k for k in MEASURES if k in have]
                for r in con.execute(f"SELECT f.name AS name, {', '.join('u.' + k for k in keys)} FROM units u "
                                     "JOIN files f ON f.id = u.file WHERE u.level = 'file'"):
                    out[r["name"]] = {k: (None if r[k] is None else round(float(r[k]), 3)) for k in keys}
                con.close()
            else:
                say(f"not measured: {ran.stdout.strip().splitlines()[-1] if ran.stdout.strip() else ran.stderr.strip()[:200]}")
    else:
        say("not measured: the database core's checker is not built (sources/bachmcp.database/build)")
    if prompt:
        try:
            import soundfile
            corpus = corpus or audio_corpus.corpus()
            words = corpus.text_embedding(prompt)
            for name in files:
                x, sr = soundfile.read(os.path.join(folder, name), dtype="float32", always_2d=True)
                e = corpus.clap().embed(x, sr)
                if e is not None:
                    out[name]["prompt_match"] = round(float(e @ words), 3)
        except Exception as exc:  # noqa: BLE001 — no database or no CLAP: the other measures stay
            say(f"no prompt match: {exc}")
    return out


def table(result: Dict[str, Any], keys=("prompt_match", "lufs", "centroid_mean", "width", "streams", "complexity", "pitched", "pitch")) -> str:
    rows = [["", "s", "sounds", "units", "files", *keys]]
    for m in result["variations"]:
        if "error" in m:
            rows.append([m["name"], "error: " + m["error"]])
            continue
        measures = m.get("measures", {})
        rows.append([m["name"], f"{m['duration_ms'] / 1000:.1f}", str(m["sounds"]), str(m["units"]), str(m["files"]),
                     *["-" if measures.get(k) is None else f"{measures[k]:g}" for k in keys]])
    widths = [max(len(r[i]) for r in rows if len(r) > i) for i in range(len(rows[0]))]
    return "\n".join("  ".join(c.ljust(widths[i]) if i < len(widths) else c for i, c in enumerate(r)) for r in rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render a process file into variations (see the docstring).")
    parser.add_argument("recipe")
    parser.add_argument("--db", default="")
    parser.add_argument("--n", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--source", default=None)
    parser.add_argument("--out", default=os.path.join(REPO, "playground", "renders"))
    parser.add_argument("--set", action="append", default=[], metavar="name=value")
    parser.add_argument("--no-measure", action="store_true")
    args = parser.parse_args(argv)
    if args.db:
        os.environ["BACHMCP_DATABASE"] = os.path.abspath(args.db)   # what audio_corpus.corpus() opens
    fixed: Dict[str, Any] = {}
    for item in args.set:
        key, _, value = item.partition("=")
        try:
            fixed[key] = json.loads(value)
        except ValueError:
            fixed[key] = value
    try:
        result = render(args.recipe, args.out, args.n, args.seed, fixed, args.source, measure_them=not args.no_measure)
    except (RecipeError, worker.ProcessError, audio_corpus.CorpusError) as exc:
        print(f"error: {exc}")
        return 1
    print()
    print(table(result))
    print(f"\n{result['folder']}")
    return 0 if any("file" in m for m in result["variations"]) else 1


__all__ = ["render", "measure", "declared", "values_for", "table", "RecipeError", "MEASURES"]


if __name__ == "__main__":
    sys.exit(main())
