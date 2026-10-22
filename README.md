# bach-mcp

`bach-mcp` bridges `bach.roll` in Max with an LLM.

## Quickstart

After the first-time installation (below):

1. Set your model in `bach.toml`: an Ollama model (`backend = "ollama"`, the way
   to run MLX models on Apple Silicon) or a GGUF file for llama.cpp (`backend = "llama"`).
2. In Max, open `bach-mcp.maxpat` (the UDP bridge needs no starting).
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

With the Ollama backend the gateway also catches one failure of the model: a
reply that runs out of tokens inside a tool call it never finishes (a
repetition loop) is asked once more, without showing anything twice. The
sampling in `bach.toml` follows Qwen's recommendation for answers without
reasoning (temperature 0.7, top_p 0.8, top_k 20, presence penalty 1.5): with
the earlier settings 5 of 12 test replies looped, with these none.

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
| `[generation]` | reply token limit, temperature, top-p/top-k, presence penalty, reasoning (off / on / auto / a level) and its token budget |
| `[chat]` | system prompt file, tool calls allowed per answer, tool timeout, show thinking, open browser |
| `[mcp]` | host/port, tool set (`lean`/`full`), write verification, tool logging |
| `[llama]` | `llama-server` binary, host/port of the chat, slots, extra flags |
| `[ollama]` | Ollama address, how long the model stays loaded |
| `[max]` | UDP ports of the bridge to Max, the buffer file scores travel through |
| `[algo]` | folder of the algorithm files, the Node.js used to check them |

The web chat treats these values as defaults: a setting you change by hand in
the browser wins from then on. To go back to `bach.toml`, use the reset button
next to that setting in the chat's settings.

## How the model writes music

The model never writes bach's llll syntax. A deterministic layer
(`py/bach_mcp/translate.py`, no LLM involved) converts between a JSON score and
llll in both directions. The JSON is bach.roll's gathered syntax in JSON
brackets: the same hierarchy (voices > chords > notes), the same order and the
same units, always with the same parts.

```json
{"voices": [{"name": "Flute", "chords": [
  [0, {"dyn": "p<"}, [6900, 1000, 55]],
  [1000, {"dyn": "f"}, [7200, 2000, 100], [7600, 500, 100]],
  [4000, {"art": "staccato"}, [6700, 250, 100]]]}]}
```

- A **chord** is `[onset, {marks}, note, ...]`: the onset in milliseconds, then
  what is marked once for the whole chord (articulation, dynamic, text; `{}`
  when nothing), then its notes.
- A **note** is always `[pitch, dur, vel]`: midicents (6000 = middle C),
  milliseconds, loudness 1-127; glissando and notehead, when needed, in an
  object after them. It has no onset of its own.
- Silence is a gap between onsets; there are no rests, beats or tempo.

The model writes this form and `read_score` answers in it. It takes about 65% of
the tokens of the earlier form with a key on every value (measured with Qwen's
tokenizer on an 893-chord score), and its fixed shape makes mistakes rare: the
model never decides what to leave out. The translators still accept the earlier
object form (`{"onset": 0, "notes": [{"pitch": 6000, "dur": 500}]}`), and reject
pitches below 1200 (C0), which catches pitch and duration swapped.

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

### The bridge to Max: UDP, plain text, and one file

Max and the MCP server talk over UDP with short plain-text messages, such as
`mcp_buffer_written q3 "/path/buffer.txt"`. In the patch, `[udpreceive 3000]`
feeds the router and replies go into `[udpsend 127.0.0.1 3001]`. `udpreceive`
only reads OSC packets, so the Python side (`py/bach_mcp/udp.py`) packs each
line into one and unpacks the replies: in Max every message is plain text.
Nothing needs to be started in Max.

Scores never travel as messages. They go through one file,
`max/bach-mcp/buffer.txt` (`[max] buffer` in `bach.toml`), always in bach's
own text llll format, the one bach.roll's `read` and `writetxt` use. One
message each way:

| MCP server -> Max | in the patch | Max -> MCP server |
|---|---|---|
| `mcp_buffer_written <path>` | `read <path>` | (nothing) |
| `write_buffer <path>` | `writetxt <path>` | `bach_buffer_written` |

`write_score` writes the buffer and sends `mcp_buffer_written`. `read_score`
sends `write_buffer` and reads the file when `bach_buffer_written` arrives.
`write_score(add=True)` cannot use `read`, which replaces everything: it
fetches the score, inserts the new chords into bach's own text and loads the
result, so whatever the JSON does not model (other slots such as sample paths,
slotinfo, commands) stays as it was. Checking each load in Max (Max answering
with the note count) is switched off for now; the code is kept, commented out,
in `buffer.py`.

## Algorithms

In algorithmic composition the work is formalising the idea, so the model's
main output is not the notes but the algorithm that generates them: a short
JavaScript file whose parameters are declared and exposed, so you can try,
tweak and run it again in Max.

An algorithm is one of two kinds:

- a **producer** makes music from nothing: `function produce(p)`;
- a **transformer** changes music already in the score:
  `function transform(source, p)`.

```js
const params = {
  times:    { type: "slider", range: [1, 64], value: 16 },
  register: { type: "range", range: [3600, 9600], value: [4800, 8400], unit: "mc" },
  seed:     { type: "seed", value: 1 },
};

function produce(p) {
  const s = score();
  const v = s.voice("Flute");
  const r = rng("pitch");
  for (let i = 0; i < p.times; i++) v.note(i * 250, r.int(p.register[0], p.register[1]), 250);
  return s;
}
```

