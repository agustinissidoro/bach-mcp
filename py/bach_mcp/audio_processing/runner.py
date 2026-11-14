"""
runner.py
---------
Runs the code of buffer instances for the hub (chat/hub.py), offline: the samples Max holds
in one bachmcp.shmbuffer~ go through the instance's process(x, sr, p) and come back in another.
Max never runs Python: it sends lines to the hub, and the hub has this runner.

Each instance has a worker of its own (worker.py), a Python process started at its first run
and kept: imports and models are loaded once, and a crash or an endless loop never reaches the
hub. Its file is the playground's processes/<name>.py, its panel processes/<name>.json.

    run(name)                  run it now (after the last change, see below)
    set_param(name, key, words) a panel change: kept, then a run
    set_source / set_target    which shmbuffers it reads and writes (default <name>-in, <name>-out)
    loaded(name)               a new file: the values set before are dropped, then a run
    stop(name)                 the run in progress ends (its worker is killed)
    forget(name)               stop, and drop everything kept for it

Requests close together become one run: a slider drag runs the code at the last value, not at
every value it passed. What comes out (send: the hub's _send):

    <name> processing
    <name> processed <ms> <frames> <channels> <sr>
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

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py")
TIMEOUT_SECONDS = 600.0
SETTLE_SECONDS = 0.05


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


class ProcessRunner:
    """send: says a line (words); playground: the playground folder now ("" when none)."""

    def __init__(self, send: Callable[..., None], playground: Callable[[], str],
                 python: str = sys.executable, timeout: float = TIMEOUT_SECONDS,
                 settle: float = SETTLE_SECONDS) -> None:
        self.send, self.playground = send, playground
        self.python, self.timeout, self.settle = python, timeout, settle
        self._lock = threading.Lock()
        self._instances: Dict[str, _Instance] = {}

    def _get(self, name: str) -> _Instance:
        """Call with the lock held."""
        if name not in self._instances:
            self._instances[name] = _Instance(f"{name}-in", f"{name}-out")
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

    def loaded(self, name: str) -> None:
        with self._lock:
            self._get(name).values.clear()
        self.run(name)

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
        with self._lock:
            instance = self._instances.get(name)
            if instance is None:
                return
            instance.wanted = False
            running = instance.thread is not None
            instance.stopped = running
            worker, instance.worker = instance.worker, None
        if running and worker is not None:
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
                request = {"source": instance.source, "target": instance.target, "values": dict(instance.values)}
            self._run_once(name, instance, request)

    def _run_once(self, name: str, instance: _Instance, request: Dict[str, Any]) -> None:
        root = self.playground()
        if not root:
            self.send(name, "process_error", "no playground: the patch sends set_playground <folder>")
            return
        file = os.path.join(root, "processes", f"{name}.py")
        if not os.path.exists(file):
            self.send(name, "process_error", f"no processes/{name}.py yet: prompt {name} for one")
            return
        spec: Dict[str, Any] = {}
        try:
            with open(os.path.join(root, "processes", f"{name}.json"), encoding="utf-8") as f:
                spec = json.load(f).get("params") or {}
        except (OSError, ValueError):
            pass
        request.update(file=file, spec=spec)
        self.send(name, "processing")
        answer = self._ask(instance, {"run": request})
        if answer is None:
            if instance.stopped:
                self.send(name, "process_stopped")
            return
        if not answer.get("ok"):
            where = f"line {answer['line']}: " if answer.get("line") else ""
            self.send(name, "process_error", where + answer.get("error", "it failed"))
            return
        for note in answer.get("warnings") or []:
            self.send(name, "process_note", note)
        self.send(name, "processed", answer["ms"], answer["frames"], answer["channels"], answer["sr"])

    def _ask(self, instance: _Instance, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to the instance's worker (started if needed) and wait for its answer.
        None when the worker ended (stopped, crashed or past the timeout): it is started again next time."""
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


__all__ = ["ProcessRunner", "value", "WORKER"]
