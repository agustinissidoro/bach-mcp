"""The worker: runs the code of a buffer instance, outside the hub's own process.

    python worker.py                         serve: one JSON request per line on stdin, one
                                             JSON answer per line on stdout (runner.py)
    python worker.py --check <file.py> [--params <file.json>]
                                             run the file on a test sound at its declared values
                                             and at the edges of its sliders; one JSON line out

The code is a Python file that defines `process(x, sr, p)`: x the samples, float32 of shape
(frames, channels); sr the sampling rate; p the parameters by name. It returns the samples,
any length and any number of channels, or (samples, sr) to change the rate; or an
audio_compose Canvas or Sound, which also say what they are made of: the database units
and what was done to them. That manifest is written next to the file (<name>.manifest.json).
A file that reads the sound database (audio_corpus) makes sound from nothing: it runs with
an empty source too.

A request:  {"run": {"file": ..., "spec": {params}, "values": {...}, "source": <shm>, "target": <pshm>}}
            The source is a bachmcp.shmbuffer~; the target is always a bachmcp.pshmbuffer~: one run
            writes <target>.1 and leaves exactly one memory. With "variations": N (> 1), the file
            runs N times with p["variation"] = 1 .. N, each into <target>.<n> (the set made, or
            resized to N); answers the first one's frames, the ms of all, and "variations": N
An answer:  {"ok": true, "ms": ..., "frames": ..., "channels": ..., "sr": ..., "warnings": [...]}
            {"ok": false, "error": ..., "line": ...}

A request:  {"load": {"file": ...}}     the file executed (its imports, what it loads at the top), no
            sound processed: a run after it starts at once; answers {"ok": true} or the error
            with its line

A request:  {"describe": {"shm": <shm>, "title": ..., "goal": <the prompt>, "models": {"tagger": <path>, "clap": <path>}}}
An answer:  {"ok": true, "text": <analysis.describe, with the labels and CLAP lines>, "features": {...},
             "similarity": <CLAP, sound to goal, or null>}       (no such memory: "text" says so)

A request:  {"listen": <as run, with "goal" and "models">}   the listen test: the code on the real
            source, kept here and NOT written to the target; answers as run, with "text" (the
            result described), "changes" (source -> result) and "before"/"similarity" (CLAP)
            {"commit": {"target": <pshm>}}               what the last listen made, into <target>.1

A description is kept for each memory and serial: the same sound is analysed once; only its
CLAP similarity to a new goal is computed again (from the kept embedding).

The worker stays alive between runs, so imports and models loaded at the top of a file are loaded
once; a file is executed again only when it changed on disk. Whatever the code prints goes to
stderr: stdout carries the answers only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "library"))                  # import audio_core
sys.path.insert(1, os.path.abspath(os.path.join(HERE, "..", "..")))  # bach_mcp

import numpy as np  # noqa: E402

from bach_mcp.utilities.shmbuffer import NoShmBuffer, PShmBuffer, ShmBuffer  # noqa: E402

MAX_CHANNELS = 64
TEST_SR = 48000.0
TEST_MS = 2000

_loaded: Dict[str, Tuple[Tuple[int, int], Callable[..., Any]]] = {}
_described: Dict[str, Tuple[int, Dict[str, Any]]] = {}  # shm -> (serial, what describe found)
_models: Dict[str, Any] = {}                             # path -> a loaded Tagger or Clap, or the error
DOWNLOAD_HINT = "python py/main.py download {name} --use"


class ProcessError(Exception):
    def __init__(self, message: str, line: Optional[int] = None):
        super().__init__(message)
        self.line = line


def load(path: str) -> Callable[..., Any]:
    """The file's process function, executed again only when the file changed."""
    stat = os.stat(path)
    key = (stat.st_mtime_ns, stat.st_size)
    cached = _loaded.get(path)
    if cached and cached[0] == key:
        return cached[1]
    spec = importlib.util.spec_from_file_location(f"bachmcp_process_{len(_loaded)}_{int(time.time() * 1e6)}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 — the model's code, any error
        raise _error(exc, path, "while loading the file") from None
    fn = getattr(module, "process", None)
    if not callable(fn):
        raise ProcessError("the file defines no function process(x, sr, p)")
    _loaded[path] = (key, fn)
    return fn


def _error(exc: BaseException, path: str, when: str = "") -> ProcessError:
    """The exception as the model can fix it: its type, its message and the line of the file."""
    line = None
    if isinstance(exc, SyntaxError) and exc.filename == path:
        line = exc.lineno
    for frame in traceback.extract_tb(exc.__traceback__):
        if os.path.abspath(frame.filename) == os.path.abspath(path):
            line = frame.lineno
    text = f"{type(exc).__name__}: {exc}" + (f" ({when})" if when else "")
    return ProcessError(text, line)


def parameters(spec: Dict[str, Any], values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """p: every declared parameter at its value, set ones overriding the declared starting value.
    A menu set by index (the panel's way) gets the option itself."""
    p: Dict[str, Any] = {}
    for name, decl in (spec or {}).items():
        decl = decl if isinstance(decl, dict) else {"value": decl}
        value = (values or {}).get(name, decl.get("value"))
        options = decl.get("options")
        if options and isinstance(value, (int, float)) and not isinstance(value, bool) and value not in options:
            index = int(value)
            if 0 <= index < len(options):
                value = options[index]
        if decl.get("type") == "toggle":
            value = bool(value)
        p[name] = value
    return p


_made: Dict[str, Any] = {}   # the manifest of the last result that had one


def uses_corpus(path: str) -> bool:
    """Whether the file reads the sound database: it then makes sound with no source at all."""
    try:
        with open(path, encoding="utf-8") as f:
            return "audio_corpus" in f.read()
    except OSError:
        return False


def output(result: Any, sr: float) -> Tuple[np.ndarray, float, List[str]]:
    """What process returned as (frames, channels) float32 and its rate, with warnings.
    Raises ProcessError when it is not samples."""
    _made.clear()
    if type(result).__name__ in ("Canvas", "Sound") and type(result).__module__ == "audio_compose":
        import audio_compose
        samples = result.render() if isinstance(result, audio_compose.Canvas) else result.samples
        if isinstance(result, audio_compose.Canvas) and not result.placed:
            raise ProcessError("process returned a canvas with nothing placed on it")
        _made.update(audio_compose.manifest_of(result) or {})
        result = (samples, result.sr)
    if isinstance(result, tuple) and len(result) == 2 and np.isscalar(result[1]):
        result, sr = result
        sr = float(sr)
        if not sr > 0:
            raise ProcessError(f"process returned a sampling rate of {sr}")
    if result is None:
        raise ProcessError("process returned None: return the samples")
    try:
        y = np.asarray(result, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ProcessError(f"process returned {type(result).__name__}, not samples ({exc})") from None
    if y.ndim == 1:
        y = y[:, None]
    if y.ndim != 2:
        raise ProcessError(f"process returned an array of shape {y.shape}: return (frames, channels) or (frames,)")
    if y.shape[1] > MAX_CHANNELS and y.shape[0] <= MAX_CHANNELS:
        raise ProcessError(f"process returned shape {y.shape}: channels last, (frames, channels); transpose it")
    if y.shape[1] > MAX_CHANNELS:
        raise ProcessError(f"process returned {y.shape[1]} channels (at most {MAX_CHANNELS})")
    if y.shape[0] == 0:
        raise ProcessError("process returned no frames")
    if not np.all(np.isfinite(y)):
        raise ProcessError("process returned NaN or infinite samples")
    warnings = []
    peak = float(np.max(np.abs(y)))
    if peak == 0:
        warnings.append("the result is silent")
    elif peak > 1.0:
        warnings.append(f"the result peaks at {20 * np.log10(peak):+.1f} dBFS: it clips when played")
    return y, sr, warnings


def call(fn: Callable[..., Any], path: str, x: np.ndarray, sr: float, p: Dict[str, Any]) -> Any:
    try:
        return fn(x, sr, dict(p))
    except ProcessError:
        raise
    except Exception as exc:  # noqa: BLE001 — the model's code, any error
        raise _error(exc, path) from None


def _source(source: str, target: str) -> Tuple[np.ndarray, float]:
    """The samples of the source memory and its rate; no memory: no frames, at the rate of the
    target's first memory (none: the test rate)."""
    try:
        src = ShmBuffer(source)
        x, sr = src.read(), src.sr
        src.close()
    except NoShmBuffer:
        x, sr = np.zeros((0, 1), dtype=np.float32), 0.0
    if not sr:
        try:
            first = ShmBuffer(f"{target}.1")
            sr = first.sr
            first.close()
        except NoShmBuffer:
            pass
    return x, sr or TEST_SR


def _process(request: Dict[str, Any], x: np.ndarray, sr: float,
             variation: Optional[int] = None) -> Tuple[np.ndarray, float, List[str], float]:
    """The file's process on x: (result, its rate, warnings, ms it took)."""
    path = request["file"]
    if "scope" in request:  # the instance's soundfile_sources: which databases, which folders of them
        import audio_corpus
        audio_corpus.set_scope(request["scope"])
    fn = load(path)
    start = time.perf_counter()
    p = parameters(request.get("spec"), request.get("values"))
    if variation is not None:
        p["variation"] = variation
    y, out_sr, warnings = output(call(fn, path, x, sr, p), sr)
    millis = (time.perf_counter() - start) * 1000.0
    if len(x) == 0 and not uses_corpus(path):
        warnings.insert(0, f"no sound in {request['source']}: the code got 0 frames")
    if _made:
        _made["values"] = p
    return y, out_sr, warnings, millis


def _manifest_path(file: str) -> str:
    """<recipes>/<name>.manifest.json for <name>.py, or for its draft in .history."""
    folder, base = os.path.split(os.path.abspath(file))
    if base.startswith(".") and base.endswith(".draft.py"):
        folder, base = os.path.dirname(folder), base[1:-len(".draft.py")] + ".py"
    return os.path.join(folder, os.path.splitext(base)[0] + ".manifest.json")


def _keep_manifest(file: str, manifest: Dict[str, Any]) -> None:
    """What the result now in the target is made of, next to the file (none: the old one goes)."""
    path = _manifest_path(file)
    try:
        if manifest:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=1, default=str)
        elif os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _made_of(manifest: Dict[str, Any]) -> Optional[Dict[str, int]]:
    if not manifest:
        return None
    units = {s.get("unit") for p in manifest.get("placed", []) for s in p.get("sources", []) if s.get("unit") is not None}
    return {"sounds": len(manifest.get("placed", [])), "units": len(units), "files": len(manifest.get("files", []))}


def _ran(y: np.ndarray, sr: float, warnings: List[str], millis: float, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": True, "ms": round(millis), "frames": int(y.shape[0]), "channels": int(y.shape[1]),
            "sr": sr, "warnings": warnings, **({"made_of": _made_of(manifest)} if manifest else {})}


def _write(target: str, results: List[Tuple[np.ndarray, float]]) -> None:
    """Each result into <target>.<n> of the pshmbuffer <target>, which ends with exactly that many
    (one run: <target>.1). Whatever else holds the name (an old plain shmbuffer) is replaced."""
    try:
        poly = PShmBuffer(target)
    except NoShmBuffer:
        poly = PShmBuffer.create(target)
    while len(poly) > len(results):
        poly.pop()
    for n, (y, sr) in enumerate(results, 1):
        if n > len(poly):
            poly.append(y, sr=sr)
        else:
            member = poly[n]
            member.write(y, sr=sr)
            member.close()
    poly.touch()


def run_variations(request: Dict[str, Any]) -> Dict[str, Any]:
    count = int(request["variations"])
    x, sr = _source(request["source"], request["target"])
    results, warnings, total = [], [], 0.0
    for n in range(1, count + 1):
        y, out_sr, said, millis = _process(request, x, sr, variation=n)
        results.append((y, out_sr))
        warnings += [f"variation {n}: {w}" for w in said]
        total += millis
    _write(request["target"], results)
    _keep_manifest(request["file"], dict(_made))
    y, out_sr = results[0]
    return {**_ran(y, out_sr, warnings, total, dict(_made)), "variations": count}


def run(request: Dict[str, Any]) -> Dict[str, Any]:
    """One run: the source memory through the file's process, into <target>.1."""
    if int(request.get("variations") or 1) > 1:
        return run_variations(request)
    x, sr = _source(request["source"], request["target"])
    y, out_sr, warnings, millis = _process(request, x, sr)
    _write(request["target"], [(y, out_sr)])
    _keep_manifest(request["file"], dict(_made))
    return _ran(y, out_sr, warnings, millis, dict(_made))


_pending: Dict[str, Any] = {}  # what the last listen made, until commit writes it


def listen(request: Dict[str, Any]) -> Dict[str, Any]:
    """The listen test: the file's process on the real source, kept here (the target is not
    touched, Max hears nothing), described and compared with the source."""
    from bach_mcp.audio_processing import analysis
    _pending.clear()
    x, sr = _source(request["source"], request["target"])
    if len(x) == 0 and not uses_corpus(request["file"]):
        return {"ok": True, "skipped": f"no sound in {request['source']} yet"}
    y, out_sr, warnings, millis = _process(request, x, sr)
    _pending.update(y=y, sr=out_sr, warnings=warnings, ms=millis, manifest=dict(_made), file=request["file"])
    models, goal = request.get("models") or {}, request.get("goal") or ""
    ran = _ran(y, out_sr, warnings, millis, dict(_made))
    try:  # the code ran: a failure from here on is the analysis's, and never refuses the file
        before = ({"features": {}, "similarity": None} if len(x) == 0 else
                  describe({"shm": request["source"], "title": "SOURCE", "goal": goal, "models": models}))
        after = _with_goal(_analyse(y, out_sr, "RESULT (not yet in Max)", models), goal, models)
        changes = analysis.compare(before["features"], after["features"]) if before["features"] else []
    except Exception as exc:  # noqa: BLE001
        why = f"{type(exc).__name__}: {str(exc).splitlines()[0][:160] if str(exc) else ''}"
        return {**ran, "text": f"RESULT (not yet in Max): not described, the analysis failed ({why}); "
                               "the code itself ran", "features": {}, "similarity": None,
                "before": {"features": {}, "similarity": None}, "changes": []}
    return {**ran, "text": after["text"], "features": after["features"], "similarity": after["similarity"],
            "before": {"features": before["features"], "similarity": before["similarity"]}, "changes": changes}


def commit(request: Dict[str, Any]) -> Dict[str, Any]:
    """Write what the last listen made into <target>.1 (the only memory left): Max gets it."""
    if "y" not in _pending:
        return {"ok": False, "error": "nothing was listened to"}
    _write(request["target"], [(_pending["y"], _pending["sr"])])
    _keep_manifest(_pending["file"], _pending.get("manifest") or {})
    answer = _ran(_pending["y"], _pending["sr"], _pending["warnings"], _pending["ms"], _pending.get("manifest"))
    _pending.clear()
    return answer


def _model(kind: str, path: str, name: str = "") -> Any:
    """The loaded model at path (kept), or a str saying why there is none (name: as [audio] says it)."""
    from bach_mcp.audio_processing import listen as models
    if not models.available(path):
        return f"{name or kind} not downloaded ({DOWNLOAD_HINT.format(name=name or '<name>')})"
    if path not in _models:
        try:
            _models[path] = {"tagger": models.Tagger, "clap": models.Clap, "pitch": models.Pitch}[kind](path)
        except Exception as exc:  # noqa: BLE001 — said in the description, never fatal
            _models[path] = f"could not load ({type(exc).__name__}: {str(exc).splitlines()[0][:160]})"
    return _models[path]


def _analyse(x: np.ndarray, sr: float, title: str, models: Dict[str, str]) -> Dict[str, Any]:
    """analysis.describe with the tagger's line, the features, and CLAP's embedding (or None)."""
    from bach_mcp.audio_processing import analysis
    extra: List[str] = []
    embedding = None
    if models.get("tagger") and len(x):
        tagger = _model("tagger", models["tagger"], models.get("tagger_name", ""))
        if isinstance(tagger, str):
            extra.append(f"is (AudioSet) {tagger}")
        else:
            tags = tagger.tags(x, sr)
            extra.append("is (AudioSet) " + (", ".join(f"{label} {score:.2f}" for label, score in tags) or "nothing it knows"))
    if models.get("clap") and len(x):
        clap = _model("clap", models["clap"], models.get("clap_name", ""))
        if isinstance(clap, str):
            extra.append(f"prompt match (CLAP) {clap}")
        else:
            embedding = clap.embed(x, sr)
    if models.get("pitch") and len(x):
        pitch = _model("pitch", models["pitch"], models.get("pitch_name", ""))
        if isinstance(pitch, str):
            extra.append(f"pitch (PENN) {pitch}")
        else:
            heard = pitch.describe(x, sr)
            where = "none: no step of it has a clear pitch" if heard["pitch"] is None else (
                f"{heard['pitch']:.0f} midicents (the median; C5 = 6000), {heard['pitched']:.2f} of it pitched")
            extra.append(f"pitch (PENN) {where}; periodicity {heard['periodicity']:.2f} (a clean tone 0.58, noise 0)")
    found = analysis.features(x, sr)
    return {"title": title, "text": analysis.describe(x, sr, title, extra, found), "features": found,
            "embedding": embedding}


def _with_goal(found: Dict[str, Any], goal: str, models: Dict[str, str]) -> Dict[str, Any]:
    """The description with CLAP's match to the goal added before the spectrogram."""
    text, similarity = found["text"], None
    goal = (goal or "").strip()
    if goal and found["embedding"] is not None:
        clap = _model("clap", models.get("clap", ""))
        if not isinstance(clap, str):
            similarity = float(found["embedding"] @ clap.embed_text(goal[:300]))
            lines = text.split("\n")
            at = next((k for k, row in enumerate(lines) if row.startswith("spectrogram:")), len(lines))
            lines.insert(at, f"prompt match (CLAP) {similarity:.2f}: how close the sound is to the words of the prompt "
                             "(cosine, -1..1; compare before and after, not with other sounds)")
            text = "\n".join(lines)
    return {"ok": True, "text": text, "features": found["features"], "similarity": similarity}


def describe(request: Dict[str, Any]) -> Dict[str, Any]:
    """The description of the sound in a memory (see the module's docstring)."""
    shm, title = request["shm"], request.get("title", "SOUND")
    models = request.get("models") or {}
    try:
        buf = ShmBuffer(shm)
        serial = buf.serial
        x, sr = buf.read(), buf.sr
        buf.close()
    except NoShmBuffer:
        return {"ok": True, "text": f"{title}: no sound (no bachmcp.shmbuffer~ named {shm})", "features": {}, "similarity": None}
    kept = _described.get(shm)
    if kept is None or kept[0] != serial or kept[1]["title"] != f"{title} ({shm})":
        kept = (serial, _analyse(x, sr, f"{title} ({shm})", models))
        _described[shm] = kept
    return _with_goal(kept[1], request.get("goal") or "", models)


def test_sound(sr: float = TEST_SR, millis: int = TEST_MS) -> np.ndarray:
    """Two channels: a decaying harmonic tone, a noise burst and silence, like a short recording."""
    n = int(sr * millis / 1000)
    t = np.arange(n) / sr
    tone = sum(np.sin(2 * np.pi * 220 * k * t) / k for k in range(1, 6)) * np.exp(-2.5 * t) * 0.4
    burst = np.random.default_rng(7).uniform(-0.3, 0.3, n) * ((t > 1.0) & (t < 1.2))
    left, right = tone + burst, np.roll(tone, int(sr * 0.01)) * 0.8 + burst
    right[-int(sr * 0.2):] = left[-int(sr * 0.2):] = 0.0
    return np.stack([left, right], axis=1).astype(np.float32)


def check(path: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """The file on the test sound at its declared values and at both ends of every slider."""
    fn = load(path)
    x = test_sound()
    runs: List[Tuple[str, Dict[str, Any]]] = [("at its declared values", {})]
    sliders = {name: decl["range"] for name, decl in (spec or {}).items()
               if isinstance(decl, dict) and decl.get("type") == "slider" and isinstance(decl.get("range"), list) and len(decl["range"]) == 2}
    if uses_corpus(path):   # it searches a database at each run: every slider low, then every slider high
        if sliders:
            runs += [("with every slider at its lowest", {n: r[0] for n, r in sliders.items()}),
                     ("with every slider at its highest", {n: r[1] for n, r in sliders.items()})]
    else:
        for name, (low, high) in sliders.items():
            runs += [(f"with {name} = {low}", {name: low}), (f"with {name} = {high}", {name: high})]
    first: Dict[str, Any] = {}
    warnings: List[str] = []
    for when, values in runs:
        start = time.perf_counter()
        try:
            y, sr, said = output(call(fn, path, x.copy(), TEST_SR, parameters(spec, values)), TEST_SR)
        except ProcessError as exc:
            raise ProcessError(f"{exc} — {when}", exc.line) from None
        millis = (time.perf_counter() - start) * 1000.0
        if not first:
            first = {"ms": round(millis), "frames": int(y.shape[0]), "channels": int(y.shape[1]), "sr": sr}
        warnings += [f"{w} ({when})" for w in said if f"{w} ({when})" not in warnings]
    return {"ok": True, "runs": len(runs), "warnings": warnings, **first}


def _answer(out, payload: Dict[str, Any]) -> None:
    out.write(json.dumps(payload) + "\n")
    out.flush()


def load_file(request: Dict[str, Any]) -> Dict[str, Any]:
    """The file executed now, nothing run (see the module's docstring)."""
    load(request["file"])
    return {"ok": True}


def _failure(exc: BaseException) -> Dict[str, Any]:
    if isinstance(exc, ProcessError):
        return {"ok": False, "error": str(exc), "line": exc.line}
    return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main(argv: List[str]) -> int:
    out = os.fdopen(os.dup(1), "w")  # the answers; the code's prints go to stderr
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    if argv[:1] == ["--check"]:
        path = argv[1]
        spec: Dict[str, Any] = {}
        if "--params" in argv:
            with open(argv[argv.index("--params") + 1], encoding="utf-8") as f:
                spec = json.load(f)
        try:
            _answer(out, check(path, spec))
        except BaseException as exc:  # noqa: BLE001
            _answer(out, _failure(exc))
        return 0
    for text in sys.stdin:
        if not text.strip():
            continue
        try:
            request = json.loads(text)
            kind = next(iter(request))
            _answer(out, {"run": run, "load": load_file, "describe": describe, "listen": listen, "commit": commit}[kind](request[kind]))
        except BaseException as exc:  # noqa: BLE001 — answer, keep serving
            if isinstance(exc, KeyboardInterrupt):
                raise
            _answer(out, _failure(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