Both return the same JSON score as `write_score`. Everything the file uses is
in scope without imports: the score builder, seeded randomness (`rng`; the
same parameters always give the same score), number helpers, procedures
(random walks, Markov chains, L-systems, cellular automata, Euclidean rhythms)
and helpers for working on a given score (`copy`, `phrases`, `chordEnd`,
`eachNote`). The library and the parameter types are in
`max/bach-mcp/javascript/bach.mcp.core.js` and in the skill. A file with the
older `function generate(p, input)` still loads, as a producer.

**A transformer keeps its original.** If it worked on whatever is in the roll,
each run (each move of a slider) would transform its own previous output. So
the runner keeps the score it started from, the *source*, in a bach text file
next to the algorithm, `max/bach-mcp/algorithms/<name>.source.txt`, and every run starts
again from it. The source is taken from the roll the first time the
transformer is loaded (the runner sends `writetxt` to bach.roll through
`[s to_bach]`), and kept from then on, also when the patch is reopened or the
model revises the file. To transform the current result further, press
**capture** on the panel (or send `capture`): the score now in the roll
becomes the new source. Any bach text file can serve as a source: copy it to
`<name>.source.txt`.

A score can also reach the runner directly, at its right inlet:
bach.roll's first outlet → `[bach.portal @out t]` → `[bach.mcp.translate @in bach @out json]`
→ `bach.mcp.algo` (right inlet). bach.roll sends from that outlet when it gets
`dump`. What such a score does depends on the **source mode**, the switch on
the panel's title row (or `sourcemode keep|follow`):

- **keep** (default): it becomes the source only when there is none yet (and is
  saved to `<name>.source.txt`); after that, inputs are ignored until **capture**.
- **follow**: every score that arrives becomes the source, so the next move of a
  parameter transforms the latest one. An input does not run the transformer by
  itself (only the first does), so dumping the roll never loops back into a run.

`send_algorithm(name, code)`:

1. runs the file in Node with the same library: at its declared values, then
   once for each slider at its minimum and maximum, each toggle flipped and
   each menu option, so every setting reachable from the panel is known to
   work (an endless loop is stopped after 20 s);
2. saves it as `max/bach-mcp/algorithms/<name>.js` (the previous version goes to
   `.history/` there);
3. tells Max to load it into `bach.mcp.algo`, and reports the parameters and
   the score at the declared values.

A file that fails changes nothing; the model gets the error with its line.
A transformer is checked on the music it will work on: its saved source, else
the score now in the roll, else a small built-in score.

Three objects in the Max package do the rest:

| object | what it does |
|---|---|
| `bach.mcp.algo [name] [file] [@roll to_bach]` | Runs an algorithm file (v8). Left inlet: `load <path>`, `run`, `capture`, `<param> <value...>`. Right inlet: a score (`dictionary`) to use as a transformer's source, following `sourcemode keep|follow`. Outlets: the score as a `dictionary`, the panel, and `loaded`/`done`/`error`. It reloads the file when it changes on disk. `name` (default `algo`) is the runner `send_algorithm` addresses; `@roll` names the `[receive]` that feeds bach.roll (default `to_bach`), used to capture sources. |
| `bach.mcp.params` | The panel: a `jsui` with `bach.mcp.params.js`. Built from the parameters the runner sends; one element per parameter, placed automatically (slider, range, toggle, menu, seed, curve, list). Moving one sends `<param> <value>` to the runner, which runs again. Double-click: back to the declared value. A pitch shows as a name, midicents or MIDI (click its value), drags snap to round values (the **snap** switch; alt inverts it). A transformer's panel shows its source, its source mode (**keep**/**follow**) and a **capture** button. Saved with the patch, and works with `pattr`/`pattrstorage` for presets. |
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
- `max/bach-mcp/algorithms/`: algorithm files written by `send_algorithm` (examples: the producers `drift.js` and `cells.js`, the transformer `transpose-phrases.js`), and each transformer's source, `<name>.source.txt`.
- `max/bach-mcp/buffer.txt`: the score exchange file between the MCP server and bach.roll (not in git).
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
- `py/bach_mcp/udp.py`: the UDP bridge to Max, plain text (`3001` inbound, `3000` outbound).
- `py/bach_mcp/tcp.py`: the former TCP bridge; no longer used.
- `py/bach_mcp/mcp_app.py`: FastMCP app factory; selects the tool set and holds the raw llll tools of the `full` set.
- `py/bach_mcp/translate.py`: deterministic JSON ↔ llll translator (voices > chords > notes in milliseconds and midicents, slots, dump parsing).
- `py/bach_mcp/compose.py`: restricted Python runner for generating scores from code. Currently not exposed as a tool.
- `py/bach_mcp/score_tools.py`: the lean JSON tool set (`write_score`, `read_score`, `clear_score`).
- `py/bach_mcp/buffer.py`: the buffer file: writing it for bach.roll to read (`mcp_buffer_written`), having bach.roll write it (`write_buffer`), adding chords to bach's own text.
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
- `py/tests/test_buffer.py`: the buffer file and the score tools against a stand-in bach.roll that reads and writes it.
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
- `max/bach-mcp/javascript/bachTCP.js`: the former Node for Max TCP bridge; no longer connected in the patch.
