"""
runner.py
---------
Runs the code of buffer instances for the hub (chat/hub.py), offline: the samples Max holds
in one bachmcp.shmbuffer~ go through the instance's process(x, sr, p) and come back in another.
Max never runs Python: it sends lines to the hub, and the hub has this runner.

Each instance has a worker of its own (worker.py), a Python process started at its first run
and kept: imports and models are loaded once, and a crash or an endless loop never reaches the
hub. Its file is the playground's recipes/<name>.py, its panel recipes/<name>.json.

    load(name)                 recipes/<name>.py into its worker, nothing run; the kept values dropped
    run(name)                  run it now (after the last change, see below)
    set_param(name, key, words) a panel change: kept, then a run
    set_source / set_target    the bachmcp.shmbuffer~ it reads (default <name>-in) and the
                               bachmcp.pshmbuffer~ it writes (default <name>, the instance's own
                               name: one run is <name>.1, variations <name>.1 .. .N)
    loaded(name)               a new file: the values set before are dropped
    listen(name, file, spec)   the listen test of a file not yet loaded: run on the real source,
                               kept in the worker (the target and Max get nothing), described
                               next to the source (send_buffer_process, before it loads the file)
    commit(name)               what the listen test made, into the target: Max gets it
    set_goal(name, text)       the prompt being answered: what CLAP measures the sound against
    set_setting(name, key, words)  a buffer setting (settings.py): sources, fx, fx_exclude, variations
    settings(name)             its BufferSettings
    prompt_analysis(name)      the description of its source (and of its result, once there is one)
                               that the hub adds to each prompt
    stop(name)                 the run in progress ends (its worker is killed)
    forget(name)               stop, and drop everything kept for it

The descriptions come from the worker (analysis.py, and listen.py's models when they are
downloaded: `models` is {"tagger": <path>, "clap": <path>, "pitch": <path>}).

Requests close together become one run: a slider drag runs the code at the last value, not at
every value it passed. What comes out (send: the hub's _send):

    <name> processing
    <name> processed <ms> <frames> <channels> <sr>   (with variations > 1: the first one's, ms of all)
    <name> processed_variations <count>         before it, with variations > 1: <target>.1 .. .<count> are written
    <name> process_note <text>                  the result is silent, clips, had no sound in ...
    <name> process_error <text>
    <name> process_stopped
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..utilities.shmbuffer import NoShmBuffer, ShmBuffer
from .settings import BufferSettings

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py")
TIMEOUT_SECONDS = 600.0
SETTLE_SECONDS = 0.05


def sound_models(audio: Any) -> Dict[str, str]:
    """What the worker needs of bachmcp.toml [audio] (config.AudioConfig): each model's folder and name."""
    out: Dict[str, str] = {}
    for kind in ("tagger", "clap", "pitch"):
        name = getattr(audio, f"{kind}_model", "").strip()
        if name:
            out[kind], out[f"{kind}_name"] = audio.model_path(name), name
    return out


def value(words: List[str]) -> Any:
    """A value as the panel sends it: one word or many (a list), numbers as numbers."""
    def one(w: str) -> Any:
        for kind in (int, float):
            try:
                return kind(w)
            except ValueError:
                pass
        return w

    out = [one(w) for w in words]
    return out[0] if len(out) == 1 else out


def _end(worker: subprocess.Popen) -> None:
    """Kill a worker and let go of its pipes (its reader thread closes stdout when it sees the end)."""
    worker.kill()
    try:
        worker.wait(5)
    except subprocess.TimeoutExpired:
        pass
    if worker.stdin:
        try:
            worker.stdin.close()
        except OSError:
            pass


@dataclass
class _Instance:
    source: str
    target: str
    values: Dict[str, Any] = field(default_factory=dict)
    wanted: bool = False
    thread: Optional[threading.Thread] = None
    worker: Optional[subprocess.Popen] = None
    answers: "queue.Queue[Optional[str]]" = field(default_factory=queue.Queue)
    stopped: bool = False
    syncing: bool = False        # a listen test is running it, on a tool's thread
    has_result: bool = False     # a run wrote its target
    goal: str = ""
    settings: BufferSettings = field(default_factory=BufferSettings)
    asking: threading.Lock = field(default_factory=threading.Lock)  # one request at a time to its worker


