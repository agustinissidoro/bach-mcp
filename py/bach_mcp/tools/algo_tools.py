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
writes produce(p), a transformer transform(source, p), a selector select(source, p).

Before a file reaches Max it is run here in Node, with the same library: at
its declared values and at the edges of every parameter. Only a file that passes
replaces the previous version (kept in algorithms/.history) and is loaded,
without waiting for an answer:

    <name> load_algo <name>.js                       to Max

A transformer or a selector is checked on the music it will work on: the score now in the
roll, read like read_score (server write_buffer -> buffer.json, see buffer.py),
else, when the roll is empty or Max does not answer, a small built-in score.
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

from ..bridge.buffer import ServerBuffer
from ..bridge.max import MaxBridge
from ..bridge.protocol import line, words
from ..music.compress import count_notes, describe
from .session import NoTarget, Target, target

ALGO_TOOLS = ("send_algorithm",)

_CHECK_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "algo_check.js")
_CHECK_TIMEOUT_SECONDS = 20.0
_TRANSFORMER = re.compile(r"\bfunction\s+transform\s*\(")
_SELECTOR = re.compile(r"\bfunction\s+select\s*\(")


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
    selector = bool(_SELECTOR.search(code))
    if t.kind == "writer":
        return f"{t.name} is a writer: it takes notes (write_score), not an algorithm"
    if t.kind == "selector" and not selector:
        return (f"{t.name} is a selector: it picks notes of the score in its roll. "
                "Write function select(source, p) { ... } returning the notes it picks")
    if t.kind != "selector" and selector:
        return f"{t.name} is a {t.kind}, not a selector: do not write function select"
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
        buffer = ServerBuffer(bridge)  # read like read_score
        score = buffer.fetch(timeout_seconds=3.0)
        if not score or not count_notes(score):
            return None, "a built-in test score: the roll is empty or Max did not hand it over"
        return buffer.path, "the score in the roll"

    @mcp.tool()
    def send_algorithm(code: str) -> str:
        """Write the music as an algorithm: a JavaScript file that generates the score
        (the file and the library in scope are described in the skill). It is checked,
        saved and sent to Max, where its parameters become a panel the user plays
        with; every change runs it again. Sending it again replaces it.

        code: the whole file: const params = {...}; then function produce(p) {...} (a generator),
          function transform(source, p) {...} (a transformer of the score in its roll)
          or function select(source, p) {...} returning the notes it picks (a selector).
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

        source, origin = _source_for(t) if t.kind in ("transformer", "selector") else (None, "")
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
            status = f"and sent to Max ({name})"

        params = "\n".join(f"  {p}" for p in result["describe"]) or "  (none)"
        kind = ""
        if result.get("kind") == "selector":
            picked = ", ".join(f"[{v} {c} {n}]" for v, c, n in (result.get("selection") or [])[:24])
            more = " ..." if len(result.get("selection") or []) > 24 else ""
            return (
                f"OK. Algorithm saved as algorithms/{file} {status}.\n"
                f"Selector, checked on {origin} ({result['source']['notes']} notes). In Max every change "
                f"asks the roll for its score and selects in it.\n"
                f"Parameters (now a panel in Max):\n{params}\n"
                f"Checked in {result['runs']} runs (every slider at its minimum and maximum, every option).\n"
                f"At the declared values it picks {result['notes']} notes ([voice chord note]): {picked or 'none'}{more}"
            )
        if result.get("kind") == "transformer":
            kind = (f"Transformer, checked on {origin} ({result['source']['notes']} notes). In Max its source "
                    f"lives in memory (non-destructive: every run starts again from it).\n")
        return (
            f"OK. Algorithm saved as algorithms/{file} {status}.\n{kind}"
            f"Parameters (now a panel in Max):\n{params}\n"
            f"Checked in {result['runs']} runs (every slider at its minimum and maximum, every option).\n"
            f"Score at the declared values ({result['notes']} notes, {result['ms']} ms):\n{describe(result['score'])}"
        )


__all__ = ["register_algo_tools", "check_algorithm", "ALGO_TOOLS"]
