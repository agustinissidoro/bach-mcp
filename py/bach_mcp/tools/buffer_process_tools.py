"""
buffer_process_tools.py
----------------
send_buffer_process: the model writes offline audio processing, as Python: a file that defines
process(x, sr, p), for a buffer instance. The hub runs it (audio_processing/runner.py) on
the samples Max holds in a bachmcp.shmbuffer~ and puts the result in another one; Max never
runs Python, it only sends lines to the hub.

Before a file is kept it is checked here:
  - statically (ast): it parses, opens with a # comment (its description), defines
    process(x, sr, p), imports only from ALLOWED, calls none of FORBIDDEN, and reads only
    parameters it declares;
  - by running it (worker.py --check, a process of its own, with a timeout) on a two-second
    test sound, at its declared values and at both ends of every slider: it must return
    finite samples.
Only a file that passes replaces the previous version (kept in processes/.history). Then:

    <name> load_buffer_process <name>.json                  to Max: the panel's file
    and a first run of the hub's runner, when there is one (the hub registers it: serve_runner)

Two files for the instance, in the playground's processes/ folder:

    <name>.py     the code as the model wrote it
    <name>.json   {"description", "params"}: the panel, in the same spec as an algorithm's
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Protocol, Set, Union

from mcp.server.fastmcp import FastMCP

from ..audio_processing.runner import WORKER
from ..bridge.max import MaxBridge
from ..bridge.protocol import line
from .session import NoTarget, target

BUFFER_PROCESS_TOOLS = ("send_buffer_process",)
BUFFER_PROCESS_TYPES = ("buffer",)

ALLOWED = ("numpy", "scipy", "math", "cmath", "random", "itertools", "functools", "collections", "statistics",
           "dataclasses", "typing", "audio_core", "pedalboard", "sklearn", "librosa", "soundfile")
FORBIDDEN = ("open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars")
CHECK_TIMEOUT_SECONDS = 120.0


# ── The hub's runner, when there is a hub ────────────────────────────── #

class Runner(Protocol):
    def loaded(self, name: str) -> None: ...


_runner: Optional[Runner] = None


def serve_runner(runner: Optional[Runner]) -> None:
    """Who runs a file once it is sent (the hub's ProcessRunner; None: nobody, Max asks for runs)."""
    global _runner
    _runner = runner


# ── Checks ───────────────────────────────────────────────────────────── #

def static_check(code: str, declared: Set[str]) -> Dict[str, Any]:
    """{"ok": True, "description": ...} or {"ok": False, "error": ..., "line": ...}."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"ok": False, "error": f"SyntaxError: {exc.msg}", "line": exc.lineno}
    first = code.lstrip().splitlines()[0] if code.strip() else ""
    if not first.startswith("#") or not first.lstrip("#").strip():
        return {"ok": False, "error": "the file opens with a # comment: what it does, in one line of plain words", "line": 1}
    description = first.lstrip("#").strip()

    fn = next((node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "process"), None)
    if fn is None:
        return {"ok": False, "error": "the file defines no top-level function process(x, sr, p)"}
    args = fn.args.posonlyargs + fn.args.args
    if len(args) < 3:
        return {"ok": False, "error": "process takes three arguments: (x, sr, p)", "line": fn.lineno}
    p = args[2].arg

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.level:
                return {"ok": False, "error": "no relative imports", "line": node.lineno}
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                if name.split(".")[0] not in ALLOWED:
                    return {"ok": False, "line": node.lineno,
                            "error": f"import {name}: only {', '.join(ALLOWED)} may be imported"}
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN:
            return {"ok": False, "error": f"{node.id} is not allowed in a process file", "line": node.lineno}
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr not in ("__name__", "__doc__"):
            return {"ok": False, "error": f"{node.attr} is not allowed in a process file", "line": node.lineno}

    for node in ast.walk(fn):
        key = None
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == p
                and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
            key = node.slice.value
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
              and isinstance(node.func.value, ast.Name) and node.func.value.id == p and node.args
              and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            key = node.args[0].value
        if key is not None and key not in declared:
            return {"ok": False, "line": node.lineno,
                    "error": f"{p}[{key!r}] is read but not declared in params"}
    return {"ok": True, "description": description}


def run_check(path: str, params_path: Optional[str], python: str = sys.executable,
              timeout: float = CHECK_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """worker.py --check on the file. Returns its JSON answer, or {"ok": False, "error": ...}."""
    try:
        done = subprocess.run([python, WORKER, "--check", path] + (["--params", params_path] if params_path else []),
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"it did not finish within {timeout:.0f} s on a two-second test sound"}
    rows = [row for row in done.stdout.splitlines() if row.strip()]
    try:
        return json.loads(rows[-1])
    except (IndexError, ValueError):
        detail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
        return {"ok": False, "error": f"the check failed: {detail[0]}", "fatal": True}


def _params(params: Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
    """The panel's declarations as an object (a model may send them as JSON text). Raises ValueError."""
    if params is None or params == "":
        return {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except ValueError as exc:
            raise ValueError(f"params is not valid JSON ({exc})") from None
    if not isinstance(params, dict) or not all(isinstance(v, dict) and "value" in v for v in params.values()):
        raise ValueError('params must be an object of declarations with a "value": '
                         '{"mix": {"type": "slider", "range": [0, 1], "value": 0.3}}')
    return params


_DOC = """ONLY for a buffer instance: offline processing of a recorded sound, as a Python file.
        Never for notes or a score (write_score), an algorithm that makes notes (send_algorithm),
        or real-time sound in gen~ (send_gen); any other instance refuses it.
        The code runs on the sound in the instance's memory in Max and the result goes back
        there. It is checked, saved and run at once; `params` become a panel in Max, and each
        change there runs it again.

        code: the whole file. It opens with a # comment: what it does, in one line of plain
          words (shown above its panel). It defines `process(x, sr, p)`: x the samples, a numpy
          float32 array of shape (frames, channels); sr the sampling rate; p the parameters by
          name. It returns the samples, any length and number of channels, or (samples, sr).
          It may import numpy, scipy, pedalboard, sklearn, librosa, soundfile, math, random,
          and `audio_core` (ac.ms, ac.mono, ac.stft/istft, ac.normalize, ac.fade, ac.pad, ac.mix).
          Load heavy things (models, impulse responses) at the top of the file: it stays loaded.
        params: the panel, one entry for each parameter the code reads, with its starting value:
          {"mix": {"type": "slider", "range": [0, 1], "value": 0.3},
           "size_ms": {"type": "slider", "range": [10, 2000], "value": 400, "unit": "ms"},
           "freeze": {"type": "toggle", "value": false},
           "mode": {"type": "menu", "options": ["up", "down"], "value": "up"}}
        The result says what the check found. It has been run on a test sound, not listened to.
        Do not call it again to check.
        """


def register_buffer_process_tools(mcp: FastMCP, bridge: MaxBridge, python: str = sys.executable) -> None:
    """Register send_buffer_process on `mcp`. python: what runs the check (the hub's own Python)."""

    def send_buffer_process(code: str, params: Union[Dict[str, Any], str, None] = None) -> str:
        try:
            t = target()
        except NoTarget as exc:
            return f"ERROR: {exc}. Nothing was loaded."
        if t.type not in BUFFER_PROCESS_TYPES:
            return (f"ERROR: {t.name} is a {t.type} instance. send_buffer_process is for a buffer instance "
                    "(offline audio in Python). Nothing was loaded.")
        if not (code or "").strip():
            return "ERROR: code is empty. Send the whole Python file. Nothing was loaded."
        try:
            declared = _params(params)
        except ValueError as exc:
            return f"ERROR: {exc}. Nothing was loaded."

        name = t.name
        text = code.rstrip() + "\n"
        found = static_check(text, set(declared))
        again = "Fix this and call send_buffer_process again with the whole file and its params."
        if not found["ok"]:
            where = f"{name}.py" + (f" line {found['line']}" if found.get("line") else "")
            return f"ERROR in {where}: {found['error']}. Nothing was loaded. {again}"

        folder = t.processes
        history = os.path.join(folder, ".history")
        os.makedirs(history, exist_ok=True)
        draft = os.path.join(history, f".{name}.draft.py")
        draft_params = os.path.join(history, f".{name}.draft.json")
        with open(draft, "w", encoding="utf-8") as f:
            f.write(text)
        with open(draft_params, "w", encoding="utf-8") as f:
            json.dump(declared, f)
        result = run_check(draft, draft_params, python=python)
        os.remove(draft_params)
        if not result.get("ok"):
            os.remove(draft)
            if result.get("fatal"):
                return f"ERROR: {result['error']}. Nothing was loaded."
            where = f"{name}.py" + (f" line {result['line']}" if result.get("line") else "")
            return f"ERROR in {where}: {result['error']}. Nothing was loaded. {again}"

        final = t.process_file
        if os.path.exists(final):
            with open(final, encoding="utf-8") as f:
                previous = f.read()
            if previous != text:
                shutil.copy2(final, os.path.join(history, f"{name}-{time.strftime('%Y%m%d-%H%M%S')}.py"))
        os.replace(draft, final)
        panel = os.path.splitext(final)[0] + ".json"
        with open(panel, "w", encoding="utf-8") as f:
            json.dump({"description": found["description"], "params": declared}, f, indent=1)

        bridge.flush()
        status = (f"and sent to Max ({name})" if bridge.send(line(name, "load_buffer_process", f"{name}.json"))
                  else "but Max could not be reached (is the patch open?)")
        if _runner is not None:
            _runner.loaded(name)
            status += "; it is running now on the sound in Max"
        notes = "".join(f"Note: {w}.\n" for w in result.get("warnings") or [])
        names = ", ".join(declared) or "(none)"
        return (f"OK. Saved as processes/{name}.py {status}.\n"
                f'Shown above its panel: "{found["description"]}"\n'
                f"Parameters (now a panel in Max): {names}\n"
                f"Checked: {result['runs']} runs on a two-second stereo test sound at 48000 Hz (declared values and "
                f"both ends of every slider); the first returned {result['frames']} frames, {result['channels']} "
                f"channels at {result['sr']:g} Hz in {result['ms']} ms.\n{notes}"
                "It has not been listened to.")

    send_buffer_process.__doc__ = _DOC
    mcp.tool()(send_buffer_process)


__all__ = ["register_buffer_process_tools", "static_check", "run_check", "serve_runner", "BUFFER_PROCESS_TOOLS", "BUFFER_PROCESS_TYPES",
           "ALLOWED", "FORBIDDEN"]
