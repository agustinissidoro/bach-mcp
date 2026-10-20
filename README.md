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
- **`llama`** — `llama-server` loads a GGUF file itself. It runs on an
  internal port behind the same gateway, which passes everything through
  unchanged except for adding the instrument docs (below).

With both backends the chat's port belongs to the gateway, and `llama-server`
runs behind it.

### Instrument docs

`py/bach_mcp/docs/` holds a reference file per instrument (strings, woodwinds,
piano): ranges, techniques and harmonics in midicents. When a message names an
instrument ("a duet for cello and alto flute"), the gateway appends that
instrument's whole file, and its family's, to the message before the model sees
it; no tool call is involved. Each file is added once per conversation, at its
first mention. The terminal names the files it added (`docs  strings/cello, ...`).
`python py/main.py agent` does the same itself. Set `docs = false` in `[chat]`
to switch it off.

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
| `[algo]` | folder of the algorithm files, the Node.js used to check them |

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

Four tools make up the `lean` tool set:

- `send_algorithm(name, code, runner)` — the algorithm that generates the score
  (below).
- `write_score(score, add)` — the score itself as JSON.
- `read_score(voice, from_ms, to_ms)` — the current score as JSON.
- `clear_score`.

### Modes: `/score` and `/algo`

A conversation is in one of two modes, chosen by starting a message with a
prefix; a mode lasts until the other prefix:

- **`/score`** (the default): the model writes the notes. It reads the score
  part of the skill and gets `write_score`, `read_score`, `clear_score`.
- **`/algo`**: the model writes an algorithm. It reads the algorithm part of the
  skill and gets only `send_algorithm`.

Each mode reads only what applies to it: about 3,200 tokens in `/algo` and
4,700 in `/score`, against 7,200 for everything (measured with Qwen's
tokenizer). The instrument docs come on top, 330–920 tokens per instrument.
The skill file marks its parts with `<!-- algo -->`, `<!-- score -->` and
`<!-- both -->` lines (`py/bach_mcp/modes.py`).

The gateway applies the mode to every request of the web chat, and
`python py/main.py agent` does the same (a message that is only `/algo` or
`/score` switches without sending anything). The model server reuses what it
has already read as long as the conversation only grows, so the skill costs
time once per conversation; switching mode, or editing an earlier message,
makes it read everything again once. Claude Desktop does not go through
either, and gets all four tools and the whole skill.

Every write is checked against bach.roll in code and answered with a compact
summary, so the model does not need to dump the score to verify it.

Set `toolset = "full"` in `bach.toml` to additionally expose the ~45 raw
bach.roll commands that take llll strings (with `BACH_SKILL_LLLL.md` as the
skill), and `verify_writes = false` to skip the post-write check.

Run the tests with `python -m unittest discover -s py/tests` (with Node.js
installed, this also runs the JavaScript tests of the Max objects in
`py/tests/js`).

## Algorithms

In algorithmic composition the work is formalising the idea, so the model's
main output is not the notes but the algorithm that generates them: a short
JavaScript file whose parameters are declared and exposed, so you can try,
tweak and run it again in Max.

```js
const params = {
  times:    { type: "slider", range: [1, 64], value: 16 },
  register: { type: "range", range: [3600, 9600], value: [4800, 8400], unit: "mc" },
  seed:     { type: "seed", value: 1 },
};

function generate(p, input) {
  const s = score();
  const v = s.voice("Flute");
  const r = rng("pitch");
  for (let i = 0; i < p.times; i++) v.note(i * 250, r.int(p.register[0], p.register[1]), 250);
  return s;
}
```

`generate` returns the same JSON score as `write_score`. Everything the file
uses is in scope without imports: the score builder, seeded randomness (`rng`;
the same parameters always give the same score), number helpers and
procedures (random walks, Markov chains, L-systems, cellular automata,
Euclidean rhythms). The library and the parameter types are in
`max/bach-mcp/javascript/bach.mcp.core.js` and in the skill.

`send_algorithm(name, code)`:

