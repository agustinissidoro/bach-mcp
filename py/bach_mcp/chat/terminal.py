"""
terminal.py
-----------
`agent`: the local model and the hub, in the terminal. What is typed is a line
for the hub, the same as Max sends (hub.py), and every line the hub sends is
printed: the answer as it is written, the rest as it comes.

    set_playground ~/bach-playground
    add_instance_names_map scales1 generator
    scales1 prompt a scale that turns around

It starts its own model server and bridge, so it cannot run beside `run` (they
would share the patch's port). The patch, if open, sends its map as usual.
"""

from __future__ import annotations

import sys

from ..config import Config, ConfigError
from ..model.backends import ModelServer
from ..model.client import ModelClient
from ..tools.registry import create_tools
from ..utilities.status import start_bridge
from .engine import build_conversation
from .hub import Hub, Message

DIM, RESET = ("\033[2m", "\033[0m") if sys.stdout.isatty() else ("", "")


class Printer:
    """Prints the hub's lines: pieces of an answer or of reasoning run on, the rest one per line."""

    def __init__(self) -> None:
        self.running = ""  # "delta" or "reasoning" while one is being printed

    def __call__(self, message: Message) -> None:
        said = message.words
        what = said[1] if len(said) > 1 else ""
        if what in ("delta", "reasoning") and len(said) > 2:
            if self.running != what:
                self._end()
                print(f"{DIM}{said[0]} thinking: " if what == "reasoning" else f"{said[0]}: ", end="")
                self.running = what
            print(said[2], end="", flush=True)
            return
        if what in ("answer", "tool_result", "history") or said[0] == "state":
            return  # already printed as it came, or only for the page
        self._end()
        if what == "tool_call":
            print(f"  {said[0]} calls {said[2]}")
        else:
            print(f"  {message.text}")

    def _end(self) -> None:
        if self.running:
            print(RESET if self.running == "reasoning" else "")
            self.running = ""


def run(config: Config) -> None:
    bridge, status = start_bridge(config, "agent")
    server = None
    try:
        try:
            server = ModelServer(config)
        except ConfigError as exc:
            status.set("no_model", message=str(exc))
            raise
        status.set("loading", model=server.label)
        print(f"  model     {server.label}: loading (log: logs/model-server.log)")
        server.start()
        status.on_quit(server.stop)
        server.wait_ready()
        status.set("ready")
        status.started()
        client = ModelClient(server.base_url, config.generation, server.request_model)
        app = create_tools(bridge, config.algo.node, config.server.tool_log)
        hub = Hub(bridge, status, lambda kind: build_conversation(config, client, app, kind))
        hub.subscribe(Printer())
        print(f"\nBach — {server.label}. Type lines as Max sends them, e.g.\n"
              "  set_playground ~/bach-playground\n  add_instance_names_map scales1 generator\n"
              "  scales1 prompt a scale that turns around\nCtrl-C to quit.\n")
        while True:
            try:
                text = input().strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                return
            if text and not hub.handle(text, "terminal"):
                print(f"  not a command: {text}")
    finally:
        if server is not None:
            server.stop()
        status.off()
        bridge.stop()


__all__ = ["run", "Printer"]
