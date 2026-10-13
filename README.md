# bach-mcp

`bach-mcp` bridges `bach.roll` in Max with an LLM.

## Quickstart

After the first-time installation (below):

1. Set your model in `bach.toml`: an Ollama model (`backend = "ollama"`, the way
   to run MLX models on Apple Silicon) or a GGUF file for llama.cpp (`backend = "llama"`).
2. In Max, open `bach-mcp.maxpat` and click `script start`.
3. Double-click `run.command` (or run `./run.command` in a terminal).

`run.command` starts the MCP server and the model server, and opens the
llama.cpp web chat already configured: the skill as system prompt, the Bach
tools connected and switched on, and the token limits from `bach.toml`. Ctrl-C
in that terminal stops everything. The first time the model calls a tool, the
chat asks for permission; choose "Always allow" from the button's menu.

### Model backends

- **`ollama`** — the model is served by Ollama, which is opened automatically
  if it is not running. This is how MLX models are used. The web chat is still llama.cpp's: a small
  gateway (`py/bach_mcp/gateway.py`) takes llama-server's place and translates
  between the chat and Ollama, so `llama-server` must be installed too (it
  provides the chat's page, without loading a model).
- **`llama`** — `llama-server` loads a GGUF file itself.

## Configuration (`bach.toml`)

One file configures the model, generation, chat, tools and ports:

| Section | What it sets |
|---|---|
| `[model]` | backend, Ollama model name or GGUF path / Hugging Face repo, context size, GPU layers |
| `[generation]` | reply token limit, temperature, top-p/top-k, reasoning (off / on / auto / a level) and its token budget |
| `[chat]` | system prompt file, tool calls allowed per answer, tool timeout, show thinking, open browser |
| `[mcp]` | host/port, tool set (`lean`/`full`), write verification, tool logging |
| `[llama]` | `llama-server` binary, host/port of the chat, slots, extra flags |
| `[ollama]` | Ollama address, how long the model stays loaded |
| `[max]` | TCP ports of the Max bridge |

The web chat treats these values as defaults: a setting you change by hand in
the browser wins from then on. To go back to `bach.toml`, use the reset button
next to that setting in the chat's settings.

## How the model writes music

The model never writes bach's llll syntax. A deterministic layer
(`py/bach_mcp/translate.py`, no LLM involved) converts between a JSON score and
llll in both directions. The JSON is bach.roll's gathered syntax with named
fields: the same hierarchy (voices > chords > notes) and the same units.

```json
{"voices": [{"name": "Flute", "chords": [
  {"onset": 0, "dyn": "p<", "notes": [{"pitch": 6900, "dur": 1000}]},
  {"onset": 1000, "dyn": "f", "notes": [{"pitch": 7200, "dur": 2000},
                                        {"pitch": 7600, "dur": 500}]},
  {"onset": 4000, "art": "staccato", "notes": [{"pitch": 6700, "dur": 250}]}]}]}
```

- A **chord** holds the `onset` (milliseconds) and what is marked once for the
  whole chord: articulation, dynamic, text.
- A **note** holds `pitch` (midicents, 6000 = middle C), `dur` (milliseconds),
  velocity, glissando and notehead. It has no onset of its own.
- Silence is a gap between onsets; there are no rests, beats or tempo.

Five tools are exposed by default (the `lean` tool set):

- `write_score(score, add)` — the score as JSON. This is how the model composes.
- `read_score(voice, from_ms, to_ms)` — the current score as JSON.
- `play`, `stop`, `clear_score`.

Every write is checked against bach.roll in code and answered with a compact
summary, so the model does not need to dump the score to verify it.

Set `toolset = "full"` in `bach.toml` to additionally expose the ~45 raw
bach.roll commands that take llll strings (with `BACH_SKILL_LLLL.md` as the
skill), and `verify_writes = false` to skip the post-write check.

Run the tests with `python -m unittest discover -s py/tests`.

## Installation instructions (llama.cpp)

**1. Install** (Python 3.11):

```bash
git clone https://github.com/dzluke/bach-mcp.git
cd bach-mcp
conda env create -f environment.yml
conda activate bach-mcp
python -m pip install -r requirements.txt
```

**2. Install llama.cpp** so that `llama-server` is available (e.g. `brew install llama.cpp`).

**3. Set up Max** — copy the `max/bach-mcp` folder into your Max Packages folder:

- macOS: `~/Documents/Max 9/Packages/`
- Windows: `%USERPROFILE%\Documents\Max 9\Packages\`

**4. Edit `bach.toml`** and follow the Quickstart above.

The pieces can also be started separately: `python py/main.py serve` runs only
the MCP server (at the `[mcp]` address), and `python py/main.py agent` is a
terminal chat against the running `llama-server`.

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
- `bach.toml`: the configuration file (model, generation, chat, tools, ports).
- `run.command`: starts the MCP server, `llama-server` and the web chat.
- `environment.yml`: Conda env definition (Python 3.11).
- `requirements.in`: direct Python dependencies (`mcp`, `requests`).
- `requirements.txt`: pinned, compiled dependency lock for pip install.
- `claude_desktop_config.json`: example Claude Desktop MCP server config for the **stdio** transport (edit absolute paths).
- `.gitignore` / `.gitattributes`: ignore rules and Git text normalization.

### Python package (`py/`)

- `py/main.py`: single entrypoint — `run` (MCP server + `llama-server` + web chat), `serve` (default; MCP server only, HTTP or `--stdio`) and `agent` (terminal chat against any OpenAI-compatible endpoint).
- `py/bach_mcp/config.py`: loads `bach.toml` and derives the `llama-server` command line and the web chat's default settings.
- `py/bach_mcp/gateway.py`: lets the llama.cpp web chat use a model served by Ollama (translates the chat's requests and the streamed replies).
- `py/bach_mcp/__init__.py`: public exports.
- `py/bach_mcp/server.py`: high-level bridge server (message queue, send/wait helpers, lifecycle).
- `py/bach_mcp/tcp.py`: low-level TCP server/client classes (`3001` inbound, `3000` outbound).
- `py/bach_mcp/mcp_app.py`: FastMCP app factory; selects the tool set and holds the raw llll tools of the `full` set.
- `py/bach_mcp/translate.py`: deterministic JSON ↔ llll translator (voices > chords > notes in milliseconds and midicents, slots, dump parsing).
- `py/bach_mcp/compose.py`: restricted Python runner for generating scores from code. Currently not exposed as a tool.
- `py/bach_mcp/score_tools.py`: the lean JSON tool set (`write_score`, `read_score`, `play`, `stop`, `clear_score`).
- `py/bach_mcp/mcp_tools.py`: in-process bridge exposing the MCP tools to the local agent (`list_tools` / `call_tool`).
- `py/bach_mcp/agent.py`: provider-agnostic tool-calling loop (`Agent`, `AgentConfig`).
- `py/bach_mcp/BACH_SKILL.md`: system prompt / skill for the lean tool set (principle first, then notation; note table; JSON format). Also sent as the MCP server instructions.
- `py/bach_mcp/BACH_SKILL_LLLL.md`: the previous llll skill, used with `toolset = "full"`.
- `py/bach_mcp/bach_score_schema.json`: earlier JSON schema draft; not used by the code.
- `py/tests/test_translate.py`: tests for the translator and the compose runner.
- `py/bach_mcp/llm/provider.py`: `LLMProvider` interface, neutral types (`ToolSpec`/`ToolCall`/`AssistantTurn`), `ProviderConfig`, and `build_provider()` factory.
- `py/bach_mcp/llm/openai_compat.py`: `OpenAICompatibleProvider` — covers Ollama, llama.cpp, vLLM, OpenAI, etc.

### Max package (`max/bach-mcp`)

- `max/bach-mcp/patchers/bach-mcp.maxpat`: patcher containing `bach.roll`, `bach.portal`, and `node.script`.
- `max/bach-mcp/js/bachTCP.js`: Node for Max TCP bridge.
  - Max listens on `0.0.0.0:3000` for Python commands.
  - Max client connects to Python on `127.0.0.1:3001` for replies/events.
