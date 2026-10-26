# bach-mcp

`bach-mcp` bridges `bach.roll` in Max with a model. Two ways in, both reaching
the same 13 tools:

- **Claude** (Claude Desktop, Claude Code) calls Bach's tools over MCP. Claude
  is its own model; nothing else runs.
- **A local model** runs on your Mac, through Bach's own chat page.

## Quickstart: the local model

After the first-time installation (below):

1. Get a model into `models/` and set it in `bach.toml` (below), e.g.
   `python py/main.py download mlx-community/Qwen3.8-27B-4bit --use`.
2. In Max, open `bach-mcp-udp.maxpat` (the UDP bridge needs no starting).
3. Double-click `run.command` (or run `./run.command` in a terminal).

`run.command` starts the model server, the bridge to Max and the chat page,
and opens the page once the model is ready (the first start of a repo also
downloads it). Ctrl-C in that terminal stops everything. The page works in a
browser, and in a Max patch inside `[jweb]`: there it also takes `send <text>`
and `new` at its inlet, and reports `mode`, `tool <name>` and `done` at its
outlet.

Start a message with `/algo` or `/score` to switch modes (below), or use the
buttons. **Stop** ends the answer being written; **New chat** forgets the
conversation.

### Model backends

Bach picks one from the model's files: `.safetensors` → mlx, `.gguf` → gguf.
Both run a server that speaks the OpenAI chat API, on an internal port; Bach
starts and stops it, and `py/bach_mcp/model/client.py` is the one client.

- **`mlx`**: `mlx_lm.server`, Apple's MLX on the Mac's GPU (the `mlx-lm` package,
  installed with the Python requirements). Models: `mlx-community/...` repos or
  a folder.
- **`gguf`**: `llama-server` from llama.cpp (`brew install llama.cpp`). Models: a
  `.gguf` file, or a repo `user/repo:Q4_K_M`.

Sampling, the reply limit and the reasoning switch travel with every request.
A reply that runs out of tokens inside a tool call it never finishes (a
repetition loop) is asked once more. The sampling in `bach.toml` follows
Qwen's recommendation for answers without reasoning (temperature 0.7, top_p
0.8, top_k 20, presence penalty 1.5): with the earlier settings 5 of 12 test
replies looped, with these none. Everything the model server prints goes to
`logs/model-server.log`.

### Models: the `models/` folder

Local models live in `models/` at the root of the repository, one folder per
model (git ignores them; they are many gigabytes).

```bash
python py/main.py download qwen3.8-27b --use                      # by its name in models/catalog.toml
python py/main.py download mlx-community/Qwen3.8-27B-4bit --use   # an MLX repo: the whole repo (16 GB)
python py/main.py download <user>/<model>-GGUF:Q4_K_M --use      # a GGUF repo: that quantization only
python py/main.py download https://huggingface.co/<user>/<repo>   # a link: a repo, one file in it, or any .gguf
python py/main.py models                                          # what is there, and what the catalogue knows
```

`models/catalog.toml` names a few models (your Qwen 3.8 27B as MLX and as
GGUF, a fast 8B, a tiny 0.6B to check that everything runs), each with its
repo, format, size and a note; add your own.

`--use` sets `[model] model` in `bach.toml`, keeping its comments. The
runtime follows from the model, never set by hand: `.safetensors` weights run
on `mlx_lm.server`, a `.gguf` file on `llama-server` (for a repo not yet
downloaded: a name with GGUF or a `:QUANT` means gguf). `model` can then be just the folder's name; it can also be any path,
or a Hugging Face repo that the model server downloads itself. A stopped
download goes on where it was when started again. Without a model, `run` still
starts: the page and Max say what is missing, and Claude Code can use the
tools.

### Max can ask Bach

Over the same UDP bridge, the patch can ask Bach about itself with one line,
and Bach answers with `mcp_info` lines (`py/bach_mcp/utilities/status.py`):

| Max sends (to `[udpsend 127.0.0.1 3001]`) | Bach answers (at `[udpreceive 3000]`) |
|---|---|
| `bach_ask status` | `mcp_info status <state> <model> <message>` |
| `bach_ask settings` | `mcp_info setting <section.key> <value>` for each, then `mcp_info end settings <n>` |
| `bach_ask models` | `mcp_info model <name> <format> <GB> <in use 1/0>` for each, then `mcp_info end models <n>` |
| `bach_ask catalog` | `mcp_info catalog <name> <format> <GB> <downloaded 1/0> <repo> <note>` for each, then `mcp_info end catalog <n>` |
| `bach_ask download_model <name\|repo\|link> [use]` | `mcp_info download start <name> <GB> <folder>`, then `mcp_info download progress <name> <percent> <GB done> <GB total>` every 2 s, then `mcp_info download done <name> <format> <GB>` (or `error <name> <message>`). With `use`, `bach.toml` then names the model; restart Bach to load it. |
| `bach_ask download_stop` | `mcp_info download stopped <name>`; what was fetched stays, and the next start goes on from there |
| `bach_ask help` / `bach_ask ping` | `mcp_info help ...` / `mcp_info pong` |

`<state>` is `starting`, `no_model`, `loading`, `ready`, `stopped` (the model
server ended), `claude` (Bach serves Claude) or `off` (Bach quit). Bach also
sends `mcp_info status ...` by itself whenever the state changes, and
`mcp_info notice <text>` for anything else worth knowing (for example another
Bach holding the port).

In the patch, two changes make this visible: add `mcp_info` to
`[route algo mcp_buffer_written write_buffer]` after `[udpreceive 3000]` and
connect its new outlet to `[print bach]` (or to `[route status setting model
end notice]`); and send requests with a message box such as `[bach_ask status(`
into `[s bach.mcp.udp]`, which feeds `[udpsend 127.0.0.1 3001]`.