1. runs the file in Node with the same library: at its declared values, then
   once for each slider at its minimum and maximum, each toggle flipped and
   each menu option, so every setting reachable from the panel is known to
   work (an endless loop is stopped after 20 s);
2. saves it as `algorithms/<name>.js` (the previous version goes to
   `algorithms/.history/`);
3. tells Max to load it into `bach.mcp.algo`, and reports the parameters and
   the score at the declared values.

A file that fails changes nothing; the model gets the error with its line.

Three objects in the Max package do the rest:

| object | what it does |
|---|---|
| `bach.mcp.algo [name] [file]` | Runs an algorithm file (v8). Left inlet: `load <path>`, `run`, `<param> <value...>`. Right inlet: an input score (`dictionary`), passed to `generate` as `input`, so one algorithm can transform another's output. Outlets: the score as a `dictionary`, the panel, and `loaded`/`done`/`error`. It reloads the file when it changes on disk. `name` (default `algo`) is the runner `send_algorithm` addresses. |
| `bach.mcp.params` | The panel: a `jsui` with `bach.mcp.params.js`. Built from the parameters the runner sends; one element per parameter, placed automatically (slider, range, toggle, menu, seed, curve, list). Moving one sends `<param> <value>` to the runner, which runs again. Double-click: back to the declared value. Saved with the patch, and works with `pattr`/`pattrstorage` for presets. |
| `bach.mcp.translate @in json\|bach @out bach\|json` | JSON score ↔ bach.roll (v8), the same translation as `translate.py`. `@in bach` reads a bach.roll llll in text form (through `[bach.portal @out t]`). `@add 1` adds instead of replacing. |

In `bach-mcp.maxpat` they are already connected: algo → translate → bach.roll,
algo ↔ panel. Several runners can live in one patch under different names
(`send_algorithm(..., runner="strings")`).

When the model revises an algorithm under the same name, parameters that keep
their name and type keep the value you set.

## Installation instructions (llama.cpp)

**1. Install** (Python 3.11):

```bash
git clone https://github.com/dzluke/bach-mcp.git
cd bach-mcp
conda env create -f environment.yml
conda activate bach-mcp
python -m pip install -r requirements.txt
```

**2. Install llama.cpp** so that `llama-server` is available (e.g. `brew install llama.cpp`),
and Node.js (`brew install node`), which checks each algorithm before it reaches Max.

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
- `algorithms/`: algorithm files written by `send_algorithm` (two examples: `drift.js`, `cells.js`).
- `run.command`: starts the MCP server, `llama-server` and the web chat.
- `environment.yml`: Conda env definition (Python 3.11).
- `requirements.in`: direct Python dependencies (`mcp`, `requests`).
- `requirements.txt`: pinned, compiled dependency lock for pip install.
- `claude_desktop_config.json`: example Claude Desktop MCP server config for the **stdio** transport (edit absolute paths).
- `.gitignore` / `.gitattributes`: ignore rules and Git text normalization.

### Python package (`py/`)

