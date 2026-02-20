# bach-mcp

> Disclaimer: this setup is currently supported on macOS only.

## Demo video

Watch the demo on YouTube: https://www.youtube.com/watch?v=MswlB7eJNpM

## What you can do with bach-mcp (current)

Instead of manually editing everything in the Max UI, you can drive `bach.roll` from an MCP client and work at a musical level.

- Write and reshape notation:
  create notes/chords, build multi-voice material, and update score content programmatically.
- Edit score structure:
  add/remove/reorder voices, control staff grouping, and organize the score layout.
- Control notation appearance:
  set clefs, staff lines, voice names, note/staff/background colors, and other display attributes.
- Work with expressive note data:
  set and manipulate noteheads, articulations, dynamics, text expressions, breakpoints, and other slot-based note metadata.
- Convert performance data:
  map dynamics to MIDI velocities and infer dynamics from velocity values.
- Perform score transformations:
  apply legato/glissando operations, explode chords, and run time-range selection edits.
- Navigate and annotate form:
  add/remove markers, query current score state, and inspect selected material.
- Audition and export:
  play score regions and export MIDI for downstream DAW or notation workflows.

### Slot and expression support (current)

- Slot workflows are already supported for expressive notation tasks (dynamics, articulations, noteheads, text, automation/function data, etc.).
- Dedicated high-level slot management commands are still limited; advanced workflows may still require raw llll-style input.

### Scope and platform support

- Platform support: macOS only (current state of this repo).
- The MCP layer already covers many common notation and editing workflows, and can be extended over time for additional bach commands.

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
