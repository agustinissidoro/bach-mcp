"""
evaluate.py
-----------
A fixed set of requests, each sent several times to the model through the same
path as the web chat (mode, docs, skill, tools, sampling of bach.toml), with
automatic checks on what comes back. It measures, so that a change to the
skill, the format or the settings is judged by results:

    python py/main.py eval                 every case, 5 runs each
    python py/main.py eval --runs 10 --case neapolitan,trio

For every case it reports how many replies were valid, how many looped (ran
out of tokens inside an unfinished tool call), the mean time, each check, and
"plan vs written": every accidental the reply's plan names (D♭, F#, ...) must
be in the score it writes. Max is not needed: scores are checked here, and an
algorithm is checked with the Node check that send_algorithm uses.

Each run is saved, with the plan and the tool call, in logs/eval-<time>.json.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from .algo_tools import check_algorithm
from .config import REPO_ROOT, BachConfig
from .docs import DocLibrary
from .gateway import ModeSwitch, build_ollama_request, with_docs
from .pitch import name_to_cents
from .pitch_tools import FUNCTIONS as PITCH_FUNCTIONS, call_pitch_tool
from .score_tools import close_brackets
from .translate import ScoreError, normalize_score

Check = Tuple[str, Optional[bool], str]  # label, passed (None = not applicable), detail


# ── Reading a score ─────────────────────────────────────────────────────── #

def chords_by_onset(score: Dict[str, Any]) -> List[Tuple[float, List[float]]]:
    """The pitches sounding together at each onset, over all voices, in time order."""
    at: Dict[float, List[float]] = {}
    for v in score["voices"]:
        for c in v["chords"]:
            at.setdefault(c["onset"], []).extend(n["pitch"] for n in c["notes"])
    return sorted(at.items())


def pitch_classes(pitches: List[float]) -> set:
    return {int(round(p / 100)) % 12 for p in pitches}


def offset(pitch: float) -> float:
    """Cents from the nearest semitone."""
    return pitch - round(pitch / 100) * 100


def voice_named(score: Dict[str, Any], word: str) -> Optional[Dict[str, Any]]:
    return next((v for v in score["voices"] if word in v["name"].lower()), None)


def ratio(passed: int, total: int) -> str:
    return f"{passed}/{total}"


# ── The cases ───────────────────────────────────────────────────────────── #

def check_neapolitan(score: Dict[str, Any], raw: Any) -> List[Check]:
    chords = chords_by_onset(score)
    sets = [pitch_classes(p) for _, p in chords]
    names = " | ".join(" ".join(str(int(p)) for p in ps) for _, ps in chords)
    v_or_v7 = lambda s: {7, 11, 2} <= s <= {7, 11, 2, 5}  # noqa: E731
    return [
        ("Neapolitan chord (Db F Ab)", any(s == {1, 5, 8} for s in sets), names),
        ("ends V -> I", len(sets) >= 2 and sets[-1] == {0, 4, 7} and v_or_v7(sets[-2]), names),
        ("4 notes in every chord", all(len(p) == 4 for _, p in chords), names),
    ]


def check_trio(score: Dict[str, Any], raw: Any) -> List[Check]:
    voices = score["voices"]
    firsts = [v["chords"][0]["onset"] for v in voices if v["chords"]]
    cello = voice_named(score, "cello")
    staccato = sum("staccato" in c.get("art", []) for c in cello["chords"]) if cello else 0
    lows = {w: (min(n["pitch"] for c in v["chords"] for n in c["notes"]) if (v := voice_named(score, w)) and v["chords"] else None)
            for w in ("violin", "viola", "cello")}
    floors = {"violin": 5500, "viola": 4800, "cello": 3600}
    return [
        ("3 voices", len(voices) == 3, f"{len(voices)} voices"),
        ("entries one after another", len(firsts) == len(set(firsts)) and len(firsts) == 3, f"first onsets {firsts}"),
        ("cello staccato", bool(cello) and staccato >= len(cello["chords"]) / 2,
         f"{staccato} of {len(cello['chords']) if cello else 0} cello chords"),
        ("every instrument in its range", all(lows[w] is not None and lows[w] >= floors[w] for w in floors), f"lowest {lows}"),
    ]


def check_spiral(score: Dict[str, Any], raw: Any) -> List[Check]:
    notes = [(c["onset"], n) for v in score["voices"] for c in v["chords"] for n in c["notes"]]
    notes.sort(key=lambda x: x[0])
    pitches = [n["pitch"] for _, n in notes]
    durs = [n["dur"] for _, n in notes]
    return [
        ("12 notes", len(notes) == 12, f"{len(notes)} notes"),
        ("quarter-tones", any(abs(abs(offset(p)) - 50) < 1 for p in pitches), " ".join(str(int(p)) for p in pitches)),
        ("ends higher than it starts", len(pitches) > 1 and pitches[-1] > pitches[0], ""),
        ("last note held longest", len(durs) > 1 and durs[-1] > max(durs[:-1]), f"durations {durs}"),
    ]


def check_microtonal(score: Dict[str, Any], raw: Any) -> List[Check]:
    chords = chords_by_onset(score)
    pitches = [p for _, ps in chords for p in ps]

    def tuned(pc: int, cents: float) -> bool:
        return any(int(round(p / 100)) % 12 == pc and abs(offset(p) - cents) <= 3 for p in pitches)

    shown = " ".join(f"{int(round(p / 100)) % 12}:{offset(p):+.0f}" for p in pitches)
    return [
        ("one sustained chord", len(chords) == 1, f"{len(chords)} onsets"),
        ("E a just third (-14 cents)", tuned(4, -14), shown),
        ("G a just fifth (+2 cents)", tuned(7, 2), shown),
        ("Bb the natural seventh (-31 cents)", tuned(10, -31), shown),
    ]


# Exact pitch arithmetic: the answer is known to the cent.

def line(score: Dict[str, Any], voice: Optional[Dict[str, Any]] = None) -> List[float]:
    """Every pitch of a voice (or of the score), in time order, low to high within a chord."""
    voices = [voice] if voice else score["voices"]
    notes = sorted((c["onset"], n["pitch"]) for v in voices for c in v["chords"] for n in c["notes"])
    return [p for _, p in notes]


def cents(*names: str) -> List[float]:
    return [name_to_cents(n) for n in names]


def shown(pitches: List[float]) -> str:
    return " ".join(f"{p:g}" for p in pitches)


MELODY = ("D4", "F4", "A4", "G4", "E4", "C#4", "D4")


def check_transposition(score: Dict[str, Any], raw: Any) -> List[Check]:
    melody = cents(*MELODY)
    parts = {w: line(score, v) if (v := voice_named(score, w)) else [] for w in ("violin", "viola", "cello")}
    detail = " | ".join(f"{w} {shown(p)}" for w, p in parts.items())
    return [
        ("violin plays the melody", parts["violin"] == melody, detail),
        ("viola a minor sixth lower (-800)", parts["viola"] == [p - 800 for p in melody], detail),
        ("cello an octave and a fourth lower (-1700)", parts["cello"] == [p - 1700 for p in melody], detail),
    ]


ROW = ("G", "Bb", "D", "F#", "A", "C", "E", "G#", "B", "C#", "Eb", "F")  # Berg, Violin Concerto


def check_row(score: Dict[str, Any], raw: Any) -> List[Check]:
    pcs = [int(round(p / 100)) % 12 for p in line(score)]
    prime = [int(name_to_cents(f"{n}4") / 100) % 12 for n in ROW]
    inversion = [(2 * prime[0] - x) % 12 for x in prime]
    forms = {"prime": prime, "retrograde": prime[::-1], "inversion": inversion, "retrograde inversion": inversion[::-1]}
    detail = " ".join(map(str, pcs))
    checks: List[Check] = [("48 notes", len(pcs) == 48, f"{len(pcs)} notes")]
    for i, (label, form) in enumerate(forms.items()):
        checks.append((label, pcs[i * 12:(i + 1) * 12] == form, detail))
    return checks


SEVENTHS = (("Bbm7b5", 10, [{10, 1, 4, 8}]), ("Eb7b9", 3, [{3, 7, 10, 1, 4}]),
            ("Abmaj9", 8, [{8, 0, 3, 7, 10}]), ("Db13", 1, [{1, 5, 8, 11, 3, 10}, {1, 5, 8, 11, 3, 6, 10}]))  # 11th optional


def check_jazz_chords(score: Dict[str, Any], raw: Any) -> List[Check]:
    chords = chords_by_onset(score)
    detail = " | ".join(shown(sorted(ps)) for _, ps in chords)
    checks: List[Check] = [("4 chords", len(chords) == 4, f"{len(chords)} onsets")]
    for i, (label, root, pcs) in enumerate(SEVENTHS):
        ps = sorted(chords[i][1]) if i < len(chords) else []
        checks.append((f"{label} complete, root in the bass",
                       bool(ps) and pitch_classes(ps) in pcs and int(round(ps[0] / 100)) % 12 == root, detail))
    return checks


def check_scale(score: Dict[str, Any], raw: Any) -> List[Check]:
    steps = [0, 200, 300, 500, 700, 800, 1100]
    up = [5200 + o * 1200 + s for o in range(2) for s in steps] + [7600]
    got = line(score)
    return [("E harmonic minor, E3 up two octaves and back", got == up + up[-2::-1], shown(got))]


def check_harmonics(score: Dict[str, Any], raw: Any) -> List[Check]:
    chords = chords_by_onset(score)
    exact = [3600 + 1200 * math.log2(n) for n in range(1, 9)]
    got = sorted(p for _, ps in chords for p in ps)
    return [
        ("one chord", len(chords) == 1, f"{len(chords)} onsets"),
        ("harmonics 1-8 of C2 to the cent", len(got) == 8 and all(abs(a - b) <= 0.5 for a, b in zip(got, exact)),
         shown(got)),
    ]


@dataclass
class Case:
    name: str
    mode: str
    prompt: str
    check: Callable[..., List[Check]]
    max_tokens: int = 3000
    tool: str = "write_score"


CASES = [
    Case("neapolitan", "score", "write a perfect cadence with a napolitan chord. 4 real voices for piano.", check_neapolitan),
    Case("trio", "score", "A string trio (violin, viola, cello): three voices enter one after another in imitation, "
         "the cello staccato.", check_trio),
    Case("spiral", "score", "A flute melody of 12 notes that spirals upward in quarter-tones; the last note is held.",
         check_spiral),
    Case("microtonal", "score", "One sustained chord for strings in just intonation: C, a pure major third, a pure "
         "fifth and the natural seventh above C.", check_microtonal),
    Case("transposition", "score", "A violin plays D4 F4 A4 G4 E4 C#4 D4, 400 ms per note. When it ends, the viola "
         "plays the same melody a minor sixth lower; when the viola ends, the cello plays it an octave and a "
         "fourth lower than the violin.", check_transposition),
    Case("row", "score", "Piano, one line, 250 ms per note: the row G Bb D F# A C E G# B C# Eb F (octaves as you like), "
         "then its retrograde, then its inversion starting on G, then the retrograde of that inversion.", check_row),
    Case("jazz", "score", "Piano: four chords of one second each, complete and in root position: Bbm7b5, Eb7b9, "
         "Abmaj9, Db13.", check_jazz_chords),
    Case("scale", "score", "Clarinet: the E harmonic minor scale from E3 up two octaves and back down to E3, "
         "200 ms per note.", check_scale),
    Case("harmonics", "score", "One sustained chord for eight instruments: the first eight harmonics of C2, each "
         "tuned exactly.", check_harmonics),
    Case("algo", "algo", "A pulse for marimba that gets faster and faster. Parameters for its length and for how "
         "fast it starts and ends.", lambda *a: [], max_tokens=6000, tool="send_algorithm"),
]


# ── Plan vs written ─────────────────────────────────────────────────────── #

_ACCIDENTAL = re.compile(r"\b([A-G])(♭|♯|b|#)(?![a-z])")
_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def plan_accidentals(plan: str) -> set:
    """Pitch classes of the notes with an accidental that a plan names (D♭, F#, Bb ...)."""
    return {(_PC[letter] + (1 if acc in "♯#" else -1)) % 12 for letter, acc in _ACCIDENTAL.findall(plan)}


# ── Pitch tools ─────────────────────────────────────────────────────────── #

_ROUNDS = 6  # model turns per run: pitch tool calls, then the score


def _numbers_in(text: str) -> set:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return set()
    flat = lambda v: [x for i in v for x in flat(i)] if isinstance(v, list) else [v]  # noqa: E731
    return {round(float(x), 2) for x in flat(value) if isinstance(x, (int, float))}


def pitch_tool_checks(score: Dict[str, Any], pitch_calls: List[Dict[str, Any]]) -> List[Check]:
    """Did the model ask the pitch tools, and did it copy their answers?"""
    answered = set().union(*(_numbers_in(c["answer"]) for c in pitch_calls)) if pitch_calls else set()
    written = {round(n["pitch"], 2) for v in score["voices"] for c in v["chords"] for n in c["notes"]}
    stray = sorted(written - answered)
    return [
        ("used the pitch tools", bool(pitch_calls), ", ".join(c["tool"] for c in pitch_calls) or "none"),
        ("every pitch copied from a tool answer", not stray if pitch_calls else None,
         f"not in any answer: {shown(stray)}" if stray else "all copied"),
    ]


# ── Running ─────────────────────────────────────────────────────────────── #

def _tools(toolset: str) -> List[Dict[str, Any]]:
    from .mcp_app import create_mcp_app

    class _Offline:  # the tools are only listed, never called
        pass

    app = create_mcp_app(_Offline(), toolset=toolset)
    return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}}
            for t in asyncio.run(app.list_tools())]