class ProcessRunner:
    """send: says a line (words); playground: the playground folder now ("" when none)."""

    def __init__(self, send: Callable[..., None], playground: Callable[[], str],
                 python: str = sys.executable, timeout: float = TIMEOUT_SECONDS,
                 settle: float = SETTLE_SECONDS, models: Optional[Dict[str, str]] = None,
                 analysis: bool = True) -> None:
        self.send, self.playground = send, playground
        self.python, self.timeout, self.settle = python, timeout, settle
        self.models, self.analysis = dict(models or {}), analysis
        self._lock = threading.Lock()
        self._instances: Dict[str, _Instance] = {}

    def _get(self, name: str) -> _Instance:
        """Call with the lock held."""
        if name not in self._instances:
            self._instances[name] = _Instance(f"{name}-in", name)  # the target: [bachmcp.pshmbuffer~ <name>]
        return self._instances[name]

    # ── What the hub asks ───────────────────────────────────────────── #

    def set_source(self, name: str, shm: str) -> None:
        with self._lock:
            self._get(name).source = shm

    def set_target(self, name: str, shm: str) -> None:
        with self._lock:
            self._get(name).target = shm

    def set_param(self, name: str, key: str, words: List[str]) -> None:
        with self._lock:
            self._get(name).values[key] = value(words)
        self.run(name)

    def load(self, name: str) -> Dict[str, Any]:
        """recipes/<name>.py into the instance's worker, nothing run: the file is executed (its
        imports, what it loads at the top) and the panel's kept values are dropped, so the
        recipe starts at its declared values. {"ok": True}, or {"ok": False, "error", "line"}."""
        root = self.playground()
        if not root:
            return {"ok": False, "error": "no playground: the patch sends set_playground <folder>"}
        file = os.path.join(root, "recipes", f"{name}.py")
        if not os.path.exists(file):
            return {"ok": False, "error": f"no recipes/{name}.py yet: prompt {name} for one"}
        with self._lock:
            instance = self._get(name)
        answer = self._ask(instance, {"load": {"file": file}})
        if answer is None:
            return {"ok": False, "error": "the worker ended"}
        if answer.get("ok"):  # only a file that loaded drops them: a failed load changes nothing
            with self._lock:
                instance.values.clear()
        return answer

    def loaded(self, name: str) -> None:
        with self._lock:
            self._get(name).values.clear()

    def set_goal(self, name: str, text: str) -> None:
        with self._lock:
            self._get(name).goal = text

    def set_setting(self, name: str, key: str, words: List[str]) -> Optional[str]:
        """One buffer setting (settings.py). None when set, else why not."""
        root = self.playground()
        with self._lock:
            return self._get(name).settings.set(key, words, root)

    def settings(self, name: str) -> BufferSettings:
        with self._lock:
            return self._get(name).settings

    def prompt_settings(self, name: str) -> str:
        """What the hub adds to a prompt of this instance about its settings ("" at the defaults)."""
        return self.settings(name).prompt_block()

    def describe(self, name: str, which: str = "source") -> Optional[Dict[str, Any]]:
        """The worker's description of the instance's source or target memory (None: the worker ended)."""
        with self._lock:
            instance = self._get(name)
            shm = instance.source if which == "source" else f"{instance.target}.1"  # the first result
            request = {"shm": shm, "title": "SOURCE" if which == "source" else "RESULT",
                       "goal": instance.goal, "models": self.models}
        answer = self._ask(instance, {"describe": request})
        return answer if answer and answer.get("ok") else None

    def prompt_analysis(self, name: str) -> str:
        """What the hub adds to a prompt of this instance: its source described, and its result
        when there is one: written by a run here, or by Max's own runner (bachmcp.python), so
        whenever <target>.1 exists. "" when analysis is off."""
        if not self.analysis:
            return ""
        blocks = []
        with self._lock:
            instance = self._get(name)
            has_result, first = instance.has_result, f"{instance.target}.1"
        if not has_result:
            try:
                ShmBuffer(first).close()
                has_result = True
            except (NoShmBuffer, ValueError):
                pass
        for which in ("source", "target") if has_result else ("source",):
            found = self.describe(name, which)
            if found:
                blocks.append(found["text"])
        if not blocks:
            return ""
        return ("[Bach's analysis of the sound, made for you: the user did not write it]\n" + "\n\n".join(blocks))

    def listen(self, name: str, file: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """The listen test of a file not yet loaded: its process on the real source, in the
        instance's worker, described next to the source. Nothing reaches the target or Max.
        {"ok": False, "error", "line"} when it fails; {"ok": True, "skipped": why} with no sound."""
        with self._lock:
            instance = self._get(name)
            instance.stopped, instance.syncing = False, True
            request = {"file": file, "spec": spec, "values": dict(instance.values), "source": instance.source,
                       "scope": instance.settings.scope(),
                       "target": instance.target, "goal": instance.goal, "models": self.models if self.analysis else {}}
        try:
            answer = self._ask(instance, {"listen": request})
        finally:
            with self._lock:
                instance.syncing = False
        if answer is None:
            return {"ok": False, "error": "stopped before it finished (buffer_process_stop)" if instance.stopped
                    else "the worker ended"}
        return answer

    def commit(self, name: str) -> bool:
        """What the last listen made, into the target: said to Max as a run is. False: it is
        not there (said to Max as process_error)."""
        with self._lock:
            instance = self._get(name)
            target = instance.target
            variations = instance.settings.variations
            request = {"source": instance.source, "target": target, "values": dict(instance.values),
                       "scope": instance.settings.scope()}
        if variations > 1:  # the listen test made one: run them all, into the pshmbuffer
            answer = self._run_once(name, instance, request)
            return bool(answer and answer.get("ok"))
        self.send(name, "processing")
        answer = self._ask(instance, {"commit": {"target": target}})
        if not answer or not answer.get("ok"):
            self.send(name, "process_error", (answer or {}).get("error", "the worker ended"))
            return False
        with self._lock:
            instance.has_result = True
        for note in answer.get("warnings") or []:
            self.send(name, "process_note", note)
        self.send(name, "processed", answer["ms"], answer["frames"], answer["channels"], answer["sr"])
        return True

    def run(self, name: str) -> None:
        with self._lock:
            instance = self._get(name)
            instance.wanted = True
            instance.stopped = False
            if instance.thread is None:
                instance.thread = threading.Thread(target=self._loop, args=(name, instance),
                                                   name=f"bach-process-{name}", daemon=True)
                instance.thread.start()

    def stop(self, name: str) -> None:
        """End the run in progress. An idle worker is kept, with what it holds (its loaded
        models, the result of a listen test not yet committed)."""
        with self._lock:
            instance = self._instances.get(name)
            if instance is None:
                return
            instance.wanted = False
            running = instance.thread is not None or instance.syncing
            instance.stopped = running
            worker = instance.worker if running else None
            if running:
                instance.worker = None
        if worker is not None:
            _end(worker)

    def forget(self, name: str) -> None:
        """Stop it and end its worker, busy or not."""
        self.stop(name)
        with self._lock:
            instance = self._instances.pop(name, None)
            worker = instance.worker if instance else None
        if worker is not None:
            _end(worker)

    def close(self) -> None:
        for name in list(self._instances):
            self.forget(name)

    # ── Running ─────────────────────────────────────────────────────── #

    def _loop(self, name: str, instance: _Instance) -> None:
        while True:
            threading.Event().wait(self.settle)
            with self._lock:
                if not instance.wanted:
                    instance.thread = None
                    return
                instance.wanted = False
                request = {"source": instance.source, "target": instance.target, "values": dict(instance.values),
                           "scope": instance.settings.scope()}
            self._run_once(name, instance, request)

    def _run_once(self, name: str, instance: _Instance, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """One run, said to Max; returns the worker's answer (None: stopped or ended)."""
        root = self.playground()
        if not root:
            self.send(name, "process_error", "no playground: the patch sends set_playground <folder>")
            return {"ok": False, "error": "no playground"}
        file = os.path.join(root, "recipes", f"{name}.py")
        if not os.path.exists(file):
            self.send(name, "process_error", f"no recipes/{name}.py yet: prompt {name} for one")
            return {"ok": False, "error": f"no recipes/{name}.py"}
        spec: Dict[str, Any] = {}
        try:
            with open(os.path.join(root, "recipes", f"{name}.json"), encoding="utf-8") as f:
                spec = json.load(f).get("params") or {}
        except (OSError, ValueError):
            pass
        request.update(file=file, spec=spec)
        with self._lock:
            variations = instance.settings.variations
        if variations > 1:
            request["variations"] = variations
        self.send(name, "processing")
        answer = self._ask(instance, {"run": request})
        if answer is None:
            if instance.stopped:
                self.send(name, "process_stopped")
            return None
        if not answer.get("ok"):
            where = f"line {answer['line']}: " if answer.get("line") else ""
            self.send(name, "process_error", where + answer.get("error", "it failed"))
            return answer
        with self._lock:
            instance.has_result = True
        for note in answer.get("warnings") or []:
            self.send(name, "process_note", note)
        if answer.get("variations"):
            self.send(name, "processed_variations", answer["variations"])
        self.send(name, "processed", answer["ms"], answer["frames"], answer["channels"], answer["sr"])
        return answer

    def _ask(self, instance: _Instance, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to the instance's worker (started if needed) and wait for its answer.
        None when the worker ended (stopped, crashed or past the timeout): it is started again next time."""
        with instance.asking:
            return self._ask_now(instance, request)

    def _ask_now(self, instance: _Instance, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            worker = instance.worker
            if worker is None or worker.poll() is not None:
                worker = subprocess.Popen([self.python, WORKER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          text=True, bufsize=1)
                instance.worker, instance.answers = worker, queue.Queue()
                answers = instance.answers
                threading.Thread(target=self._read, args=(worker, answers), daemon=True).start()
            answers = instance.answers
        try:
            worker.stdin.write(json.dumps(request) + "\n")
            worker.stdin.flush()
        except (BrokenPipeError, OSError):
            return None
        try:
            text = answers.get(timeout=self.timeout)
        except queue.Empty:
            _end(worker)
            with self._lock:
                instance.worker = None
            return {"ok": False, "error": f"it did not finish within {self.timeout:.0f} s"}
        if text is None:
            with self._lock:
                if instance.worker is worker:
                    instance.worker = None
            if instance.stopped:
                return None
            return {"ok": False, "error": "the worker ended (a crash in a library?)"}
        try:
            return json.loads(text)
        except ValueError:
            return {"ok": False, "error": f"the worker answered {text[:200]!r}"}

    @staticmethod
    def _read(worker: subprocess.Popen, answers: "queue.Queue[Optional[str]]") -> None:
        try:
            for text in worker.stdout:
                if text.strip():
                    answers.put(text)
        except (OSError, ValueError):
            pass
        finally:
            worker.stdout.close()
            answers.put(None)


__all__ = ["ProcessRunner", "sound_models", "value", "WORKER"]
