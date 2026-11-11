"""
gen_tools.py
------------
send_gen: the model writes sound, not notes: GenExpr code that runs sample by
sample inside gen~ in Max, for a synth instance (it makes sound) or an fx instance
(it processes the sound that comes in). Its parameters become the same panel an
algorithm has (GUI_parameters/); a change there sets the Param of that name in gen~.

These are the tools of the gen mode (prompt/modes.py MODE_TOOLS): a synth or an fx
instance gets only them, and never the tools of the score. Called for an instance
of another type, send_gen refuses, as send_algorithm and write_score refuse a synth.

There is no gen~ compiler outside Max, so the code is not run here: gen_check.js
(Node) parses it and checks it against what gen~ accepts (syntax, operators and their
arguments, names set before they are read, inlets and outlets described, Params
against the panel's declarations). Then a last check on the gendsp itself, before it is
written (panel_mismatch): every parameter of the panel is a Param of its codebox and
sends a number, since gen~ takes no symbols. Only a file that passes replaces the previous
version (kept in gen/.history) and is loaded, without waiting for an answer:

    <name> load_gen <name>.gendsp                    to Max

Three files are written for the instance, in the playground's gen/ folder:

    <name>.genexpr   the code as the model wrote it
    <name>.gendsp    the same code in a gen patcher (one codebox between its in and
                     out objects): what gen~ loads (its `gen` attribute)
    <name>.json      what the patch needs around it: {"description", "type", "inlets",
                     "outlets", "params", "buffers", "data"}. Each param has "send": the
                     number gen~ gets for its value (a toggle 0 or 1, a menu the index
                     of its option); each buffer {"name", "buffer"}: the name in the
                     code and the buffer~ it reads, which the message `<name> <buffer~>`
                     to gen~ changes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP

from ..bridge.max import MaxBridge
from ..bridge.protocol import line
from .session import NoTarget, target

GEN_TOOLS = ("send_gen",)
GEN_TYPES = ("synth", "fx")

_CHECK_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_check.js")
_CHECK_TIMEOUT_SECONDS = 20.0
_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def check_gen(path: str, instance_type: str, params: Optional[str] = None, node: str = "node") -> Dict[str, Any]:
    """Run gen_check.js on a GenExpr file (params: the file with the panel's declarations).
    Returns its JSON answer, or {"ok": False, "error": ...}."""
    try:
        done = subprocess.run(
            [node, _CHECK_SCRIPT, path, "--type", instance_type] + (["--params", params] if params else []),
            capture_output=True, text=True, timeout=_CHECK_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"Node.js not found ({node}); set [algo] node in bachmcp.toml", "fatal": True}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "the check did not finish", "fatal": True}
    lines = [row for row in done.stdout.splitlines() if row.strip()]
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        detail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
        return {"ok": False, "error": f"the check failed: {detail[0]}", "fatal": True}


def gendsp(code: str, inlets: int, outlets: int) -> Dict[str, Any]:
    """The code as a gen patcher: one codebox, fed by `in 1` ... and feeding `out 1` ..."""
    boxes: List[Dict[str, Any]] = [{"box": {
        "id": "obj-code", "maxclass": "codebox", "code": code.replace("\n", "\r\n"),
        "fontface": 0, "fontname": "<Monospaced>", "fontsize": 12.0,
        "numinlets": max(inlets, 1), "numoutlets": max(outlets, 1), "outlettype": [""] * max(outlets, 1),
        "patching_rect": [40.0, 80.0, 720.0, 520.0],
    }}]
    lines: List[Dict[str, Any]] = []
    for k in range(1, inlets + 1):
        boxes.append({"box": {"id": f"obj-in-{k}", "maxclass": "newobj", "text": f"in {k}", "numinlets": 0, "numoutlets": 1,
                              "outlettype": [""], "patching_rect": [40.0 + 70.0 * (k - 1), 30.0, 40.0, 22.0]}})
        lines.append({"patchline": {"source": [f"obj-in-{k}", 0], "destination": ["obj-code", k - 1]}})
    for k in range(1, outlets + 1):
        boxes.append({"box": {"id": f"obj-out-{k}", "maxclass": "newobj", "text": f"out {k}", "numinlets": 1, "numoutlets": 0,
                              "patching_rect": [40.0 + 70.0 * (k - 1), 630.0, 45.0, 22.0]}})
        lines.append({"patchline": {"source": ["obj-code", k - 1], "destination": [f"obj-out-{k}", 0]}})
    return {"patcher": {
        "fileversion": 1,
        "appversion": {"major": 8, "minor": 6, "revision": 0, "architecture": "x64", "modernui": 1},
        "classnamespace": "dsp.gen",
        "rect": [100.0, 100.0, 820.0, 720.0],
        "boxes": boxes,
        "lines": lines,
    }}


_PARAM = re.compile(r"\bParam\s+([A-Za-z_]\w*)")


def panel_mismatch(patch: Dict[str, Any], params: List[Dict[str, Any]]) -> List[str]:
    """The last check, on what Max will load: every parameter of the panel must be a Param in
    the gendsp's codebox and send a number (gen~ takes no symbols). Returns the problems."""
    code = "".join(box["box"].get("code", "") for box in patch["patcher"]["boxes"]
                   if box["box"].get("maxclass") == "codebox")
    declared = set(_PARAM.findall(_COMMENT.sub("", code)))
    problems = []
    for spec in params:
        name, send = spec.get("name"), spec.get("send")
        if name not in declared:
            problems.append(f"the panel's parameter {name} is not a Param in the gendsp")
        if isinstance(send, bool) or not isinstance(send, (int, float)):
            problems.append(f"the panel's parameter {name} sends {send!r}, not a number")
    return problems


def _bare(code: str) -> str:
    """The code without comments and whitespace: two files with the same bare text sound the same."""
    return re.sub(r"\s+", "", _COMMENT.sub("", code or ""))


def _params(params: Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
    """The panel's declarations as an object (a model may send them as JSON text). Raises ValueError."""
    if params is None or params == "":
        return {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except ValueError as exc:
            raise ValueError(f"params is not valid JSON ({exc})") from None
    if not isinstance(params, dict):
        raise ValueError('params must be an object: {"cutoff": {"type": "slider", "range": [20, 20000], "value": 1000}}')
    return params


_DOC = """gen~ code (sound, not a score): write the sound as GenExpr, the code of a gen~
        codebox (the language, the file and its operators are described in the skill). It is
        checked, saved and loaded in the gen~ of this synth or fx instance in Max, where
        `params` become a panel the user plays with while it sounds. Sending it again replaces it.

        code: the whole file. It opens with a // comment: what it does, in one line of plain
          words (shown above its panel); then one comment line for every inlet and outlet it
          uses (// in1: ..., // out1: ...); then functions, declarations (Param, History, Delay,
          Data, Buffer) and the statements that set out1, out2 ...
        params: the panel, one entry for each Param of the code, with the same name and the
          same starting value:
          {"cutoff": {"type": "slider", "range": [20, 20000], "value": 1000, "unit": "Hz"},
           "drive": {"type": "toggle", "value": false},
           "shape": {"type": "menu", "options": ["sine", "saw"], "value": "sine"}}
        The result lists the inlets, outlets, parameters and buffers of the file. The code has
        been checked, not listened to. Do not call it again to check.
        """


def register_gen_tools(mcp: FastMCP, bridge: MaxBridge, node: str = "node") -> None:
    """Register send_gen on `mcp`. node: the Node.js that checks the files ([algo] node)."""

    def send_gen(code: str, params: Union[Dict[str, Any], str, None] = None) -> str:
        try:
            t = target()
        except NoTarget as exc:
            return f"ERROR: {exc}. Nothing was loaded."
        if t.type not in GEN_TYPES:
            return (f"ERROR: {t.name} is a {t.type} instance: it works on the score, not on sound. "
                    "send_gen is for a synth or an fx instance. Nothing was loaded.")
        if not (code or "").strip():
            return "ERROR: code is empty. Send the whole GenExpr file. Nothing was loaded."
        try:
            declared = _params(params)
        except ValueError as exc:
            return f"ERROR: {exc}. Nothing was loaded."

        name, folder = t.name, t.gen
        history = os.path.join(folder, ".history")
        os.makedirs(history, exist_ok=True)
        final = t.gen_file
        text = code.rstrip() + "\n"
        draft = os.path.join(history, f".{name}.draft.genexpr")
        draft_params = os.path.join(history, f".{name}.draft.json")
        with open(draft, "w", encoding="utf-8") as f:
            f.write(text)
        with open(draft_params, "w", encoding="utf-8") as f:
            json.dump(declared, f)
        result = check_gen(draft, t.type, draft_params, node=node)
        os.remove(draft_params)
        if not result.get("ok"):
            os.remove(draft)
            if result.get("fatal"):
                return f"ERROR: {result['error']}. Nothing was loaded."
            where = f"{name}.genexpr" + (f" line {result['line']}" if result.get("line") else "")
            return (f"ERROR in {where}: {result['error']}. Nothing was loaded. "
                    "Fix this and call send_gen again with the whole file and its params.")

        patch = gendsp(text, len(result["inlets"]), len(result["outlets"]))
        problems = panel_mismatch(patch, result["params"])
        if problems:
            os.remove(draft)
            return (f"ERROR in {name}.genexpr: {'; '.join(problems)}. Nothing was loaded. "
                    "Every entry of params is a Param of the code, with the same name, and its value is a number "
                    "(a menu sends the index of its option). Fix this and call send_gen again with the whole file and its params.")

        same = ""
        if os.path.exists(final):
            with open(final, encoding="utf-8") as f:
                previous = f.read()
            if _bare(previous) == _bare(code):
                same = ("\nNOTHING CHANGED in the code: apart from comments it is the file it replaces, so it sounds "
                        "the same unless a parameter's declaration changed. If you meant to correct something, "
                        "the line that causes it is still there: change that line.")
            if previous != text:
                stamp = time.strftime("%Y%m%d-%H%M%S")
                shutil.copy2(final, os.path.join(history, f"{name}-{stamp}.genexpr"))
        os.replace(draft, final)
        stem = os.path.splitext(final)[0]
        with open(stem + ".gendsp", "w", encoding="utf-8") as f:
            json.dump(patch, f, indent=1)
        about = {key: result[key] for key in ("description", "type", "inlets", "outlets", "params", "buffers", "data")}
        with open(stem + ".json", "w", encoding="utf-8") as f:
            json.dump(about, f, indent=1)

        bridge.flush()
        file = f"{name}.gendsp"
        if not bridge.send(line(name, "load_gen", file)):
            status = "but Max could not be reached (is the patch open?)"
        else:
            status = f"and sent to Max ({name})"

        def ports(rows: List[Dict[str, Any]], way: str) -> str:
            return "\n".join(f"  {way}{row['index']}: {row['about']}" for row in rows) or "  (none)"

        described = "\n".join(f"  {row}" for row in result["describe"]) or "  (none)"
        buffers = ""
        if result["buffers"]:
            rows = "\n".join(f"  {b['name']}: reads the buffer~ named {b['buffer']}" for b in result["buffers"])
            buffers = (f"Buffers (the user fills each buffer~ with a sound file or a table, and can point a name to "
                       f"another buffer~):\n{rows}\n")
        notes = "".join(f"Note: {w}.\n" for w in result.get("warnings") or [])
        return (
            f"OK. {t.type} saved as gen/{name}.genexpr {status}.\n"
            f'Shown above its panel: "{result["description"]}"\n'
            f"Inlets:\n{ports(result['inlets'], 'in')}\n"
            f"Outlets:\n{ports(result['outlets'], 'out')}\n"
            f"Parameters (now a panel in Max):\n{described}\n{buffers}{notes}"
            "Checked: the syntax, every operator and its arguments, every name, the parameters, and that every "
            "parameter of the panel is a Param of the gendsp and sends a number. "
            f"gen~ compiles it in Max; it has not been listened to.{same}"
        )

    send_gen.__doc__ = _DOC
    mcp.tool()(send_gen)


__all__ = ["register_gen_tools", "check_gen", "gendsp", "panel_mismatch", "GEN_TOOLS", "GEN_TYPES"]
