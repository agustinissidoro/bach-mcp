"""
algo_tools.py
-------------
send_algorithm: the model writes the algorithm that generates the music, not the
notes. The code is a JavaScript file run in Max by bach.mcp.algo (v8), with the
core library of max/bach-mcp/javascript/bach.mcp.core.js in scope. Its declared
parameters become a panel (bach.mcp.params) the user plays with; every change
runs the algorithm again.

Before a file reaches Max it is run here in Node, with the same core library: at
its declared values and at the edges of every parameter. Only a file that passes
replaces the previous version (kept in algorithms/.history) and is loaded.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .server import BachMCPServer
from .translate import ScoreError, normalize_score, summarize

ALGO_TOOLS = ("send_algorithm",)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CHECK_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "algo_check.js")
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,47}$")
_CHECK_TIMEOUT_SECONDS = 20.0
_CONFIRM_SECONDS = 4.0


def algorithms_dir() -> str:
    """Where algorithm files are written: [algo] dir in bach.toml (relative to the repo)."""
    folder = os.path.expanduser(os.getenv("BACH_ALGO_DIR") or "algorithms")
    return folder if os.path.isabs(folder) else os.path.join(_REPO_ROOT, folder)


def check_algorithm(path: str, timeout: Optional[float] = None) -> Dict[str, Any]:
    """Run algo_check.js on a file. Returns its JSON answer, or {"ok": False, "error": ...}."""
    timeout = timeout or _CHECK_TIMEOUT_SECONDS
    node = os.getenv("BACH_NODE") or "node"
    try:
        done = subprocess.run(
            [node, _CHECK_SCRIPT, path],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"Node.js not found ({node}); set [algo] node in bach.toml", "fatal": True}
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


def register_algo_tools(mcp: FastMCP, bach: BachMCPServer) -> None:
    """Register send_algorithm on `mcp`."""

    def _wait_for_max(runner: str) -> Optional[str]:
        """The runner's answer to a load: "loaded <runner> <file> <notes> <ms>" or "error <runner> <message>"."""
        deadline = time.time() + _CONFIRM_SECONDS
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            message = bach.wait_for_incoming(timeout_seconds=remaining)
            if message is None:
                return None
            words = str(message.get("data", "")).split()
            if len(words) >= 3 and words[0] == "algo_status" and words[2] == runner and words[1] in ("loaded", "error"):
                return " ".join(words[1:])

    @mcp.tool()
    def send_algorithm(name: str, code: str, runner: str = "algo") -> str:
        """Write the music as an algorithm: a JavaScript file that generates the score
        (the file and the library in scope are described in the skill). It is checked,
        saved as algorithms/<name>.js and loaded in Max, where its parameters become a
        panel the user plays with; every change runs it again.

        name: the file name, letters, digits, _ or - (e.g. "walkers"). The same name replaces it.
        code: the whole file: const params = {...}; function generate(p, input) {... return s; }
        runner: which bach.mcp.algo loads it (default "algo").
        The result lists the parameters and the score at the declared values; the file
        has also been run at every slider's minimum and maximum. Do not call it again to check.
        """
        if not _NAME.match(name or ""):
            return "ERROR: name must start with a letter and use only letters, digits, _ or - (e.g. \"walkers\")."
        if not (code or "").strip():
            return "ERROR: code is empty. Send the whole file: const params = {...}; function generate(p, input) {...}"
        runner = (runner or "algo").strip() or "algo"

        folder = algorithms_dir()
        os.makedirs(os.path.join(folder, ".history"), exist_ok=True)
        final = os.path.join(folder, f"{name}.js")
        draft = os.path.join(folder, ".history", f".{name}.draft.js")
        with open(draft, "w", encoding="utf-8") as f:
            f.write(code.rstrip() + "\n")

        result = check_algorithm(draft)
        if not result.get("ok"):
            os.remove(draft)
            return _error_text(name, result)
        try:
            canonical = normalize_score(result["score"])
        except ScoreError as exc:
            os.remove(draft)
            return _error_text(name, {"error": f"the score is not valid: {exc}"})

        if os.path.exists(final):
            with open(final, encoding="utf-8") as f:
                unchanged = f.read() == code.rstrip() + "\n"
            if not unchanged:
                stamp = time.strftime("%Y%m%d-%H%M%S")
                shutil.copy2(final, os.path.join(folder, ".history", f"{name}-{stamp}.js"))
        os.replace(draft, final)

        bach.flush_incoming()
        sent = bach.send_info(f'algo {runner} load "{final}"')
        if not sent:
            status = "but Max could not be reached (is the patch open and the script started?)"
        else:
            answer = _wait_for_max(runner)
            if answer is None:
                status = f"and sent to Max, which did not confirm (is there a bach.mcp.algo named \"{runner}\"?)"
            elif answer.startswith("error"):
                status = f"but Max reported an error: {answer.split(' ', 2)[-1]}"
            else:
                status = f"and loaded in Max (bach.mcp.algo \"{runner}\")"

        relative = os.path.relpath(final, _REPO_ROOT) if final.startswith(_REPO_ROOT) else final
        params = "\n".join(f"  {line}" for line in result["describe"]) or "  (none)"
        return (
            f"OK. Algorithm \"{name}\" saved as {relative} {status}.\n"
            f"Parameters (now a panel in Max):\n{params}\n"
            f"Checked in {result['runs']} runs (every slider at its minimum and maximum, every option).\n"
            f"Score at the declared values ({result['notes']} notes, {result['ms']} ms):\n{summarize(canonical)}"
        )


__all__ = ["register_algo_tools", "check_algorithm", "algorithms_dir", "ALGO_TOOLS"]
