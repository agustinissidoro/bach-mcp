"""
status.py
---------
What Bach tells Max about itself, over the same UDP bridge as the tools.

Unasked, Bach sends only two lines, which arrive at [udpreceive 3000]:

    mcp_info status 1   once it has started (the bridge and its door are up)
    mcp_info status 0   its very last message, before it goes off

(and `mcp_info warning "Another bach server is already running"` from a second
Bach, which therefore does not start).

Max asks with one line, sent to [udpsend 127.0.0.1 3001]; Bach answers at once:

Every line is `mcp_info <what it is> <value>`, so the patch routes on the second word.

    bach status     mcp_info status 1
                    mcp_info model <model>             only when a model is loaded and answers
                    mcp_info warning <text>            only when there is something to say (e.g. no model)
    bach settings   mcp_info <section.key> <value>     one per setting, e.g. mcp_info generation.temperature 0.7
                    mcp_info end settings <count>
    bach models     mcp_info models <name> <format> <GB> <in use 1/0>   one per model in models/
                    mcp_info end models <count>
    bach catalog    mcp_info catalog <name> <format> <GB> <downloaded 1/0> <repo> <note>
                        one per model of models/catalog.toml, then: mcp_info end catalog <count>
    bach download_model <name|repo|link> [use]
                    mcp_info download_start <name> <GB>
                    mcp_info download_progress <percent>          every 2 s
                    mcp_info download_done <name>                 (with use: bachmcp.toml now names it)
                    or: mcp_info download_error <message>
    bach download_stop
                    mcp_info download_stopped <name>  (what was fetched stays: the next start goes on)
    bach quit       mcp_info status 0; Bach stops its model server, downloads and page, and exits
    bach help       mcp_info help <the requests>
    bach ping       mcp_info pong

<state> is one of:
    starting   Bach is starting
    no_model   no model is set, or it cannot be found: <message> says what to do
    loading    the model server is loading the model (a first start may download it)
    ready      the local model answers
    stopped    the model server ended: <message> has its last words
    claude     Bach serves Claude, which brings its own model

In the patch, after [udpreceive 3000]: [route mcp_info] -> [print bach], or
[route status model warning models catalog download_progress download_done end].
"""

from __future__ import annotations

import os
import threading
from dataclasses import fields
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..bridge.max import BridgeBusy, MaxBridge
from ..config import Config, ConfigError
from .download import DownloadJob, ModelInfo, in_use, list_models, load_catalog, make_plan, use_in_config

INFO = "mcp_info"
REQUESTS = ("status", "settings", "models", "catalog", "download_model", "download_stop", "quit", "help", "ping")
Word = Union[str, int, float]


class Status:
    """Bach's state, for Max (over UDP) and the chat page."""

    def __init__(self, config: Config, bridge: Any, door: str) -> None:
        self.config = config
        self.bridge = bridge
        self.door = door  # "run", "agent" or "serve"
        self.state = "claude" if door == "serve" else "starting"
        self.model = ""
        self.message = ""
        self.job: Optional[DownloadJob] = None
        self._on_quit: List[Callable[[], None]] = []  # what to stop before exiting, in order
        self._on_change: List[Callable[[], None]] = []  # who shows the state (the hub, for the page)
        self._off_said = False
        self._downloading = threading.Lock()  # one download at a time, from the request to its end

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    def as_dict(self) -> Dict[str, Any]:
        return {"state": self.state, "model": self.model, "message": self.message, "ready": self.ready}

    def set(self, state: str, model: str = "", message: str = "") -> None:
        """Change the state (Max reads it with `bach status`; the page shows it)."""
        self.state, self.message = state, message
        self.model = model or self.model
        for changed in self._on_change:
            changed()

    def on_change(self, changed: Callable[[], None]) -> None:
        """Something to call after every change of the state."""
        self._on_change.append(changed)

    def started(self) -> None:
        """Tell Max that Bach has started: mcp_info status 1."""
        self._say("status", 1)

    def off(self) -> None:
        """Tell Max that Bach goes off: mcp_info status 0, its last message."""
        if not self._off_said:
            self._off_said = True
            self._say("status", 0)

    def warning(self, text: str) -> None:
        """Anything to tell Max that has no category of its own: mcp_info warning <text>."""
        self._say("warning", text)

    def answer(self, request: str) -> None:
        """Answer one `bach <what>` line from the patch."""
        words = request.split()
        what = words[1].strip('"').lower() if len(words) > 1 else "help"
        if what == "status":
            self._say("status", 1)
            if self.ready:
                self._say("model", self.model)  # only a model that is loaded and answers
            if self.message:
                self._say("warning", self.message)
        elif what == "settings":
            rows = settings(self.config)
            for key, value in rows:
                self._say(key, value)
            self._say("end", "settings", len(rows))
        elif what == "models":
            models = list_models()
            for m in models:
                self._say("models", m.name, m.format or "-", round(m.size / 1e9, 1), int(in_use(m, self.config)))
            self._say("end", "models", len(models))
        elif what == "catalog":
            catalog = load_catalog()
            for entry in catalog.values():
                self._say("catalog", entry.name, entry.format, entry.size_gb, int(entry.downloaded()), entry.repo, entry.note)
            self._say("end", "catalog", len(catalog))
        elif what == "download_model":
            if len(words) < 3:
                self._say("download_error", "say what to download: a name from bach catalog, a repo or a link")
                return
            use = any(w.strip('"').lower() == "use" for w in words[3:])
            threading.Thread(target=self.download, args=(words[2].strip('"'), use), daemon=True).start()
        elif what == "download_stop":
            if self._downloading.locked() and self.job is not None:
                self.job.stop()
            else:
                self._say("warning", "no download is running")
        elif what == "quit":
            threading.Thread(target=self.quit, daemon=True).start()  # not on the bridge's own thread
        elif what == "ping":
            self._say("pong")
        elif what == "help":
            self._say("help", *REQUESTS)
        else:
            self._say("warning", f"unknown request {what}: ask one of {', '.join(REQUESTS)}")

    def on_quit(self, stop: Callable[[], None]) -> None:
        """Something to stop when Max says `bach quit` (the model server, the bridge ...)."""
        self._on_quit.append(stop)

    def quit(self) -> None:
        """Stop everything and exit the process, whatever door it is (`bach quit`)."""
        self.set("off")
        if self.job is not None and self.job.running:
            self.job.stop()
        for stop in self._on_quit:  # the page and the model server; the bridge stays for the last word
            try:
                stop()
            except Exception:  # noqa: BLE001 — quitting goes on whatever fails
                pass
        self.off()
        self.bridge.stop()
        os._exit(0)

    def download(self, spec: str, use: bool = False) -> None:
        """Download a model into models/ and report it to Max (on its own thread)."""
        if not self._downloading.acquire(blocking=False):
            running = self.job.plan.name if self.job is not None else "one"
            self._say("warning", f"a download is already running: {running} (bach download_stop ends it)")
            return
        try:
            plan = make_plan(spec)
        except ConfigError as exc:
            self._say("download_error", str(exc))
            self._downloading.release()
            return
        name = plan.name
        gb = lambda n: round(n / 1e9, 2)  # noqa: E731

        def done(info: ModelInfo) -> None:
            self._downloading.release()
            self._say("download_done", name)
            if use:
                self._use(info)

        def error(message: str) -> None:
            self._downloading.release()
            if message == "stopped":
                self._say("download_stopped", name)
            else:
                self._say("download_error", message)

        self.job = DownloadJob(plan, on_progress=lambda d, t: self._say("download_progress", int(100 * d / t) if t else 0),
                               on_done=done, on_error=error)
        self._say("download_start", name, gb(plan.size))
        self.job.start()

    def _use(self, info: ModelInfo) -> None:
        if not os.path.isfile(self.config.source):
            self.warning(f"no bachmcp.toml to set it in: set [model] model = \"{info.name}\" by hand")
            return
        try:
            use_in_config(info, self.config.source)
        except ConfigError as exc:
            self.warning(str(exc))
            return
        self.warning(f"bachmcp.toml now uses {info.name} ({info.format}): restart Bach to load it")

    def _say(self, *words: Word) -> None:
        self.bridge.say(INFO, *atoms(words))


