# Command map

Every command that travels between the parts of Bach, who sends it and who receives it.

```
                    ┌──────────────────────── Python (the hub) ────────────────────────┐
  Max  ──UDP 3001──►│  chat/hub.py: one handler for every line                         │
       ◄─UDP 3000───│  holds: playground · instance map · active instance · chats      │
                    │                                                                   │
  web  ──POST /api/line──►   same lines as Max                                         │
       ◄─GET /api/events──   same lines as Max + web-only lines (server-sent events)   │
                    │                                                                   │
  terminal (agent) ─ typed lines ─► same lines as Max; prints everything back          │
                    │                                                                   │
  Claude ──MCP /mcp or stdio──► the 13 tools, which work for the active instance       │
                    └───────────────────────────────────────────────────────────────────┘
```

## The form of a line

| Rule | Example |
|---|---|
| Words separated by spaces | `set_active_instance scales1` |
| An instance's command starts with its name | `scales1 prompt "a scale"` |
| Text with spaces, `"` or `\` goes between double quotes, with `\"` and `\\` inside | `scales1 prompt "a \"tight\" canon"` |
| A `prompt` joins every word after it, so Max may also send the text unquoted | `scales1 prompt a scale that turns` |
| Numbers are written as they are | `scales1 done 1834 5200` |

Ports and the address are set in `bachmcp.toml`: `[max] send_port` (3000, Python → Max), `[max] receive_port` (3001, Max → Python), `[server] port` (8090, the page and `/mcp`).

**Instance types:** `generator` · `transformer` · `selector` · `writer`

---

## 1. Into Python

Max sends these to `[udpsend 127.0.0.1 3001]`. The web page and the terminal send exactly the same lines.

### Server commands

| Command | Arguments | What Python does | Sent by |
|---|---|---|---|
| `set_playground` | `<path>` (a Max path like `Macintosh HD:/…` works too) | creates `algorithms/`, `rolls/` and `prompts/` if missing; everything the model makes goes there | Max · web · terminal |
| `clear_instance_names_map` | — | empties the map | Max · web · terminal |
| `add_instance_names_map` | `<name> <type>` | adds or updates one instance | Max · web · terminal |
| `set_active_instance` | `<name>` | the instance the menu shows and that Claude's tools work for | Max · web · terminal |

### Instance commands

| Command | Arguments | What Python does | Sent by |
|---|---|---|---|
| `<name> prompt` | `<text>` | queues a prompt for that instance's conversation | Max · web · terminal |
| `<name> stop` | — | stops the answer being written, or removes the prompt from the queue | Max · web · terminal |
| `<name> new` | — | starts a new conversation; the old one is kept as `prompts/<name>-<date>.jsonl` | Max · web · terminal |

### Instance answers (Max → Python)

The tools wait for these after they send something to an instance.

| Line | When |
|---|---|
| `<name> algo_loaded <file> <notes> <ms>` | the instance loaded and ran the algorithm (sent by `bach.mcp.algo.js`) |
| `<name> algo_error <message>` | loading or running it failed |
| `<name> algo_done <notes> <ms>` | it ran again after a parameter change (Python ignores it) |
| `<name> roll_written <file>` | its roll wrote `rolls/<file>` after a `write_roll` |

### Requests about Bach (Max → Python)

Each one is answered at once with `mcp_info …` lines (see section 2).

| Request | Arguments |
|---|---|
| `bach status` | — |
| `bach settings` | — |
| `bach models` | — |
| `bach catalog` | — |
| `bach download_model` | `<name \| repo \| link> [use]` |
| `bach download_stop` | — |
| `bach quit` | — |
| `bach help` | — |
| `bach ping` | — |

---

## 2. Out of Python

Max gets these at `[udpreceive 3000]`. The page gets them through `/api/events`, and the terminal prints them.

**Echo rule:** Python never sends a line back to Max when it came from Max. A line from the web or the terminal goes to Max and to every page.

### Echoes of the server state

| Line | To Max | To the web |
|---|:---:|:---:|
| `set_playground <path>` | ✓ (if the web sent it) | ✓ |
| `clear_instance_names_map` | ✓ (if the web sent it) | ✓ |
| `add_instance_names_map <name> <type>` | ✓ (if the web sent it) | ✓ |
| `set_active_instance <name>` | ✓ (if the web sent it) | ✓ |
| `mcp_info warning <text>` (bad path, unknown type, unknown instance …) | ✓ | ✓ |

### Commands to an instance

Max routes these by the first word, through the map. File names are bare: Max adds the playground folder.

| Line | What the instance does | Sent by the tool |
|---|---|---|
| `<name> load_algo <name>.js` | loads `<playground>/algorithms/<name>.js` and answers `algo_loaded` or `algo_error` | `send_algorithm` |
| `<name> load_roll <name>.txt` | its roll reads `<playground>/rolls/<name>.txt` | `write_score` |
| `<name> write_roll <name>.txt` | its roll writes itself there and answers `roll_written` | `read_score`, `write_score add`, `send_algorithm` (a transformer's source) |
| `<name> tonedivision <n>` | sets the microtonal grid before a load | `write_score` |
| `<name> clear` | erases its roll | `clear_score` |

### A conversation

| Line | Meaning | To Max | To the web |
|---|---|:---:|:---:|
| `<name> prompt <text>` | echo of a prompt | ✓ (if the web sent it) | ✓ |
| `<name> new` | echo: a new conversation | ✓ (if the web sent it) | ✓ |
| `<name> queued` | waits for another instance's answer (one model, one answer at a time) | ✓ | ✓ |
| `<name> thinking` | the model started | ✓ | ✓ |
| `<name> tool <tool> <first line of the result>` | a tool ran | ✓ | ✓ |
| `<name> answer <text>` | the whole answer, once | ✓ | ✓ |
| `<name> done <tokens> <ms>` | finished | ✓ | ✓ |
| `<name> stopped` | stopped by `stop` | ✓ | ✓ |
| `<name> error <message>` | refused or failed (no instance, no playground, no model, selector …) | ✓ | ✓ |
| `<name> delta <text>` | a piece of the answer as it is written | — | ✓ |
| `<name> reasoning <text>` | a piece of the reasoning | — | ✓ |
| `<name> note <text>` | instrument docs added, a reply asked again | — | ✓ |
| `<name> tool_call <tool> <arguments as JSON>` | a tool call, in full | — | ✓ |
| `<name> tool_result <tool> <result>` | a tool's whole answer | — | ✓ |
| `<name> history <JSON>` | a saved conversation, sent when a page connects | — | ✓ |
| `state <state> <model> <message>` | the model's state: `starting`, `loading`, `ready`, `no_model`, `stopped`, `claude` | — | ✓ |

### Answers about Bach (Python → Max only)

Every one starts with `mcp_info`, so the patch routes on the second word.

| Line | When |
|---|---|
| `mcp_info status 1` | Bach started (sent unasked) and in answer to `bach status` |
| `mcp_info status 0` | Bach's last message before it goes off (sent unasked) |
| `mcp_info model <model>` | `bach status`, only when a model is loaded and answers |
| `mcp_info warning <text>` | anything to fix |
| `mcp_info <section.key> <value>` … `mcp_info end settings <n>` | `bach settings` |
| `mcp_info models <name> <format> <GB> <in use 1/0>` … `mcp_info end models <n>` | `bach models` |
| `mcp_info catalog <name> <format> <GB> <downloaded 1/0> <repo> <note>` … `mcp_info end catalog <n>` | `bach catalog` |
| `mcp_info download_start <name> <GB>` · `download_progress <percent>` · `download_done <name>` · `download_error <message>` · `download_stopped <name>` | `bach download_model`, `bach download_stop` |
| `mcp_info help <requests…>` | `bach help` |
| `mcp_info pong` | `bach ping` |

---

## 3. The web page (`page.html`)

It holds nothing: it shows what Python says and turns each action into a line.

| The user does | The page sends (`POST /api/line`) |
|---|---|
| clicks an instance in the menu | `set_active_instance <name>` |
| types a message and presses Send | `<active> prompt "<text>"` |
| presses Stop | `<active> stop` |
| presses New chat | `<active> new` |

| HTTP | What it is |
|---|---|
| `GET /` | the page (browser or Max's `[jweb]`) |
| `POST /api/line` | one line as the body; answers `{"ok": true}` or 400 `{"error": …}` |
| `GET /api/events` | the stream of lines: first the present (state, playground, map, active instance, saved conversations), then everything as it happens |
| `GET /api/state` | the model's state as JSON (the page's heartbeat) |
| `/mcp` | the tools, for Claude (section 4) |

In `[jweb]` the page also sends `off` from its outlet when Bach goes off.

---

## 4. Claude (MCP)

Claude Desktop or Claude Code connects over MCP, either to `python py/main.py serve --stdio` or to `http://127.0.0.1:8090/mcp`. Claude has no `prompt` line. Its tools work for the **active instance** (`set_active_instance`), and the instance's type decides what they accept.

