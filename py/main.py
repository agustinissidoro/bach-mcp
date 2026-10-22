"""Single entrypoint for Bach. Everything is configured in bach.toml.

    run                Start the whole local setup: the MCP server, llama-server
                       with the model from bach.toml, and the llama.cpp web chat
                       already wired to both (system prompt, tools, limits).
                       This is what run.command launches.

    serve  (default)   Only the MCP server, for an MCP host you start yourself
                       (Claude Desktop, another web UI). HTTP by default; pass
                       --stdio for the subprocess transport.

    agent              Terminal chat against any OpenAI-compatible endpoint
                       (by default the llama-server of bach.toml). This process
                       owns the tool loop. Useful for testing without a browser.

Usage:
    python main.py run                   # everything, then open the chat
    python main.py serve                 # MCP server at the [mcp] host/port of bach.toml
    python main.py serve --stdio         # MCP over stdio (the host launches this process)
    python main.py agent                 # terminal chat
    python main.py run --config other.toml
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser

from bach_mcp import (
    Agent,
    AgentConfig,
    BachMCPServer,
    McpToolBridge,
    MCPConfig,
    ProviderConfig,
    build_provider,
    create_mcp_app,
)
from bach_mcp.config import REPO_ROOT, BachConfig, ConfigError, load_config
from bach_mcp.docs import DocLibrary
from bach_mcp.modes import DEFAULT_MODE, split_prefix, tools_for

LLAMA_LOG = os.path.join(REPO_ROOT, "logs", "llama-server.log")


def _start_bach(config: BachConfig) -> BachMCPServer:
    config.apply_env()
    bach = BachMCPServer(MCPConfig(
        incoming_port=config.max.receive_port,
        outgoing_port=config.max.send_port,
    ))
    bach.start()
    return bach


def _serve_http(bach: BachMCPServer, config: BachConfig) -> None:
    """Serve the MCP app over streamable HTTP until interrupted.

    The Starlette app is wrapped in CORS middleware: browser-based MCP clients
    (the llama.cpp web chat) make cross-origin fetches and are blocked without
    these headers. Mcp-Session-Id must be exposed so the browser can read the
    session id the transport returns and complete the handshake.
    """
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    mcp = create_mcp_app(bach, config.mcp.toolset, instructions=config.system_prompt())

    @mcp.resource("bach://skill")
    def bach_skill() -> str:
        """Bach MCP skill — how to compose with the tools of this server."""
        return config.system_prompt()

    mcp.settings.host = config.mcp.host
    mcp.settings.port = config.mcp.port
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )
    uvicorn.run(app, host=config.mcp.host, port=config.mcp.port, log_level="warning")


def run_serve(config: BachConfig, stdio: bool = False) -> None:
    """Run only the MCP server, for an external MCP host."""
    bach = _start_bach(config)
    try:
        if stdio:
            mcp = create_mcp_app(bach, config.mcp.toolset, instructions=config.system_prompt())
            mcp.run(transport="stdio")
        else:
            print(f"Bach MCP server listening at {config.mcp_url}", flush=True)
            _serve_http(bach, config)
    finally:
        bach.stop()


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _tail(path: str, lines: int = 15) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError:
        return ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ollama_is_up(config: BachConfig) -> bool:
    try:
        with urllib.request.urlopen(f"{config.ollama.url}/api/version", timeout=2):
            return True
    except OSError:
        return False


def _ensure_ollama(config: BachConfig):
    """Start Ollama if it is not running. Returns the process we started, if any.

    The Ollama app is preferred (it stays in the menu bar and is left running on
    exit, as if the user had opened it). Without the app, `ollama serve` is run
    as a child process and stopped again when Bach exits.
    """
    if _ollama_is_up(config) or not config.ollama.autostart:
        return None
    print("  ollama    not running, starting it", end="", flush=True)
    process = None
    opened = sys.platform == "darwin" and subprocess.run(
        ["open", "-g", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not opened:
        binary = shutil.which("ollama")
        if not binary:
            print()
            raise ConfigError("Ollama is not running and could not be started: neither the Ollama app "
                              "nor the `ollama` command was found.")
        process = subprocess.Popen([binary, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if _ollama_is_up(config):
            print(" ... ready")
            return process
        if process is not None and process.poll() is not None:
            break
        print(".", end="", flush=True)
        time.sleep(0.5)
    print()
    if process is not None and process.poll() is None:
        process.terminate()
    raise ConfigError(f"Ollama was started but did not answer at {config.ollama.url} within 30 seconds.")


def _ollama_capabilities(config: BachConfig) -> list:
    """Check that Ollama is up and has the model; return the model's capabilities."""
    request = urllib.request.Request(
        f"{config.ollama.url}/api/show",
        data=json.dumps({"model": config.model.ollama_model}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response).get("capabilities", [])
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ConfigError(
                f"Ollama has no model \"{config.model.ollama_model}\". Check `ollama list`, "
                f"or get it with `ollama pull {config.model.ollama_model}`."
            ) from None
        raise ConfigError(f"Ollama answered with an error ({exc.code}) at {config.ollama.url}.") from None
    except OSError:
        raise ConfigError(f"Cannot reach Ollama at {config.ollama.url}. Open the Ollama app, "
                          "or set autostart = true in [ollama].") from None


def run_all(config: BachConfig) -> None:
    """Start the MCP server, the model server and the web chat, wired together."""
    binary = shutil.which(config.llama.binary)
    if not binary:
        raise ConfigError(f"[llama] binary \"{config.llama.binary}\" was not found. Install llama.cpp or set its full path.")
    for label, host, port in (("[mcp]", config.mcp.host, config.mcp.port),
                              ("[llama]", config.llama.host, config.llama.port)):
        if _port_in_use(host, port):
            raise ConfigError(f"{label} port {port} is already in use. Stop the other program or change the port.")

    print(f"Bach — config: {config.source}")
    ollama_process = _ensure_ollama(config) if config.uses_ollama else None
    try:
        capabilities = _ollama_capabilities(config) if config.uses_ollama else []
        if config.uses_ollama and "tools" not in capabilities:
            raise ConfigError(f"The Ollama model \"{config.model.ollama_model}\" does not support tool calling.")
        _run_stack(config, capabilities)
    finally:
        if ollama_process is not None and ollama_process.poll() is None:
            ollama_process.terminate()


def _run_stack(config: BachConfig, capabilities: list) -> None:
    if config.has_model:
        print(f"  model     {config.model_label}")
    else:
        print("  model     NOT SET in [model]: llama-server starts without one.\n"
              "            Set path or hf_repo in bach.toml; context and reasoning settings need it.")
    print(f"  context   {config.model.context_size} tokens, reply limit {config.generation.max_tokens}, "
          f"reasoning {config.generation.reasoning}")
    print(f"  tools     {config.mcp.toolset} set at {config.mcp_url}")

    ui_file = tempfile.NamedTemporaryFile("w", suffix=".json", prefix="bach-webui-", delete=False, encoding="utf-8")
    json.dump(config.webui_settings(), ui_file)
    ui_file.close()

    os.makedirs(os.path.dirname(LLAMA_LOG), exist_ok=True)
    log = open(LLAMA_LOG, "w", encoding="utf-8")
    # The gateway always holds the chat port; llama-server runs behind it on an internal port.
    import uvicorn
    from bach_mcp.gateway import create_gateway_app, create_llama_gateway_app

    internal_port = _free_port()
    internal = f"http://127.0.0.1:{internal_port}"
    if config.uses_ollama:
        # llama-server runs without a model, only to provide the web chat's files;
        # the gateway answers for it and talks to Ollama.
        llama = subprocess.Popen(config.llama_ui_args(internal_port), stdout=log, stderr=subprocess.STDOUT)
        gateway_app = create_gateway_app(config, internal, capabilities)
        print("  chat      llama.cpp web chat through the Ollama gateway")
    else:
        llama = subprocess.Popen(config.llama_args(ui_file.name, internal_port), stdout=log, stderr=subprocess.STDOUT)
        gateway_app = create_llama_gateway_app(config, internal)
        print(f"  llama     starting (log: {os.path.relpath(LLAMA_LOG, REPO_ROOT)})")
    gateway = uvicorn.Server(uvicorn.Config(
        gateway_app, host=config.llama.host, port=config.llama.port, log_level="warning",
    ))
    threading.Thread(target=gateway.run, daemon=True).start()
    print(f"  docs      {'added to messages that name an instrument' if config.chat.docs else 'off'}")

    def announce_when_ready() -> None:
        # With Ollama the gateway answers at once; wait for the chat page itself,
        # which comes from the model-less llama-server behind it.
        url = f"{config.chat_url}/" if config.uses_ollama else f"{config.chat_url}/health"
        started = time.time()
        while llama.poll() is None:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            if time.time() - started > 900:
                print("\nllama-server is still not ready after 15 minutes; see the log.")
                return
            time.sleep(1)
        else:
            print(f"\nllama-server stopped (exit code {llama.returncode}). Last lines of its log:\n{_tail(LLAMA_LOG)}")
            os._exit(1)
        print(f"\nReady. Chat: {config.chat_url}   (Ctrl-C here stops everything)\n", flush=True)
        if config.chat.open_browser:
            webbrowser.open(config.chat_url)

    threading.Thread(target=announce_when_ready, daemon=True).start()

    bach = _start_bach(config)
    try:
        _serve_http(bach, config)
    finally:
        bach.stop()
        if llama.poll() is None:
            llama.terminate()
            try:
                llama.wait(timeout=10)
            except subprocess.TimeoutExpired:
                llama.kill()
        log.close()
        try:
            os.unlink(ui_file.name)
        except OSError:
            pass
        print("Stopped.")


def run_agent(config: BachConfig) -> None:
    """Terminal chat against an OpenAI-compatible endpoint.

    Uses the llama-server of bach.toml unless BACH_LLM_BASE_URL points elsewhere
    (then all BACH_LLM_* variables apply, see ProviderConfig).
    """
    if os.getenv("BACH_LLM_BASE_URL"):
        provider_cfg = ProviderConfig.from_env()
    else:
        provider_cfg = ProviderConfig(
            base_url=f"{config.ollama.url}/v1" if config.uses_ollama else f"{config.chat_url}/v1",
            model=config.model.ollama_model if config.uses_ollama else config.model.alias,
            temperature=config.generation.temperature,
            max_tokens=config.generation.max_tokens,
            sampling={"top_p": config.generation.top_p, "top_k": config.generation.top_k,
                      "presence_penalty": config.generation.presence_penalty},
        )
    provider = build_provider(provider_cfg)

    bach = _start_bach(config)
    mcp = create_mcp_app(bach, config.mcp.toolset)
    tools = McpToolBridge(mcp)
    agent = Agent(provider, tools, AgentConfig(
        system_prompt=config.system_prompt(DEFAULT_MODE),
        max_tool_rounds=config.chat.max_tool_rounds,
    ))
    all_tools = list(agent.tool_specs)

    def enter(mode: str) -> None:
        agent.set_mode(config.system_prompt(mode), tools_for(all_tools, mode, name_of=lambda t: t.name))

    enter(DEFAULT_MODE)

    # This process talks to the model directly, so it adds the docs itself.
    library = DocLibrary() if config.chat.docs else None
    seen_docs: set = set()

    print(f"\nBach — {provider_cfg.provider}:{provider_cfg.model} @ {provider_cfg.base_url}")
    print(f"Mode {DEFAULT_MODE}: {len(agent.tool_specs)} tools. Start a message with /algo or /score to switch.")
    print("Type a message and press Enter. Ctrl-C to quit.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                break
            if not user_input:
                continue
            mode, rest = split_prefix(user_input)
            if mode:
                enter(mode)
                print(f"  mode      {mode} ({len(agent.tool_specs)} tools)")
                if rest == user_input:  # only the prefix: switch, send nothing
                    continue
                user_input = rest
            if library is not None:
                user_input, added = library.augment_text(user_input, seen_docs)
                if added:
                    print(f"  docs      {', '.join(added)}")
            try:
                reply = agent.chat(user_input)
                print(f"\nBach: {reply}\n")
            except RuntimeError as exc:
                print(f"[Error] {exc}")
    finally:
        tools.close()
        bach.stop()


def main() -> None:
    parser = argparse.ArgumentParser(prog="bach", description="Bridge bach.roll in Max to an LLM.")
    parser.add_argument(
        "mode",
        nargs="?",
        default="serve",
        choices=["run", "serve", "agent", "eval"],
        help="run = MCP server + llama-server + web chat. serve = MCP server only (default). "
             "agent = terminal chat. eval = the evaluation suite against the model.",
    )
    parser.add_argument("--config", default="", help="path to the config file (default: bach.toml in the repo root).")
    parser.add_argument("--stdio", action="store_true", help="serve over stdio instead of HTTP.")
    parser.add_argument("--runs", type=int, default=5, help="eval: runs per case (default 5).")
    parser.add_argument("--case", default="", help="eval: only these cases, comma-separated "
                        "(neapolitan, trio, spiral, microtonal, algo).")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    try:
        config = load_config(args.config)
        if args.mode == "run":
            run_all(config)
        elif args.mode == "agent":
            run_agent(config)
        elif args.mode == "eval":
            from bach_mcp.evaluate import run_suite
            run_suite(config, runs=args.runs, only=[c.strip() for c in args.case.split(",") if c.strip()])
        else:
            run_serve(config, stdio=args.stdio)
    except ConfigError as exc:
        sys.exit(f"Configuration problem: {exc}")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
