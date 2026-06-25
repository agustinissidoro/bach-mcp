# bach-mcp

`bach-mcp` bridges `bach.roll` in Max with an LLM. There is **one entrypoint**,
`py/main.py`, with two roles:

- **`serve`** (default) — an MCP server for MCP host apps such as Claude Desktop.
  The host owns the model and the agent loop; bach-mcp only exposes the
  `bach.roll` tools and waits to be driven. Serves over **HTTP by default**
  (`--stdio` switches to the subprocess transport).
- **`agent`** — a self-hosted agent that drives any OpenAI-compatible LLM endpoint
  itself (Ollama, llama.cpp, vLLM, OpenAI, …) and calls the same tools in-process.

Both roles share one tool definition (`py/bach_mcp/mcp_app.py`) and one system
prompt/skill (`py/bach_mcp/BACH_SKILL.md`).

## Quick start

**1. Install** (Python 3.11):

```bash
git clone https://github.com/agustinissidoro/bach-mcp.git
cd bach-mcp
conda env create -f environment.yml
conda activate bach-mcp
python -m pip install -r requirements.txt
```

**2. Set up Max** — copy the `max/bach-mcp` folder into your Max Packages folder,
open the patcher, and start the Node bridge:

- macOS: `~/Documents/Max 9/Packages/`
- Windows: `%USERPROFILE%\Documents\Max 9\Packages\`

Then open `max/bach-mcp/patchers/bach-mcp.maxpat` and run `script start` in the
patch.

**3. Run one of the two roles:**

```bash
# A) Drive it from an MCP host (Claude Desktop, etc.) — the host owns the model.
python py/main.py                 # serves over HTTP at http://127.0.0.1:8000/mcp
                                  # (for Claude Desktop, register it for stdio — see below)

# B) Self-hosted agent against a local LLM.
ollama serve                      # any OpenAI-compatible backend
ollama pull qwen3:8b
python py/main.py agent
```

That's it. The sections below explain how to choose between the two roles and
configure each.

## serve vs agent — how they differ and when to use each

`serve` and `agent` are not two copies of the same server — they are two
different *roles* that share the same core. The difference is **who runs the
model and the agent loop**.

- `serve` is *only the tools*. It speaks MCP (JSON-RPC) — over HTTP by default,
  or stdio with `--stdio` — and waits to be driven. It contains no model and no
  loop: an external **MCP host** (Claude Desktop, or another MCP-capable client)
  supplies those, connects to (or launches) this process, runs the model, and
  decides when to call the tools.
- `agent` is *the whole thing in one process*: tools + agent loop + LLM client.
  It exists because a bare inference endpoint (raw `ollama serve`, raw
  `llama-server`) is **not** an MCP host — it cannot launch a tool server or run
  a loop. So `agent` becomes the host itself and talks to that endpoint over the
  OpenAI-compatible HTTP API.

The distinction is **not** "Claude vs local"; it is "is there already an MCP host
to drive things, or do I need to be that host?". (Once an Anthropic provider is
added, `agent` will drive Claude-the-cloud-model too.)

| You have…                                            | Use     | Who picks the model           |
|------------------------------------------------------|---------|-------------------------------|
| Claude Desktop / any app that "adds an MCP server"   | `serve` | the host app                  |
| Raw Ollama / llama.cpp / vLLM / OpenAI API (no host) | `agent` | `BACH_LLM_MODEL` (see note)    |

Note on `BACH_LLM_MODEL`: in `agent` mode this process is the host, and the
OpenAI API requires a `model` field in every request. For multi-model endpoints
(Ollama, OpenAI, vLLM) it selects the model. For `llama.cpp`'s `llama-server`,
the model is chosen at launch (`-m model.gguf`) and the request field is ignored,
so the value is cosmetic there.

## Role: `serve` — MCP host apps (e.g. Claude Desktop)

`serve` is *just the tools*: it holds the TCP connection to Max and waits for an
MCP host to drive it. The **transport** only changes how the host reaches those
tools, not what they do. There are two:

### HTTP vs stdio — which transport to use

**HTTP (default)** — *you* run a standalone, long-lived server; clients connect
to a URL.

- Run it once; it keeps **one stable connection to Max** while clients come and
  go. Nothing bounces when you restart the client — handy while you're patching
  in Max.
- Supports **multiple / repeat clients** against one running server.
- **Remote / cross-machine**: bind `--host 0.0.0.0` and connect over the network
  (also the natural fit for a tunneled setup).
- Easy to **debug** with curl or the MCP Inspector against a fixed URL, and works
  with HTTP-only MCP clients and containers.

**stdio (`--stdio`)** — the host *launches and owns* the server process.

- Claude Desktop (or another local MCP host) spawns `py/main.py` as a child
  process and talks over its stdin/stdout. You configure it once and never start
  it by hand.
- Single client, single process, same machine, **nothing on the network** — the
  simplest, most locked-down option for a local Max + Claude Desktop setup.
- Each host launch is a fresh process opening a fresh connection to Max; you
  can't share one server across clients or poke it with curl.

### HTTP (default)

Start the server yourself:

```bash
python py/main.py                       # 127.0.0.1:8000/mcp
python py/main.py serve --host 0.0.0.0 --port 9000   # bind for remote clients
```

It prints the URL it's listening on (default `http://127.0.0.1:8000/mcp`). Point
any HTTP-capable MCP client at that URL. The server stays up until you stop it
(Ctrl-C), holding its connection to Max across client reconnects.