def check_algorithm_code(code: str) -> Tuple[List[Check], Optional[Dict[str, Any]]]:
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "eval.js")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        result = check_algorithm(path)
    if not result.get("ok"):
        return [("passes the check at every parameter edge", False, result.get("error", ""))], None
    score = result["score"]
    onsets = sorted(c["onset"] if isinstance(c, dict) else c[0] for c in score["voices"][0]["chords"]) if score["voices"] else []
    gaps = [b - a for a, b in zip(onsets, onsets[1:])]
    return [
        ("passes the check at every parameter edge", True, f"{result['runs']} runs"),
        ("a producer", result.get("kind") == "producer", str(result.get("kind"))),
        ("at least 2 parameters", len(result["params"]) >= 2, ", ".join(p["name"] for p in result["params"])),
        ("gets faster", len(gaps) >= 2 and gaps[-1] < gaps[0], f"first gap {gaps[0]:.0f} ms, last {gaps[-1]:.0f} ms" if gaps else "no gaps"),
    ], score


def run_once(case: Case, config: BachConfig, tools: List[Dict[str, Any]], library: Optional[DocLibrary]) -> Dict[str, Any]:
    request = {"messages": [{"role": "system", "content": config.system_prompt()},
                            {"role": "user", "content": f"/{case.mode} {case.prompt}"}],
               "tools": tools, "chat_template_kwargs": {"enable_thinking": config.generation.reasoning not in ("off",)}}
    payload = build_ollama_request(with_docs(ModeSwitch(config)(request), library), config)
    payload["stream"] = False
    payload["options"]["num_predict"] = case.max_tokens
    start = time.time()
    out: Dict[str, Any] = {"tokens": 0, "plan": "", "pitch_calls": [], "checks": []}
    calls: List[Dict[str, Any]] = []
    for _ in range(_ROUNDS):  # the pitch tools answer here, as the MCP server would, until the music is sent
        reply = httpx.post(f"{config.ollama.url}/api/chat", json=payload, timeout=1800).json()
        message = reply.get("message") or {}
        out["tokens"] += reply.get("eval_count") or 0
        out["plan"] = "\n".join(t for t in (out["plan"], (message.get("content") or "").strip()) if t)
        requested = message.get("tool_calls") or []
        calls = [c for c in requested if c["function"]["name"] == case.tool]
        pitch_calls = [c for c in requested if c["function"]["name"] in PITCH_FUNCTIONS]
        if calls or not pitch_calls:
            break
        payload["messages"].append({"role": "assistant", "content": message.get("content") or "", "tool_calls": requested})
        for c in requested:
            name, args = c["function"]["name"], c["function"].get("arguments") or {}
            result = call_pitch_tool(name, args) if name in PITCH_FUNCTIONS else f"ERROR: {name} is not available here."
            out["pitch_calls"].append({"tool": name, "arguments": args, "answer": result})
            payload["messages"].append({"role": "tool", "content": result, "tool_name": name})
    out["seconds"] = round(time.time() - start, 1)
    if not calls:
        out["outcome"] = "loop" if reply.get("done_reason") == "length" else "no call"
        return out
    args = calls[0]["function"]["arguments"]
    out["call"] = args
    if case.tool == "send_algorithm":
        checks, _ = check_algorithm_code(str(args.get("code", "")))
        out["checks"] = checks
        out["outcome"] = "valid" if checks[0][1] else "invalid"
        return out
    raw = args.get("score")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = close_brackets(raw)
    try:
        score = normalize_score(raw)
    except (ScoreError, TypeError, ValueError) as exc:
        out["outcome"] = "invalid"
        out["error"] = str(exc)
        return out
    out["outcome"] = "valid"
    out["checks"] = case.check(score, raw) + pitch_tool_checks(score, out["pitch_calls"])
    named = plan_accidentals(out["plan"])
    if named:
        written = {int(round(n["pitch"] / 100)) % 12 for v in score["voices"] for c in v["chords"] for n in c["notes"]}
        missing = sorted(named - written)
        out["checks"].append(("plan vs written (accidentals)", not missing,
                              f"named {sorted(named)}, missing in the score {missing}" if missing else "all present"))
    return out