def watch_input(status: Status) -> None:
    """Read what reaches Bach's own input, on a thread. Max's [shell] runs Bach in a terminal of
    its own, and while Bach runs, a second command sent to that [shell] is typed into Bach rather
    than started: a second start therefore arrives here, and Max is warned. `quit` typed there
    stops Bach. Only for `run`: with `serve --stdio` the input is MCP, with `agent` the chat."""
    def read() -> None:
        import sys
        try:
            for line in sys.stdin:
                on_input(status, line)
        except (OSError, ValueError):
            pass  # no input (closed, or none at all)
    threading.Thread(target=read, name="bach-input", daemon=True).start()


def on_input(status: Status, line: str) -> None:
    """One line typed into a running Bach (see watch_input)."""
    text = line.strip()
    if not text:
        return
    if text in ("quit", "bach quit"):
        status.quit()
    elif "main.py" in text or text.split()[0] in ("run", "python", "zsh", "conda", "cd"):
        status.warning(ALREADY_RUNNING)
    else:
        status.warning(f"Bach is running and did not run: {text}")


def atoms(words) -> List[Word]:
    """Words as Max should get them: every word its own atom, so a text arrives without quotes,
    and no commas, semicolons or quotes, which Max would read as separators."""
    out: List[Word] = []
    for word in words:
        if isinstance(word, str):
            out += [w for w in word.translate(_DROP).split() if w]
        else:
            out.append(word)
    return out


_DROP = str.maketrans("", "", ",;\"'")


def settings(config: Config) -> List[Tuple[str, Word]]:
    """Every setting of bachmcp.toml as (section.key, value), and where Bach found the model."""
    rows: List[Tuple[str, Word]] = []
    for section in fields(config):
        if section.name == "source":
            continue
        values = getattr(config, section.name)
        for f in fields(values):
            value = getattr(values, f.name)
            if isinstance(value, bool):
                value = int(value)
            elif isinstance(value, list):
                value = " ".join(map(str, value)) or "-"
            elif value == "":
                value = "-"
            rows.append((f"{section.name}.{f.name}", value))
    rows.append(("model.found", config.model_path if config.model_is_local else "-"))
    rows.append(("model.runtime", config.backend if config.model.model.strip() else "-"))
    rows.append(("server.url", config.url))
    rows.append(("config.file", config.source))
    return rows


ALREADY_RUNNING = "Another bach server is already running"


def start_bridge(config: Config, door: str) -> Tuple[MaxBridge, Status]:
    """The bridge to Max, with Bach's status answering the patch. If another Bach holds the
    port, this one does not go on: it warns Max (sending needs no port of its own) and
    raises BridgeBusy. The one already running keeps going."""
    bridge = MaxBridge(config.max.send_port, config.max.receive_port)
    status = Status(config, bridge, door)
    bridge.on_request(status.answer)
    try:
        bridge.start()
    except BridgeBusy:
        status.warning(ALREADY_RUNNING)
        raise BridgeBusy(f"{ALREADY_RUNNING} (UDP {config.max.receive_port} is taken). "
                         "Stop it first: send `bach quit` from Max, or Ctrl-C where it runs.") from None
    return bridge, status


__all__ = ["Status", "start_bridge", "watch_input", "settings", "INFO", "REQUESTS"]
