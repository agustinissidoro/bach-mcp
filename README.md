# bach-mcp

> Disclaimer: this setup is currently supported on macOS only.

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

If your `environment.yml` has a `prefix:` line that points to a different machine, remove that line before creating the env.

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
~/Documents/Max 8/Packages/
```

Resulting path should be:

```text
~/Documents/Max 8/Packages/bach-mcp
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
