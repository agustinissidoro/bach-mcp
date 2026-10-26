"""
algo_tools.py
-------------
send_algorithm: the model writes the algorithm that generates the music, not the
notes. The code is a JavaScript file run in Max by an algorithm instance (v8),
with the algorithmic core library in scope (max/bach-mcp/javascript/
algorithmic_core_library, listed in bachmcp.lib.index.js). Its
declared parameters become a panel (GUI_parameters/) the user plays with; every
change runs the algorithm again.

The file is for one instance (session.py: the one whose prompt is being
answered, else the active one), and carries its name: algorithms/<name>.js in
the playground. The instance's type decides what the file must be: a generator
writes produce(p), a transformer transform(source, p).

Before a file reaches Max it is run here in Node, with the same library: at
its declared values and at the edges of every parameter. Only a file that passes
replaces the previous version (kept in algorithms/.history) and is loaded:

    <name> load_algo <name>.js                       to Max
    <name> algo_loaded <file> <notes> <ms>           from Max, or
    <name> algo_error <message>

A transformer is checked on the music it will work on: its saved source
(algorithms/<name>.source.json) if it has one, else the score now in its roll
(fetched through rolls/<name>.txt, see buffer.py), else a small built-in score.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP

from ..bridge.buffer import RollBuffer
from ..bridge.max import MaxBridge
from ..bridge.protocol import line, words
from ..music.compress import count_notes, describe
from .session import NoTarget, Target, target

ALGO_TOOLS = ("send_algorithm",)

_CHECK_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "algo_check.js")
_CHECK_TIMEOUT_SECONDS = 20.0
_CONFIRM_SECONDS = 6.0  # a transformer first captures its source from the roll
_TRANSFORMER = re.compile(r"\bfunction\s+transform\s*\(")


def check_algorithm(path: str, node: str = "node", timeout: Optional[float] = None,
                    source: Optional[str] = None) -> Dict[str, Any]:
    """Run algo_check.js on a file with Node (a transformer on the `source` score file).
    Returns its JSON answer, or {"ok": False, "error": ...}."""
    timeout = timeout or _CHECK_TIMEOUT_SECONDS
    try:
        done = subprocess.run(
            [node, _CHECK_SCRIPT, path] + (["--source", source] if source else []),
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"Node.js not found ({node}); set [algo] node in bachmcp.toml", "fatal": True}
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        last = [line for line in stderr.splitlines() if line.startswith("run: ")]
        context = last[-1][5:] if last else ""
        return {"ok": False, "error": f"it did not finish within {timeout:.0f} s (an endless loop, or far too many notes)",
                "context": context}
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        detail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
        return {"ok": False, "error": f"the check failed: {detail[0]}", "fatal": True}


def _error_text(name: str, result: Dict[str, Any]) -> str:
    where = f"{name}.js" + (f" line {result['line']}" if result.get("line") else "")
    context = f" ({result['context']})" if result.get("context") and result["context"] != "with the declared values" else ""
    if result.get("fatal"):
        return f"ERROR: {result['error']}. Nothing was loaded."
    return (f"ERROR in {where}: {result['error']}{context}. Nothing was loaded. "
            "Fix this and call send_algorithm again with the whole file.")


def _kind_error(t: Target, code: str) -> Optional[str]:
    """Why this code cannot be this instance's algorithm, or None."""
    transformer = bool(_TRANSFORMER.search(code))
    if t.kind == "writer":
        return f"{t.name} is a writer: it takes notes (write_score), not an algorithm"
    if t.kind == "selector":
        return f"{t.name} is a selector, and selector algorithms are not built yet"
    if t.kind == "generator" and transformer:
        return (f"{t.name} is a generator: it makes music from nothing. "
                "Write function produce(p) { ... }, not transform")
    if t.kind == "transformer" and not transformer:
        return (f"{t.name} is a transformer: it changes the score in its roll. "
                "Write function transform(source, p) { ... }")
    return None


