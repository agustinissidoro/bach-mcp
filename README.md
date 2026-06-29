# bach-mcp

`bach-mcp` bridges `bach.roll` in Max with an LLM.

## Quickstart

After running the first time installation instructions (see below) you can start using bach MCP with the following steps:

1. Navigate to your `bach-mcp` folder and activate your conda environment with `conda activate bach-mcp`
2. Start the MCP server with `python py/main.py`
3. Start the llama.cpp server with `llama-server`
4. In Max, open the `bach-mcp.maxpat` and hit the `script start` message
5. In your browser, navigate to the llama.cpp webui at `https://localhost:8080` and begin chatting

## Installation instructions (llama.cpp)

**1. Install** (Python 3.11):

```bash
git clone https://github.com/dzluke/bach-mcp.git
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

**3. Start the server:**

The server must remain running for you to interact with it, start it by running:

```bash
python py/main.py                 # serves over HTTP at http://127.0.0.1:8000/mcp
```

**4. Start llama-server (llama.cpp)**

After installing llama.cpp, run the llama.cpp server with:

```bash
llama-server
```

This hosts a web UI you can use to chat with local LLMs. Run `llama-server -h` for flags to set the context window, cache type, etc.

**5. Add the MCP server to llama-server web UI**

Open the llama-server web UI at `http://localhost:8080`. 

1. Click the `+` icon next to the chat bar and navigate to 'MCP Servers' -> 'Manage MCP Servers'
2. Under 'Manage Servers' click 'Add New Server'
3. In the 'Server URL' field, enter the URL that was printed when you started the MCP server (default is `http://127.0.0.1:8000/mcp`) 
4. Click 'Add', save settings, and begin chatting with the LLM


## Installation instructions (Claude Desktop)

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