def run_suite(config: BachConfig, runs: int = 5, only: Optional[List[str]] = None) -> Dict[str, Any]:
    if not config.uses_ollama:
        raise SystemExit("eval talks to Ollama: set [model] backend = \"ollama\" in bach.toml")
    tools = _tools(config.mcp.toolset)
    library = DocLibrary() if config.chat.docs else None
    cases = [c for c in CASES if not only or c.name in only]
    report: Dict[str, Any] = {"when": time.strftime("%Y-%m-%d %H:%M"), "model": config.model.ollama_model,
                              "sampling": {k: getattr(config.generation, k) for k in
                                           ("temperature", "top_p", "top_k", "presence_penalty", "reasoning")},
                              "cases": {}}
    for case in cases:
        results = []
        for i in range(runs):
            result = run_once(case, config, tools, library)
            results.append(result)
            failed = [label for label, ok, _ in result["checks"] if ok is False]
            print(f"  {case.name:11s} run {i + 1}: {result['outcome']:8s} {result['seconds']:6.1f} s"
                  + (f"  failed: {', '.join(failed)}" if failed else ""), flush=True)
        report["cases"][case.name] = results
    os.makedirs(os.path.join(REPO_ROOT, "logs"), exist_ok=True)
    path = os.path.join(REPO_ROOT, "logs", f"eval-{time.strftime('%Y%m%d-%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print()
    print(summary(report))
    print(f"\nEvery run, with its plan and tool call: {os.path.relpath(path, REPO_ROOT)}")
    return report


def summary(report: Dict[str, Any]) -> str:
    lines = [f"{report['model']}  sampling {report['sampling']}", ""]
    for name, results in report["cases"].items():
        n = len(results)
        count = lambda outcome: sum(r["outcome"] == outcome for r in results)  # noqa: E731
        seconds = sum(r["seconds"] for r in results) / max(1, n)
        lines.append(f"{name}: valid {ratio(count('valid'), n)}, loops {ratio(count('loop'), n)}, "
                     f"no call {ratio(count('no call'), n)}, invalid {ratio(count('invalid'), n)}, {seconds:.0f} s mean")
        labels: Dict[str, List[bool]] = {}
        for r in results:
            for label, ok, _ in r["checks"]:
                if ok is not None:
                    labels.setdefault(label, []).append(ok)
        for label, oks in labels.items():
            lines.append(f"    {label:42s} {ratio(sum(oks), len(oks))}")
    return "\n".join(lines)


__all__ = ["CASES", "run_suite", "summary", "plan_accidentals", "check_algorithm_code", "pitch_tool_checks"]