| Tool | Arguments | For types | Sends to Max |
|---|---|---|---|
| `send_algorithm` | `code` | generator (`produce`), transformer (`transform`) | (`<name> write_roll` for a transformer's source), then `<name> load_algo <name>.js` |
| `write_score` | `score`, `add` | writer | (`<name> write_roll` when `add`), `<name> tonedivision`, `<name> load_roll` |
| `read_score` | `voice`, `from_ms`, `to_ms` | any | `<name> write_roll` |
| `clear_score` | — | writer | `<name> clear` |
| `p2mc` `mc2p` `get_midicents` `transpose` `reverse` `mirror` `force_scale` `get_chord` `get_scale` | pitch arguments | any | nothing (computed in Python) |

| Also offered to Claude | What |
|---|---|
| the server instructions | the skill (`BACH_SKILL.md`) |
| prompts `score`, `algo` | the two ways of working |
| resources `bach://skill`, `bach://docs/<instrument>` | the skill and the instrument docs |

**Planned, not built:** Claude run headless (`claude -p`) behind Bach's own page and Max, through the same `<name> prompt` lines.

---

## 5. The local model (inside Python)

Not a separate part on the wire: the hub hands each prompt to the engine (`chat/engine.py`), which calls the same tools in-process. Each instance's type fixes the mode and the tools.

| Type | Mode | Tools | The model writes |
|---|---|---|---|
| `generator` | algo | `send_algorithm` | `function produce(p)` |
| `transformer` | algo | `send_algorithm` | `function transform(source, p)` |
| `selector` | — | — | refused: not built yet |
| `writer` | score | `write_score` `read_score` `clear_score` + the pitch tools | the notes, as JSON |

---

## 6. Files in the playground

| File | Written by | Read by |
|---|---|---|
| `algorithms/<name>.js` | `send_algorithm` (after the check passes) | the instance (`load_algo`) |
| `algorithms/.history/<name>-<date>.js` | `send_algorithm`, the version it replaced | you |
| `algorithms/<name>.source.txt` | a transformer instance in Max (its source score) | the instance; `send_algorithm`'s check |
| `rolls/<name>.txt` | `write_score` (→ `load_roll`), the roll (→ `write_roll`) | the roll; `read_score` |
| `prompts/<name>.jsonl` | the hub, one message per line, after each answer | the hub, when the instance is next prompted or a page connects |
| `prompts/<name>-<date>.jsonl` | `<name> new`, the conversation it put aside | you |