### Instrument docs

`py/bach_mcp/prompt/docs/` holds a reference file per instrument (strings,
woodwinds, piano): ranges, techniques and harmonics in midicents. When a
message names an instrument ("a duet for cello and alto flute"), that
instrument's whole file, and its family's, is appended to the message before
the model sees it; no tool call is involved. Each file is added once per
conversation, at its first mention, and the chat shows which. Set `docs =
false` in `[chat]` to switch it off. Claude gets the same files as MCP
resources (`bach://docs/strings/cello`, ...).

## Quickstart: Claude

```bash
python py/main.py claude
```

adds Bach to Claude Desktop (restart it afterwards) and prints the line that
adds it to Claude Code. Claude then starts Bach itself. It gets the 13 tools,
the whole skill as the server's instructions, `/score` and `/algo` as prompts,
and the instrument docs as resources.

Only one Bach can talk to the patch at a time (it holds UDP port 3001), and
Claude Desktop starts one when it opens. To use Claude Code beside
`run.command`, add the second line `main.py claude` prints: it joins the
running Bach at `http://127.0.0.1:8080/mcp` instead of starting another.

## Configuration (`bach.toml`)

One file configures everything; Claude only uses `[server]`, `[max]` and
`[algo]`:

| Section | What it sets |
|---|---|
| `[model]` | the model (its runtime follows from it), context size (gguf), extra server flags |
| `[generation]` | reply token limit, temperature, top-p, top-k, presence penalty, reasoning (off / on) |
| `[chat]` | the skill file, tool calls allowed per answer, instrument docs, open the browser |
| `[server]` | Bach's address (the chat page, and `/mcp` for Claude Code), tool logging |
| `[max]` | UDP ports of the bridge to Max, the buffer file scores travel through |
| `[algo]` | folder of the algorithm files, the Node.js used to check them |

## How the model writes music

The model never writes bach's llll syntax. A deterministic layer
(`py/bach_mcp/music/translate.py`, no LLM involved) converts between a JSON score and
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

The tools:

- `send_algorithm(name, code, runner)` — the algorithm that generates the score
  (below).
- `write_score(score, add)` — the score itself as JSON.
- `read_score(voice, from_ms, to_ms)` — the current score as JSON.
- `clear_score`.
- the pitch tools (`p2mc`, `mc2p`, `get_midicents`, `transpose`, `reverse`,
  `mirror`, `force_scale`, `get_chord`, `get_scale`): exact pitch arithmetic in
  midicents, whose answers the model copies into the score.

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
`<!-- both -->` lines (`py/bach_mcp/prompt/skill.py`).

The local chat applies the mode to every request (`py/bach_mcp/chat/engine.py`);
a message that is only `/algo` or `/score` switches without asking the model.
The model server reuses what it has already read as long as the conversation
only grows, so the skill costs time once per conversation; switching mode
makes it read everything again once. Claude gets the whole skill and every
tool, and the modes as two prompts.

Every write is checked against bach.roll in code and answered with a compact
summary, so the model does not need to dump the score to verify it.

### The bridge to Max: UDP, plain text, and one file

Max and the MCP server talk over UDP with short plain-text messages, such as
`mcp_buffer_written q3 "/path/buffer.txt"`. In the patch, `[udpreceive 3000]`
feeds the router and replies go into `[udpsend 127.0.0.1 3001]`. `udpreceive`
only reads OSC packets, so the Python side (`py/bach_mcp/bridge/udp.py`) packs each
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
in `py/bach_mcp/bridge/buffer.py`.

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
| `bach.mcp.translate @in json\|bach @out bach\|json` | JSON score ↔ bach.roll (v8), the same translation as `music/translate.py`. `@in bach` reads a bach.roll llll in text form (through `[bach.portal @out t]`). `@add 1` adds instead of replacing. |

In `bach-mcp-udp.maxpat` they are already connected: algo → translate → bach.roll,
algo ↔ panel. Several runners can live in one patch under different names
(`send_algorithm(..., runner="strings")`).

When the model revises an algorithm under the same name, parameters that keep
their name and type keep the value you set.

## Installation

**1. Python** (3.11), with the MCP server and MLX:

```bash
git clone https://github.com/dzluke/bach-mcp.git
cd bach-mcp
conda env create -f environment.yml
conda activate bach-mcp
python -m pip install -r requirements.txt
```

**2. Node.js** (`brew install node`), which checks each algorithm before it
reaches Max. For GGUF models also **llama.cpp** (`brew install llama.cpp`).

**3. Max**: open the patch from `max/bach-mcp/patchers`, with the repository
on Max's search path, or copy the `max/bach-mcp` folder into your Max Packages
folder (`~/Documents/Max 9/Packages/`).

**4. Edit `bach.toml`** and follow a Quickstart above.

### Commands

```
python py/main.py run       the local model in the chat page (what run.command does)
python py/main.py serve     the tools for an MCP host: --stdio when the host starts Bach
python py/main.py agent     the local model in the terminal, same engine as the page
python py/main.py eval      the evaluation suite against the local model (no Max needed)
python py/main.py claude    add Bach to Claude Desktop; print the line for Claude Code
python py/main.py download  a model into models/: a catalogue name, a repo or a link (--use: set it in bach.toml)
python py/main.py models    the models in models/, and the catalogue
```

## File map

What each file does, and a diagram of how they connect, is in
[`filemap.md`](filemap.md). Files no longer used are in
[`deprecated/`](deprecated/README.md).