### stdio (Claude Desktop / subprocess hosts)

Here the host launches the process for you, so you do **not** start it by hand —
you just register it in the host's config.

1. Install Claude Desktop: `https://claude.ai/download`
2. Point Claude Desktop to this MCP server.

Claude config file locations:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Example (`claude_desktop_config.json` in this repo is a copy of this — edit the
absolute paths to match your machine):

```json
{
  "mcpServers": {
    "bach-mcp": {
      "command": "/absolute/path/to/conda/envs/bach-mcp/bin/python",
      "args": ["/absolute/path/to/bach-mcp/py/main.py", "serve", "--stdio"],
      "cwd": "/absolute/path/to/bach-mcp"
    }
  }
}
```

The `--stdio` flag is **required** here: the default transport is HTTP, so
without it the launched process would start an HTTP listener the host can't talk
to over the pipe.

Then fully restart Claude Desktop.

## Role: `agent` — self-hosted (any OpenAI-compatible provider)

The local agent works with any backend that exposes an OpenAI-compatible
`/v1/chat/completions` endpoint with tool calling. Defaults target a local
Ollama.

1. Start a backend, e.g. Ollama (`https://ollama.com`):

```bash
ollama serve
ollama pull qwen3:8b   # or any tool-capable model
```

2. Start the agent:

```bash
python py/main.py agent
```

Configuration is entirely via environment variables (all optional):

| Variable | Default | Notes |
|---|---|---|
| `BACH_LLM_PROVIDER` | `openai` | `openai` (covers Ollama/llama.cpp/vLLM/OpenAI); `anthropic` reserved (not yet implemented). |
| `BACH_LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible base, **including** the version segment. |
| `BACH_LLM_MODEL` | `qwen3:8b` | Model tag/name. |
| `BACH_LLM_API_KEY` | _(none)_ | Bearer token if the server needs one. Falls back to `OPENAI_API_KEY`. |
| `BACH_LLM_TEMPERATURE` / `BACH_LLM_MAX_TOKENS` / `BACH_LLM_TIMEOUT` | `0.35` / `2048` / `300` | |

Examples:

```bash
# Local llama.cpp server
BACH_LLM_BASE_URL=http://localhost:8080/v1 BACH_LLM_MODEL=qwen2.5-7b-instruct \
  python py/main.py agent

# OpenAI cloud
BACH_LLM_BASE_URL=https://api.openai.com/v1 BACH_LLM_MODEL=gpt-4o \
  BACH_LLM_API_KEY=sk-... python py/main.py agent
