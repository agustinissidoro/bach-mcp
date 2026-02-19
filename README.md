# bach-mcp

> Disclaimer: this setup is currently supported on macOS only.

## Available MCP tools (current)

The server currently exposes tools to control and query `bach.roll` from an MCP client.

- Score writing:
  `add_single_note`, `send_score_to_max`.
- Generic command bridge:
  `send_process_message_to_max` for raw bach/Max messages that do not have a dedicated wrapper.
- Score/query dump:
  `dump`, `getcurrentchord`, `getnumchords`, `getnumnotes`, `getnumvoices`.
- Score structure and display:
  `numvoices`, `insertvoice`, `deletevoice`, `numparts`, `clefs`, `stafflines`, `voicenames`, `bgcolor`, `staffcolor`, `notecolor`.
- Selection and editing:
  `sel`, `select`, `unselect`, `clearselection`, `legato`, `glissando`, `explodechords`.
- Playback and export:
  `play`, `exportmidi`.
- Markers:
  `addmarker`, `deletemarker`.
- Dynamics and velocity conversion:
  `dynamics2velocities`, `velocities2dynamics`.

### Possibilities

- Build, transform, and play multi-voice notation programmatically.
- Query score state and selected material back into your MCP client workflow.
- Automate rendering/layout settings (clefs, staff lines/colors, names) and MIDI export.
- Use raw llll data for advanced notation structures when needed.

### Slot support (current)

- There are no standalone, slot-dedicated MCP tools yet (e.g. `set_slot` / `get_slot`).
- Slot workflows are already possible through:
  `add_single_note` (`slots=` argument), `dump(mode="slotinfo")`, and raw llll with `send_score_to_max`.

### Scope and support

- Platform support: macOS only (current state of this repo).
- The MCP layer wraps a growing subset of bach/Max messages; for uncovered commands, use `send_process_message_to_max`.

## 1) Clone the repo

```bash
git clone https://github.com/agustinissidoro/bach-mcp.git
cd bach-mcp
```

## 2) Create the conda environment from `environment.yml`

```bash
cd bach-mcp
conda env create -f environment.yml
conda activate bach-mcp
```

## 3) Install pip packages from `pip_requirements.txt`

With the `bach-mcp` conda environment activated:

```bash
cd bach-mcp
pip install -r pip_requirements.txt
```

## 4) Copy `max/bach-mcp` into Max Packages

Copy this folder:

```text
max/bach-mcp
```

Into your Max Packages folder (macOS default):

```text
~/Documents/Max 9/Packages/
```

## 5) Download Claude Desktop

Download and install Claude Desktop from Anthropic:

```text
https://claude.ai/download
```

## 6) Configure Claude Desktop MCP

### Config file location

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Get python path from the running conda env

Activate the env, then get the absolute python path:

```bash
cd bach-mcp
conda activate bach-mcp
which python
```

### Set the main script path

In this repo, the entrypoint is:

```text
/absolute/path/to/bach-mcp/py/main.py
```

### Example `claude_desktop_config.json`

Use the repo example (`claude_desktop_config.json`) and update the absolute paths:

```json
{
  "mcpServers": {
    "bach-mcp": {
      "command": "/absolute/path/to/miniconda3/envs/bach-mcp/bin/python",
      "args": ["/absolute/path/to/bach-mcp/py/main.py"],
      "cwd": "/absolute/path/to/bach-mcp"
    }
  }
}
```

Then fully quit and reopen Claude Desktop.
