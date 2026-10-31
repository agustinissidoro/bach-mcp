"""
web.py
------
`run`: the local model, the hub and the chat page. One Bach process, one port ([server]):

    /               the chat page (page.html): in a browser, or in Max's [jweb]
    /api/line       POST one line, the same as Max sends over UDP (hub.py), as the body
    /api/events     every line the hub sends, as a stream of server-sent events; a page
                    first gets what it needs to show the present (Hub.snapshot)
    /api/state      Bach's state (status.py): no_model, loading, ready ... (the page's heartbeat)

run() starts the bridge to Max, the hub and the model server (model/backends.py),
serves the page, opens it in the browser once the model is ready, and stops
everything on Ctrl-C, a signal or `bach quit`. Without a model it still runs: the
page and Max (bach status) say what is missing. Claude has no way in here: it
works with `serve` (bachmcp.server claude), which loads no model.
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from typing import Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .. import claude
from ..config import Config, ConfigError
from ..model.backends import ModelServer
from ..model.client import ModelClient
from ..utilities.status import Status, quit_on_signals, start_bridge, watch_input
from .engine import build_conversation
from .hub import Hub, Message

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.html")
KEEPALIVE_SECONDS = 15.0


def event(text: str) -> bytes:
    """One line as a server-sent event: a line with newlines in it (an answer) takes several data: rows."""
    return ("".join(f"data: {row}\n" for row in text.split("\n")) + "\n").encode("utf-8")


def create_app(hub: Hub, status: Status) -> Starlette:
    """The chat page and the two ends of the hub."""

    async def page(request: Request) -> Response:
        with open(PAGE, encoding="utf-8") as f:
            return HTMLResponse(f.read(), headers={"Cache-Control": "no-cache"})

    async def get_state(request: Request) -> JSONResponse:
        return JSONResponse(status.as_dict())

    async def post_line(request: Request) -> JSONResponse:
        text = (await request.body()).decode("utf-8", errors="replace").strip()
        if not text:
            return JSONResponse({"error": "empty line"}, status_code=400)
        if not hub.handle(text, "web"):
            return JSONResponse({"error": f"unknown command: {text[:80]}"}, status_code=400)
        return JSONResponse({"ok": True})

    async def events(request: Request) -> Response:
        loop = asyncio.get_running_loop()
        lines: "asyncio.Queue[str]" = asyncio.Queue()

        def client(message: Message) -> None:  # called from the hub's threads
            loop.call_soon_threadsafe(lines.put_nowait, message.text)

        stop = hub.subscribe(client)
        first = hub.snapshot()

        async def stream() -> AsyncIterator[bytes]:
            try:
                for text in first:
                    yield event(text)
                while True:
                    try:
                        text = await asyncio.wait_for(lines.get(), KEEPALIVE_SECONDS)
                    except asyncio.TimeoutError:
                        yield b": keepalive\n\n"
                        continue
                    yield event(text)
            finally:
                stop()

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    routes = [Route("/", page), Route("/api/state", get_state), Route("/api/events", events),
              Route("/api/line", post_line, methods=["POST"])]
    return Starlette(routes=routes)


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) != 0


def close_page_tabs(url: str) -> None:
    """Close the browser tabs that show the chat page (Chrome, Safari), as Bach goes off. A page
    cannot close a tab it did not open itself, so this asks the browsers; macOS asks once whether
    Python may control them. Browsers that are not running are left alone."""
    if sys.platform != "darwin":
        return
    for app in ("Google Chrome", "Safari"):
        script = (f'if application "{app}" is running then tell application "{app}" to '
                  f'close (every tab of every window whose URL starts with "{url}")')
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def run(config: Config) -> None:
    """Start the bridge to Max, the model and the chat page; open the page when the model is ready.
    Max hears server status 1 once the page is up, and status 0 as Bach goes off."""
    import uvicorn

    bridge, status = start_bridge(config, "run")  # stops here if another Bach is running
    quit_on_signals(status)
    if not _port_free(config.server.host, config.server.port):
        bridge.stop()
        raise ConfigError(f"[server] port {config.server.port} is in use by another program")
    print(f"Bach — config: {config.source}")
    server: Optional[ModelServer] = None
    try:
        mcp = claude.mcp_app(config, bridge)
        make = None
        try:
            server = ModelServer(config)  # checks [model]
        except ConfigError as exc:
            status.set("no_model", message=str(exc))
            print(f"  model     {exc}")
        if server is not None:
            status.set("loading", model=server.label)
            print(f"  model     {server.label}: loading (log: logs/model-server.log)")
            server.start()
            status.on_quit(server.stop)
            client = ModelClient(server.base_url, config.generation, server.request_model)
            make = lambda kind: build_conversation(config, client, mcp, kind)  # noqa: E731
        print(f"  docs      {'added to messages that name an instrument' if config.chat.docs else 'off'}")
        print(f"  max       answers bach status|settings|models|catalog|download_model|quit|help on UDP {config.max.receive_port}")
        hub = Hub(bridge, status, make)
        status.on_quit(hub.close)

        def when_ready() -> None:
            if server is not None:
                try:
                    server.wait_ready()
                except RuntimeError as exc:
                    status.set("stopped", message=str(exc).splitlines()[0])
                    print(f"\n{exc}", flush=True)
                    return
                status.set("ready", model=server.label)
                print(f"\nReady. Chat: {config.url}   (Ctrl-C here stops everything)\n", flush=True)
            if config.chat.open_browser:
                webbrowser.open(config.url)

        http = uvicorn.Server(uvicorn.Config(create_app(hub, status), host=config.server.host,
                                             port=config.server.port, log_level="warning",
                                             timeout_graceful_shutdown=1))  # the pages' streams never end

        def when_started() -> None:
            while not http.started and not http.should_exit:
                time.sleep(0.05)
            if http.started:
                status.started()
                when_ready()

        status.on_quit(lambda: close_page_tabs(config.url))
        threading.Thread(target=when_started, daemon=True).start()
        watch_input(status)  # a second start through the same [shell] arrives here
        http.run()
    finally:
        if server is not None:
            server.stop()
        close_page_tabs(config.url)
        status.off()
        bridge.stop()
        print("Stopped.")


__all__ = ["create_app", "run"]
