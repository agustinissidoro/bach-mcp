# bach-mcp

A Max package that connects `bach.roll` to a language model. The model writes
algorithms that run inside Max, and their parameters become panels you can play
with. It works with a model running on your computer, or with Claude.

## Requirements

- **macOS** and **Max 9**
- The **bach** and **shell** packages, both from Max's Package Manager
- **Python 3.11 or newer**. The installer makes its own virtual environment from
  it, inside the package
- **Node.js**: nothing to install, the installer uses the one that comes with Max
  if you have no other

For a local model:

- **Apple Silicon** for MLX models. Other Macs run GGUF models only, and need
  `brew install llama.cpp`
- Enough memory and disk for the model: the recommended `qwen3.8-27b-4bit` is a
  16 GB download

For Claude: **Claude Desktop** and/or **Claude Code**, on your own Claude account.
Prompts from Max run through Claude Code, which comes with Claude Desktop but has to
be logged in once. `install` checks this and prints the exact command for your
computer in the Max console.

## Installation

1. Put the folder in Max's packages, named `bach-mcp`, and restart Max:

   ```bash
   git clone https://github.com/agustinissidoro/bach-mcp.git ~/Documents/Max\ 9/Packages/bach-mcp
   ```

2. In Max, open the tutorials from **Extras > bach-mcp** and follow them in order:

   | Tutorial | What it does |
   |---|---|
   | `1-installation` | Sends `install` to `bachmcp.server` and sets everything up. Follow it in the Max console |
   | `2-downloading a model` | Lists the catalog and downloads a model (local only) |
   | `3-testing local` | Tries the local model from start to finish |
   | `4-testing claude` | Tries the Claude setup |

The installation can also run from a terminal:

```bash
sh ~/Documents/Max\ 9/Packages/bach-mcp/py/install.sh --claude true --local true
```

Running it again repairs or adds what is missing.

**To uninstall**, remove the folder from Max's packages. If you installed Claude,
also remove the `bach` entry from its configuration: leaving it does no harm, but
Claude will keep trying to connect.

## Basic features

**Two hosts, one server.** `[bachmcp.server local @model <name>]` runs a model on
your computer. `[bachmcp.server claude]` serves the same 13 tools to Claude over
MCP. Start and stop either one with `start` and `stop`, or `1` and `0`.

**Instances you prompt.** Each one has a name, keeps its own conversation and runs
its own algorithm:

| Object | What its algorithm does |
|---|---|
| `bachmcp.generator` | Makes a score from nothing |
| `bachmcp.transformer` | Changes the score of a `bach.roll` |
| `bachmcp.selector` | Selects notes in the score of a `bach.roll` |

Each of these comes with its parameter panel. For your own layout, use the parts
separately: `bachmcp.algo.generate`, `bachmcp.algo.transform`, `bachmcp.algo.select`
and `bachmcp.gui.params`.

**Prompting.** Send `prompt <text>` to an instance, for example from a `bachmcp.prompt`
box. A local model also has a chat page at `http://127.0.0.1:8090`. You can also write
in Claude Desktop or Claude Code directly: its tools work for the active instance,
which is the first one in the patch until you send `set_active_instance <name>` to
`[s bachmcp.server.s]`.

**The playground.** Everything the model makes is kept in a folder, by default
`playground/` in the package: `algorithms/`, `scores/` and `prompts/`. Saving an
algorithm file reloads it in Max, so you can also write algorithms by hand.

**Scores as dictionaries.** `bachmcp.translate` converts between `bach.roll` and a
Max dictionary without losing anything. See
[`bachjson-syntax-specification.md`](bachjson-syntax-specification.md).

**Models.** Download by catalog name, Hugging Face repo or link with `download`
on `bachmcp.server`. Add your own names to `models/catalog.toml`.

**Instrument docs.** A message that names an instrument brings in its ranges and
techniques. Switch this off with `@docs false`.

Every object has a help patch and a reference page. All settings are attributes of
`bachmcp.server`, which writes them to `bachmcp.toml`.

## More

- [`filemap.md`](filemap.md): every file and how they connect
- [`cmdmap.md`](cmdmap.md): every message between Max, Python, the page and Claude

Tests need neither Max nor a model:

```bash
.venv/bin/python -m unittest discover -s py/tests
```
