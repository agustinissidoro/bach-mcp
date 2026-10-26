# deprecated

Files that are no longer used, kept as they were. They keep their original
place in the tree (`deprecated/py/...` was `py/...`), so it is clear where
each came from. Nothing here is imported, tested or loaded, and the Python
files no longer run from here (their relative imports point at a package that
moved on).

| file | what it was | replaced by |
|---|---|---|
| `py/bach_mcp/tcp.py` | TCP bridge to Max (Python side) | `py/bach_mcp/bridge/udp.py` |
| `max/bach-mcp/javascript/bachTCP.js` | TCP bridge to Max (Node for Max side) | `[udpreceive]` / `[udpsend]` in the patch |
| `max/bach-mcp/patchers/bach-mcp.maxpat` | main patch of the TCP era (`node.script bachTCP.js`) | `max/bach-mcp/patchers/bach-mcp-udp.maxpat` |
| `py/bach_mcp/mcp_app_full.py` | the old `mcp_app.py` with the `full` tool set: 43 raw bach.roll tools taking llll, project memory, score screenshots | `py/bach_mcp/tools/registry.py` (the 13 JSON and pitch tools) |
| `py/bach_mcp/BACH_SKILL_LLLL.md` | the skill of the `full` tool set | `py/bach_mcp/prompt/BACH_SKILL.md` |
| `py/bach_mcp/assets/screenshots/` | output of `score_snapshot` (`full` set) | — |
| `py/bach_mcp/compose.py` | restricted Python runner that generated scores from code; never exposed as a tool; thinks in note names and beats | `send_algorithm` (JavaScript algorithms run in Max) |
| `py/tests/test_compose.py` | its tests, taken out of `py/tests/test_translate.py` | — |
| `py/bach_mcp/bach_score_schema.json` | early JSON schema draft, never read by the code | `py/bach_mcp/music/translate.py` |
| `py/bach_mcp/gateway.py` | the proxy between llama.cpp's web chat and the model: translated to Ollama's API, or passed through to llama-server, adding the mode and the docs | `py/bach_mcp/chat/` (our own chat page and one conversation engine) and `py/bach_mcp/model/` (mlx or gguf, one OpenAI-format client) |
| `py/tests/test_gateway.py` | its tests | `py/tests/test_chat.py`, `py/tests/test_model.py` |
| `py/bach_mcp/llm/` | the provider layer of the terminal agent (`provider.py`, `openai_compat.py`, `BACH_LLM_*` variables) | `py/bach_mcp/model/client.py` |
| `claude_desktop_config.json` | example Claude Desktop entry, with three paths to edit by hand | `python py/main.py claude` writes the entry with the real paths |

Moved, not deprecated: `agent.py` became `chat/engine.py`, `mcp_tools.py`
became `tools/inprocess.py`, `mcp_app.py` became `tools/registry.py`, and
`server.py` became `bridge/max.py`.

The Max search path includes the whole repository, so Max can still find the
files here. Their names are unique, so they cannot shadow a file in use.