def register_algo_tools(mcp: FastMCP, bridge: MaxBridge, node: str = "node") -> None:
    """Register send_algorithm on `mcp`. node: the Node.js that checks the files ([algo] node)."""

    def _source_for(t: Target) -> Tuple[Optional[str], str]:
        """The score a transformer is checked on: (file, where it comes from)."""
        saved = os.path.join(t.algorithms, f"{t.name}.source.json")
        if os.path.exists(saved):
            return saved, f"its saved source ({t.name}.source.json)"
        score = RollBuffer(bridge, t.name, t.roll_file).fetch(timeout_seconds=3.0)
        if not score or not count_notes(score):
            return None, "a built-in test score: the roll is empty or Max did not hand it over"
        return t.roll_file, "the score in the roll"

    def _wait_for_max(name: str) -> Optional[List[str]]:
        """The instance's answer to a load: [name, "algo_loaded", ...] or [name, "algo_error", ...]."""
        deadline = time.time() + _CONFIRM_SECONDS
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            answer = bridge.receive(timeout_seconds=remaining)
            if answer is None:
                return None
            said = words(answer)
            if len(said) >= 2 and said[0] == name and said[1] in ("algo_loaded", "algo_error"):
                return said

    @mcp.tool()
    def send_algorithm(code: str) -> str:
        """Write the music as an algorithm: a JavaScript file that generates the score
        (the file and the library in scope are described in the skill). It is checked,
        saved and loaded in Max, where its parameters become a panel the user plays
        with; every change runs it again. Sending it again replaces it.

        code: the whole file: const params = {...}; then function produce(p) {...} (a generator)
          or function transform(source, p) {...} (a transformer of the score in its roll).
        The result lists the parameters and the score at the declared values; the file
        has also been run at every slider's minimum and maximum. Do not call it again to check.
        """
        try:
            t = target()
        except NoTarget as exc:
            return f"ERROR: {exc}. Nothing was loaded."
        if not (code or "").strip():
            return "ERROR: code is empty. Send the whole file: const params = {...}; function produce(p) {...}"
        wrong = _kind_error(t, code)
        if wrong:
            return f"ERROR: {wrong}. Nothing was loaded."

        name, folder = t.name, t.algorithms
        os.makedirs(os.path.join(folder, ".history"), exist_ok=True)
        final = t.algorithm_file
        draft = os.path.join(folder, ".history", f".{name}.draft.js")
        with open(draft, "w", encoding="utf-8") as f:
            f.write(code.rstrip() + "\n")

        source, origin = _source_for(t) if t.kind == "transformer" else (None, "")
        result = check_algorithm(draft, node=node, source=source)
        if not result.get("ok"):
            os.remove(draft)
            return _error_text(name, result)
        if os.path.exists(final):
            with open(final, encoding="utf-8") as f:
                unchanged = f.read() == code.rstrip() + "\n"
            if not unchanged:
                stamp = time.strftime("%Y%m%d-%H%M%S")
                shutil.copy2(final, os.path.join(folder, ".history", f"{name}-{stamp}.js"))
        os.replace(draft, final)

        bridge.flush()
        file = os.path.basename(final)
        if not bridge.send(line(name, "load_algo", file)):
            status = "but Max could not be reached (is the patch open?)"
        else:
            answer = _wait_for_max(name)
            if answer is None:
                status = f"and sent to Max, which did not confirm (is the instance \"{name}\" in the patch?)"
            elif answer[1] == "algo_error":
                status = f"but Max reported an error: {' '.join(answer[2:])}"
            else:
                status = f"and loaded in Max ({name})"

        params = "\n".join(f"  {p}" for p in result["describe"]) or "  (none)"
        kind = ""
        if result.get("kind") == "transformer":
            kind = (f"Transformer, checked on {origin} ({result['source']['notes']} notes). In Max it keeps "
                    f"its source in {name}.source.json; every run starts again from it.\n")
        return (
            f"OK. Algorithm saved as algorithms/{file} {status}.\n{kind}"
            f"Parameters (now a panel in Max):\n{params}\n"
            f"Checked in {result['runs']} runs (every slider at its minimum and maximum, every option).\n"
            f"Score at the declared values ({result['notes']} notes, {result['ms']} ms):\n{describe(result['score'])}"
        )


__all__ = ["register_algo_tools", "check_algorithm", "ALGO_TOOLS"]
