#!/bin/zsh
# Starts everything Bach needs: the MCP server, llama-server and the web chat.
# Open the Max patch and click "script start" first. Settings live in bach.toml.
# Double-click this file in Finder, or run ./run.command in a terminal.

cd "$(dirname "$0")" || exit 1

# Find the Python of the bach-mcp conda environment (override with BACH_PYTHON).
PY="${BACH_PYTHON:-}"
if [[ -z "$PY" ]]; then
  for base in "${CONDA_PREFIX:-}" "$HOME/miniconda3/envs/bach-mcp" "$HOME/anaconda3/envs/bach-mcp" \
              "$HOME/miniforge3/envs/bach-mcp" "/opt/miniconda3/envs/bach-mcp" \
              "/opt/anaconda3/envs/bach-mcp" "/opt/homebrew/Caskroom/miniconda/base/envs/bach-mcp"; do
    if [[ -n "$base" && -x "$base/bin/python" ]] && "$base/bin/python" -c "import mcp" 2>/dev/null; then
      PY="$base/bin/python"
      break
    fi
  done
fi
if [[ -z "$PY" ]]; then
  echo "Could not find the bach-mcp Python environment."
  echo "Create it (see README), or set BACH_PYTHON to its python executable."
  exit 1
fi

# Homebrew's llama-server is not on PATH when this is launched from Finder.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

exec "$PY" py/main.py run "$@"