```

All tools are exposed regardless of model. The agent loads `BACH_SKILL.md` as
its system prompt and routes tool calls to Max through the same TCP bridge.

## File map (what each file is for)

### Root files

- `README.md`: setup and usage.
- `environment.yml`: Conda env definition (Python 3.11).
- `requirements.in`: direct Python dependencies (`mcp`, `requests`).
- `requirements.txt`: pinned, compiled dependency lock for pip install.
- `claude_desktop_config.json`: example Claude Desktop MCP server config for the **stdio** transport (edit absolute paths).
- `.gitignore` / `.gitattributes`: ignore rules and Git text normalization.

### Python package (`py/`)

- `py/main.py`: single entrypoint with two subcommands — `serve` (default; MCP server for MCP host apps like Claude Desktop, over HTTP by default or stdio with `--stdio`) and `agent` (self-hosted REPL against any OpenAI-compatible provider). Both build the same `BachMCPServer` + FastMCP app.
- `py/bach_mcp/__init__.py`: public exports.
- `py/bach_mcp/server.py`: high-level bridge server (message queue, send/wait helpers, lifecycle).
- `py/bach_mcp/tcp.py`: low-level TCP server/client classes (`3001` inbound, `3000` outbound).
- `py/bach_mcp/mcp_app.py`: FastMCP tool registration — the single source of truth for tools, used by both roles.
- `py/bach_mcp/mcp_tools.py`: in-process bridge exposing the MCP tools to the local agent (`list_tools` / `call_tool`).
- `py/bach_mcp/agent.py`: provider-agnostic tool-calling loop (`Agent`, `AgentConfig`).
- `py/bach_mcp/BACH_SKILL.md`: system prompt / skill (session protocol, llll syntax, slots, orchestral layout).
- `py/bach_mcp/bach_score_schema.json`: JSON schema describing the Bach score format.
- `py/bach_mcp/llm/provider.py`: `LLMProvider` interface, neutral types (`ToolSpec`/`ToolCall`/`AssistantTurn`), `ProviderConfig`, and `build_provider()` factory.
- `py/bach_mcp/llm/openai_compat.py`: `OpenAICompatibleProvider` — covers Ollama, llama.cpp, vLLM, OpenAI, etc.

### Max package (`max/bach-mcp`)

- `max/bach-mcp/patchers/bach-mcp.maxpat`: patcher containing `bach.roll`, `bach.portal`, and `node.script`.
- `max/bach-mcp/js/bachTCP.js`: Node for Max TCP bridge.
  - Max listens on `0.0.0.0:3000` for Python commands.
  - Max client connects to Python on `127.0.0.1:3001` for replies/events.

## Implementation details

The `agent` role is assembled from these components:

1. Provider layer (`py/bach_mcp/llm/`)
- `LLMProvider` is the single interface every backend implements.
- `OpenAICompatibleProvider` calls `/chat/completions` with `tools` and normalizes the reply into an `AssistantTurn` (text + `ToolCall`s).
- `ProviderConfig.from_env()` + `build_provider()` select the backend from `BACH_LLM_*`. There is no Ollama-specific provider — Ollama is just an OpenAI-compatible endpoint.

2. Tool source of truth (`py/bach_mcp/mcp_app.py` + `py/bach_mcp/mcp_tools.py`)
- `mcp_app.py` defines all tools once via FastMCP.
- `McpToolBridge` introspects that app for schemas (`list_tools`) and invokes tools in-process (`call_tool`). No duplicated schemas or dispatch.

3. Agent loop (`py/bach_mcp/agent.py`)
- `Agent.chat()` runs up to `max_tool_rounds` rounds: call provider → execute any tool calls via the bridge → feed results back.
- Provider- and tool-agnostic: the same loop drives any model against the same tools.

4. Shared Max transport (`py/bach_mcp/server.py` + `py/bach_mcp/tcp.py`)
- Same transport stack for both roles.
- Commands go to Max on port `3000`; responses/events come back on `3001`.

## Dependencies

Install from `requirements.txt` (the pinned lock compiled from `requirements.in`):

```bash
python -m pip install -r requirements.txt
```

If you change `requirements.in`, rebuild the lock file with pip-tools:

```bash
pip-compile --output-file=requirements.txt requirements.in
```