- `py/main.py`: single entrypoint — `run` (MCP server + `llama-server` + web chat), `serve` (default; MCP server only, HTTP or `--stdio`) and `agent` (terminal chat against any OpenAI-compatible endpoint).
- `py/bach_mcp/config.py`: loads `bach.toml` and derives the `llama-server` command line and the web chat's default settings.
- `py/bach_mcp/gateway.py`: sits on the chat's port in front of the model: a pass-through proxy to llama-server (llama backend) or a translator to Ollama (ollama backend); with both it applies the mode and adds the instrument docs to the messages.
- `py/bach_mcp/docs.py`: finds the instruments named in a message (keyword matching on each file's aliases) and builds the reference block from their files.
- `py/bach_mcp/__init__.py`: public exports.
- `py/bach_mcp/server.py`: high-level bridge server (message queue, send/wait helpers, lifecycle).
- `py/bach_mcp/tcp.py`: low-level TCP server/client classes (`3001` inbound, `3000` outbound).
- `py/bach_mcp/mcp_app.py`: FastMCP app factory; selects the tool set and holds the raw llll tools of the `full` set.
- `py/bach_mcp/translate.py`: deterministic JSON ↔ llll translator (voices > chords > notes in milliseconds and midicents, slots, dump parsing).
- `py/bach_mcp/compose.py`: restricted Python runner for generating scores from code. Currently not exposed as a tool.
- `py/bach_mcp/score_tools.py`: the lean JSON tool set (`write_score`, `read_score`, `clear_score`).
- `py/bach_mcp/modes.py`: the `/score` and `/algo` modes: the prefixes, each mode's part of the skill and its tools.
- `py/bach_mcp/algo_tools.py`: `send_algorithm`: checks an algorithm file in Node, saves it in `algorithms/` and loads it in Max.
- `py/bach_mcp/algo_check.js`: the Node check `send_algorithm` runs (declared values, then the edges of every parameter).
- `py/bach_mcp/mcp_tools.py`: in-process bridge exposing the MCP tools to the local agent (`list_tools` / `call_tool`).
- `py/bach_mcp/agent.py`: provider-agnostic tool-calling loop (`Agent`, `AgentConfig`).
- `py/bach_mcp/BACH_SKILL.md`: system prompt / skill for the lean tool set (principle first, then notation; note table; JSON format). Also sent as the MCP server instructions.
- `py/bach_mcp/BACH_SKILL_LLLL.md`: the previous llll skill, used with `toolset = "full"`.
- `py/bach_mcp/bach_score_schema.json`: earlier JSON schema draft; not used by the code.
- `py/bach_mcp/docs/`: instrument reference for the model (strings, woodwinds, piano): ranges, techniques and harmonics in midicents, one file per instrument plus one per family. Added to the messages by the gateway (`docs.py`); the format is in `docs/README.md`.
- `py/tests/test_translate.py`: tests for the translator and the compose runner.
- `py/tests/test_docs.py`: checks the instrument docs (fields, ranges, clefs, JSON spellings the translator accepts).
- `py/tests/test_modes.py`: the modes: prefixes, skill parts, tools, and what the gateway sends.
- `py/tests/test_algo.py`: `send_algorithm`, the example algorithms, and the JS translator against `translate.py` on the same scores and dumps.
- `py/tests/js/`: tests of the Max objects, run with Node on a stand-in for Max (`maxmock.js`).
- `py/bach_mcp/llm/provider.py`: `LLMProvider` interface, neutral types (`ToolSpec`/`ToolCall`/`AssistantTurn`), `ProviderConfig`, and `build_provider()` factory.
- `py/bach_mcp/llm/openai_compat.py`: `OpenAICompatibleProvider` — covers Ollama, llama.cpp, vLLM, OpenAI, etc.

### Max package (`max/bach-mcp`)

- `max/bach-mcp/patchers/bach-mcp.maxpat`: patcher containing `bach.roll`, `bach.portal`, `node.script`, and an algorithm runner with its panel and translator.
- `max/bach-mcp/patchers/bach.mcp.algo.maxpat`, `bach.mcp.translate.maxpat`: the runner and translator abstractions.
- `max/bach-mcp/javascript/bach.mcp.core.js`: the library in scope in every algorithm file, and the loader (also used by the Node check).
- `max/bach-mcp/javascript/bach.mcp.score.js`: JSON ↔ llll in JavaScript, a port of `translate.py`.
- `max/bach-mcp/javascript/bach.mcp.algo.js`, `bach.mcp.translate.js`: the v8 scripts of the two abstractions.
- `max/bach-mcp/javascript/bach.mcp.params.js`, `bach.mcp.gui.js`: the panel (jsui) and its library of elements (ECMAScript 5, for jsui's engine).
- `max/bach-mcp/javascript/bachTCP.js`: Node for Max TCP bridge.
  - Max listens on `0.0.0.0:3000` for Python commands.
  - Max client connects to Python on `127.0.0.1:3001` for replies/events.
