# bach-mcp

`bach-mcp` bridges `bach.roll` in Max with AI in two modes:

1. Claude mode: Claude Desktop <-> MCP (`py/main.py`) <-> Max
2. Local mode: Ollama + Qwen (`py/main_local.py`) <-> Max

## Dependency note

Use `requirements.txt` (generated from `requirements.in`).

- Do use: `requirements.txt`
- Source file: `requirements.in`
- Do not use: `pip_requirements.txt` (it is not part of this repo)

## File map (what each file is for)

### Root files

- `README.md`: setup and usage.
- `environment.yml`: Conda env definition (Python 3.11).
- `requirements.in`: direct Python dependencies (`mcp`, `requests`).
- `requirements.txt`: pinned, compiled dependency lock for pip install.
- `claude_desktop_config.json`: example Claude Desktop MCP server config (edit absolute paths).
- `.gitignore`: excludes cache/build/local artifacts (including `.DS_Store` and `__pycache__`).
- `.gitattributes`: Git text normalization.

### Python entrypoints

- `py/main.py`: starts `BachMCPServer`, creates FastMCP app, runs MCP over stdio for Claude Desktop.
- `py/main_local.py`: local terminal REPL mode using Ollama/Qwen.

### Python package (`py/bach_mcp`)

- `py/bach_mcp/__init__.py`: public exports.
- `py/bach_mcp/server.py`: high-level bridge server (message queue, send/wait helpers, lifecycle).
- `py/bach_mcp/tcp.py`: low-level TCP server/client classes (`3001` inbound, `3000` outbound).
- `py/bach_mcp/mcp_app.py`: Claude-facing FastMCP tool registration (46 tools).
- `py/bach_mcp/ollama_bridge.py`: Ollama chat client + tool-calling loop + tool executor.
- `py/bach_mcp/ollama_utils.py`: Ollama startup, model discovery, model selection/pull menus.
- `py/bach_mcp/tool_registry.py`: local tool schemas for Qwen (`core` and `extended` sets).

### Max package files

- `max/bach-mcp/patchers/bach-mcp.maxpat`: patcher containing `bach.roll`, `bach.portal`, and `node.script`.
- `max/bach-mcp/js/bachTCP.js`: Node for Max TCP bridge.
  - Max listens on `0.0.0.0:3000` for Python commands.
  - Max client connects to Python on `127.0.0.1:3001` for replies/events.

### Generated/non-source artifacts

- `.DS_Store`, `__pycache__/`, `*.pyc`: generated files, not part of runtime logic.

## Setup (shared by both modes)

1. Clone:

```bash
git clone https://github.com/agustinissidoro/bach-mcp.git
cd bach-mcp
```

2. Create/activate environment:

```bash
conda env create -f environment.yml
conda activate bach-mcp
```

3. Install Python dependencies from `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

4. Install Max package:
copy `max/bach-mcp` into Max Packages.

- macOS default: `~/Documents/Max 9/Packages/`
- Windows default: `%USERPROFILE%\Documents\Max 9\Packages\`

5. In Max, open `max/bach-mcp/patchers/bach-mcp.maxpat` and start the Node script (`script start`).

## Mode 1: Claude mode (MCP)

1. Install Claude Desktop: `https://claude.ai/download`
2. Point Claude Desktop to this MCP server.

Claude config file locations:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Example:

```json
{
  "mcpServers": {
    "bach-mcp": {
      "command": "/absolute/path/to/python",
      "args": ["/absolute/path/to/bach-mcp/py/main.py"],
      "cwd": "/absolute/path/to/bach-mcp"
    }
  }
}
```

Then fully restart Claude Desktop.

## Mode 2: Local mode (Ollama + Qwen)

1. Install Ollama: `https://ollama.com`
2. Start local mode:

```bash
python py/main_local.py
```

What happens:

- Ensures Ollama is running (starts `ollama serve` if needed).
- Shows an interactive model picker (installed models).
- If no models exist, offers pull/download from known Qwen tags.
- Starts a terminal chat loop and routes tool calls to Max through the same TCP bridge.
- Uses the `core` tool tier by default in this entrypoint (`BridgeConfig.extended_tools=False`).

Optional for larger local models (32B/72B):

```bash
python py/bach_mcp/ollama_bridge.py
```

That REPL auto-enables `extended` tools for 32B/72B tags.

## Ollama + Qwen implementation details

Local mode uses these components:

1. Model lifecycle (`py/bach_mcp/ollama_utils.py`)
- `QWEN_MODELS` defines known Qwen tags and preference order.
- `ensure_ollama_running()` checks `/api/tags` and starts Ollama when needed.
- `select_model()` displays installed models and supports pulling new ones.

2. Bridge config (`py/bach_mcp/ollama_bridge.py`)
- `BridgeConfig` defines model, fallback models, temperature, token limits, TCP ports, and tool tier.
- Default transport is the same as Claude mode: outgoing `3000`, incoming `3001`.

3. Tool-calling loop (`py/bach_mcp/ollama_bridge.py`)
- `OllamaClient.chat()` calls Ollama `/api/chat` with `tools`.
- `OllamaBridge._run_tool_loop()` executes iterative tool rounds (up to `max_tool_rounds`).
- On missing model, it can switch to installed fallback models from the configured list.

4. Tool execution (`py/bach_mcp/ollama_bridge.py` + `py/bach_mcp/tool_registry.py`)
- `tool_registry.py` defines two local tool sets:
  - Core: 12 tools (default, best for smaller models)
  - Extended: 46 tools total (core + advanced)
- `ToolExecutor` maps called tool names to Max commands via `BachMCPServer`.

5. Shared Max transport (`py/bach_mcp/server.py` + `py/bach_mcp/tcp.py`)
- Same transport stack for both modes.
- Commands go to Max on port `3000`; responses/events come back on `3001`.

## Optional: regenerate `requirements.txt`

If you change `requirements.in`, rebuild the lock file with pip-tools:

```bash
pip-compile --output-file=requirements.txt requirements.in
```
