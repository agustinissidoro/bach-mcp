"""The worker: runs the code of a buffer instance, outside the hub's own process.

    python worker.py                         serve: one JSON request per line on stdin, one
                                             JSON answer per line on stdout (runner.py)
    python worker.py --check <file.py> [--params <file.json>]
                                             run the file on a test sound at its declared values
                                             and at the edges of its sliders; one JSON line out

The code is a Python file that defines `process(x, sr, p)`: x the samples, float32 of shape
(frames, channels); sr the sampling rate; p the parameters by name. It returns the samples,
any length and any number of channels, or (samples, sr) to change the rate.

A request:  {"run": {"file": ..., "spec": {params}, "values": {...}, "source": <shm>, "target": <shm>}}
An answer:  {"ok": true, "ms": ..., "frames": ..., "channels": ..., "sr": ..., "warnings": [...]}
            {"ok": false, "error": ..., "line": ...}

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

from bach_mcp.utilities.shmbuffer import NoShmBuffer, ShmBuffer  # noqa: E402

MAX_CHANNELS = 64
TEST_SR = 48000.0
TEST_MS = 2000

_loaded: Dict[str, Tuple[Tuple[int, int], Callable[..., Any]]] = {}


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


def output(result: Any, sr: float) -> Tuple[np.ndarray, float, List[str]]:
    """What process returned as (frames, channels) float32 and its rate, with warnings.
    Raises ProcessError when it is not samples."""
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


def run(request: Dict[str, Any]) -> Dict[str, Any]:
    """One run: the source memory through the file's process, into the target memory."""
    path, source, target = request["file"], request["source"], request["target"]
    fn = load(path)
    try:
        src = ShmBuffer(source)
        x, sr = src.read(), src.sr
        src.close()
    except NoShmBuffer:
        x, sr = np.zeros((0, 1), dtype=np.float32), 0.0
    if not sr:
        try:
            sr = ShmBuffer(target).sr
        except NoShmBuffer:
            sr = TEST_SR
    start = time.perf_counter()
    y, out_sr, warnings = output(call(fn, path, x, sr, parameters(request.get("spec"), request.get("values"))), sr)
    millis = (time.perf_counter() - start) * 1000.0
    if len(x) == 0:
        warnings.insert(0, f"no sound in {source}: the code got 0 frames")
    try:
        dest = ShmBuffer(target)
    except NoShmBuffer:
        dest = ShmBuffer.create(target, y.shape[0], y.shape[1], out_sr)
    dest.write(y, sr=out_sr)
    dest.close()
    return {"ok": True, "ms": round(millis), "frames": int(y.shape[0]), "channels": int(y.shape[1]),
            "sr": out_sr, "warnings": warnings}


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
    for name, decl in (spec or {}).items():
        if isinstance(decl, dict) and decl.get("type") == "slider" and isinstance(decl.get("range"), list) and len(decl["range"]) == 2:
            low, high = decl["range"]
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
            _answer(out, run(request["run"]))
        except BaseException as exc:  # noqa: BLE001 — answer, keep serving
            if isinstance(exc, KeyboardInterrupt):
                raise
            _answer(out, _failure(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
