# Command map

Every command that travels between the parts of Bach: who sends it and who receives it.

```
                    ┌──────────────────────── Python (the hub) ────────────────────────┐
  Max  ──UDP 3001──►│  chat/hub.py: one handler for every line                          │
       ◄─UDP 3000───│  holds: playground · instance map · active instance · chats       │
                    │                                                                   │
  page ──POST /api/line──►   the same lines as Max                                      │
       ◄─GET /api/events──   the same lines as Max + page-only lines (server-sent events)
                    │                                                                   │
  terminal (agent) ─ typed lines ─► the same lines as Max; prints everything back       │
                    │                                                                   │
  Claude ──MCP──► the 13 tools, which work for the instance being answered, else the active one
                    └───────────────────────────────────────────────────────────────────┘
```

The page and the local model exist with `bachmcp.server local` (`main.py run`). `bachmcp.server claude` (`main.py serve`) has Max and MCP, and no page: `claude -p` answers the prompts (section 6).

## The form of a line

| Rule | Example |
|---|---|
| Words separated by spaces | `set_active_instance scales1` |
| An instance's command starts with its name | `scales1 prompt "a scale"` |
| Text with spaces, `"` or `\` goes between double quotes, with `\"` and `\\` inside | `scales1 prompt "a \"tight\" canon"` |
| `prompt` joins every word after it, so Max may send the text unquoted | `scales1 prompt a scale that turns` |
| Numbers are written as they are | `scales1 done 1834 5200` |

Ports and the address are in `bachmcp.toml`: `[max] send_port` (3000, Python → Max), `[max] receive_port` (3001, Max → Python), `[server] port` (8090, the page and `/mcp`).

**Instance types:** `generator` · `transformer` · `selector` · `writer`

---

## 1. Inside Max

### `bachmcp.server` (its inlet)

| Message | What it does |
|---|---|
| `start` · `1` | starts the server, with the host given as first argument (`local` or `claude`) |
| `stop` · `0` | sends `bach quit` |
| `map_refresh` | sends the instance map again |
| `open` | opens the chat page in the browser |
| `debug 0/1` | prints every line from Python in the Max console |
| `install` · `install local` · `install claude` | runs `py/install.sh` |
| `model_catalog` | lists `models/catalog.toml` |
| `download <name\|repo\|link>` | downloads a model into `models/` |

| Outlet | What comes out |
|---|---|
| 0 | to `bach.roll`: `writetxt <package>/buffer.txt`, when Python asks for the score |
| 1 | an answer, as a dictionary: `instance`, `tokens`, `time`, `answer` |
| 2 | the output of `[shell]`: the server and the installer |

### Between the server and the instances

Two named sends connect every object in Max to the server's UDP objects:

| Name | Direction | What it carries |
|---|---|---|
| `[s bachmcp.server.s]` | to the server, then to Python | every line for Python, plus the two below |
| `[r bachmcp.server.r]` | from the server to every instance | every line from Python that does not start with `server`, plus the two below |

| Line | Sent by → to | What it does |
|---|---|---|
| `instance_names_map_update` | instance → server | an instance was named or renamed: the map must be sent again |
| `get_playground` | instance → server | asks for the playground path |
| `get_instance_names` | server → instances | each instance writes its name and type in `[dict bachmcp.instancenames.map]`; the server then sends the map to Python |
| `playground <path>` | server → instances | the playground path |

### Instance objects

Messages to the inlet of `bachmcp.algo.generate`, `.transform` and `.select`, and of the objects that contain them:

| Message | Generator | Transformer | Selector | What it does |
|---|:---:|:---:|:---:|---|
| `prompt <text>` | ✓ | ✓ | ✓ | sends `<name> prompt <text>` to Python |
| `name <name>` | ✓ | ✓ | ✓ | renames the instance |
| `bang` · `dump` · `run` | ✓ | ✓ | ✓ | runs with the current values |
| `param <param> <value...>` · `<param> <value...>` | ✓ | ✓ | ✓ | sets a parameter |
| `load <path>` · `load_algo <path>` · `try_load_algo <path>` · `reload` | ✓ | ✓ | ✓ | loads a file (`try_load_algo` is silent if it cannot) |
| `open` | ✓ | ✓ | ✓ | opens the algorithm's code |
| `write_to_playground` | ✓ | ✓ | ✓ | writes the last score to `scores/<name>.json` |
| `auto_dump 0/1` | ✓ | ✓ | ✓ | 1: output on every parameter change |
| `snap 0/1/3` | ✓ | ✓ | ✓ | output pitches: semitones, quarter tones, free |
| `bypass 0/1` · `repeat` | ✓ | ✓ | ✓ | scores pass through · the last output again |
| `verbose 0/1` · `watch 0/1` | ✓ | ✓ | ✓ | say what happens · reload when the file changes |
| `dictionary <dict>` · `input clear` | | ✓ | ✓ | a score in · forget the source |
| `source_mode 0/1` | | ✓ | ✓ | 0 destructive, 1 non-destructive |
| `capture` | | ✓ | ✓ | the next score in becomes the source |
| `process_only_selection 0/1` · `selection_slot <n>` | | ✓ | ✓ | work on the notes flagged in that slot |
| `dump_selection_only 0/1` · `dump_selection` · `clear_selection` | | | ✓ | what the selection outputs |

| Outlet | Generator | Transformer | Selector |
|---|---|---|---|
| score (`dictionary <name>`) | 0 | 0 | 0 |
| to `bach.roll` | — | 1: `dump` | 1: `dump`, `clearselection`, `sel note [v c n]` |
| to `bachmcp.gui.params` | 1 | 2 | 2 |
| dumpout: `algo_loaded <file> <notes> <ms>`, `algo_done <notes> <ms>`, `processing 0/1` | 2 | 3 | 3 |

`timeout` and `algo_error` are printed in the Max console instead. These status lines stay in Max: Python does not get them.

**The panel.** `bachmcp.gui.params` takes `spec`, `set`, `status`, `source`, `source_mode` and more from a runner's panel outlet, and sends `param <name> <value...>`, `bypass`, `repeat`, `snap`, `source_mode`, `capture` and `write_to_playground` back to its inlet. By hand: `set_name <name>`, `reset`, `bang`, `clear`, `autosize 0/1`.

**The prompt box.** `bachmcp.prompt` sends `prompt <text>` on Enter, the whole text as one symbol. By hand: `set <text>`, `append <text>`, `clear`, `bang`, `paste`.

**Translation.** `bachmcp.translate @from llll|t|json @to json|llll|t` takes a bach llll or `dictionary <name>`, and passes other messages through with `@transparent 1`.

---

## 2. Into Python

Max sends these to `[udpsend 127.0.0.1 3001]`. The page and the terminal send the same lines.

### Server commands

| Command | Arguments | What Python does | Sent by |
|---|---|---|---|
| `set_playground` | `<path>` (a Max path like `Macintosh HD:/…` works too) | creates `algorithms/`, `scores/` and `prompts/` if missing; everything the model makes goes there | `bachmcp.server` · terminal |
| `clear_instance_names_map` | — | empties the map | `bachmcp.server` · terminal |
| `add_instance_names_map` | `<name> <type>` | adds or updates one instance; the first one becomes the active instance | `bachmcp.server` · terminal |
| `set_active_instance` | `<name>` | the instance the menu shows and that Claude's tools work for | page · terminal · by hand, through `[s bachmcp.server.s]` (no object sends it) |

### Instance commands

| Command | Arguments | What Python does | Sent by |
|---|---|---|---|
| `<name> prompt` | `<text>` | queues a prompt for that instance's conversation | instance object · page · terminal |
| `<name> stop` | — | stops the answer being written, or removes the prompt from the queue | page · terminal |
| `<name> new` | — | starts a new conversation; the old one is kept as `prompts/<name>-<date>.jsonl` | page · terminal |

### Answers the tools wait for (Max → Python)

| Line | When | Sent by |
|---|---|---|
| `server buffer_done` | the score is in `buffer.json`, after `server write_buffer` | `bachmcp.server` |
| `<name> roll_written <file>` | its roll wrote `scores/<file>`, after `write_roll` | no object yet (writer) |

### Requests about Bach (Max → Python)

Each one is answered at once with `server …` lines (section 3).

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

## 3. Out of Python

Max gets these at `[udpreceive 3000]`. The page gets them through `/api/events`, and the terminal prints them.

**Echo rule:** Python never sends a line back to Max when it came from Max. A line from the page or the terminal goes to Max and to every page.

### Echoes of the server state

| Line | To Max | To the page |
|---|:---:|:---:|
| `set_playground <path>` | ✓ (if the page or terminal sent it) | ✓ |
| `clear_instance_names_map` | ✓ (if the page or terminal sent it) | ✓ |
| `add_instance_names_map <name> <type>` | ✓ (if the page or terminal sent it) | ✓ |
| `set_active_instance <name>` | ✓ (if the page or terminal sent it) | ✓ |

### Commands to an instance

File names are bare: they are in the playground.

| Line | What the instance does | Sent by the tool | Received in Max |
|---|---|---|---|
| `<name> load_algo <name>.js` | loads `algorithms/<name>.js` | `send_algorithm` | generator, transformer, selector |
| `<name> load_roll <name>.json` | its roll takes `scores/<name>.json` | `write_score` | no object yet (writer) |
| `<name> write_roll <name>.json` | its roll writes itself there and answers `roll_written` | no tool calls it now (`RollBuffer.fetch`) | no object yet (writer) |
| `<name> tonedivision <n>` | sets the microtonal grid before a load | `write_score` | no object yet (writer) |
| `<name> clear` | erases its roll | `clear_score` | no object yet (writer) |

### A conversation

| Line | Meaning | To Max | To the page |
|---|---|:---:|:---:|
| `<name> prompt <text>` | echo of a prompt | ✓ (if the page or terminal sent it) | ✓ |
| `<name> new` | echo: a new conversation | ✓ (if the page or terminal sent it) | ✓ |
| `<name> queued` | waits for another instance's answer (one model, one answer at a time) | ✓ | ✓ |
| `<name> thinking` | the model started | ✓ | ✓ |
| `<name> tool <tool> <first line of the result>` | a tool ran | ✓ | ✓ |
| `<name> answer <text>` | the whole answer, once | ✓ | ✓ |
| `<name> done <tokens> <ms>` | finished | ✓ | ✓ |
| `<name> stopped` | stopped by `stop` | ✓ | ✓ |
| `<name> error <message>` | refused or failed (no instance, no playground, no model …) | ✓ | ✓ |
| `<name> delta <text>` | a piece of the answer as it is written | — | ✓ |
| `<name> reasoning <text>` | a piece of the reasoning | — | ✓ |
| `<name> note <text>` | instrument docs added, a reply asked again | — | ✓ |
| `<name> tool_call <tool> <arguments as JSON>` | a tool call, in full | — | ✓ |
| `<name> tool_result <tool> <result>` | a tool's whole answer | — | ✓ |
| `<name> history <JSON>` | a saved conversation, sent when a page connects | — | ✓ |
| `state <state> <model> <message>` | the model's state: `starting`, `loading`, `ready`, `no_model`, `stopped`, `claude`, `off` | — | ✓ |

### Lines for the server object (Python → Max only, except `warning`)

Every one starts with `server`, so `bachmcp.server` routes on the second word and passes everything else to the instances.

| Line | When |
|---|---|
| `server status 1` | Bach started (sent unasked), and in answer to `bach status` |
| `server status 0` | Bach's last message before it goes off (sent unasked) |
| `server warning <text>` | anything to fix (bad path, unknown type, unknown instance …). The hub's warnings also reach the page |
| `server write_buffer` | a tool wants the score: `read_score`, `write_score`, or `send_algorithm` for a transformer or selector |
| `server prompt received` | a prompt from Max has arrived |
| `server answer <name> <text>` · `server answer tokens <n>` · `server answer time <ms>` | after each answer; they make the dictionary at outlet 1 |
| `server model <model>` | `bach status`, only when a model is loaded and answers |
| `server <section.key> <value>` … `server end settings <n>` | `bach settings` |
| `server models <name> <format> <GB> <in use 1/0>` … `server end models <n>` | `bach models` |
| `server catalog <name> <format> <GB> <downloaded 1/0> <repo> <note>` … `server end catalog <n>` | `bach catalog` |
| `server download_start <name> <GB>` · `download_progress <percent>` · `download_done <name>` · `download_error <message>` · `download_stopped <name>` | `bach download_model`, `bach download_stop` |
| `server help <requests…>` | `bach help` |
| `server pong` | `bach ping` |

---

## 4. The web page (`page.html`)

It holds nothing: it shows what Python says and turns each action into a line.

| The user does | The page sends (`POST /api/line`) |
|---|---|
| clicks an instance in the menu | `set_active_instance <name>` |
| types a message and presses Send | `<active> prompt "<text>"` |
| presses Stop | `<active> stop` |
| presses New chat | `<active> new` |

| HTTP | What it is |
|---|---|
| `GET /` | the page |
| `POST /api/line` | one line as the body; answers `{"ok": true}` or 400 `{"error": …}` |
| `GET /api/events` | the stream of lines: first the present (state, playground, map, active instance, saved conversations), then everything as it happens |
| `GET /api/state` | the model's state as JSON (the page's heartbeat) |

---

## 5. Claude (MCP)

Claude Code connects to `http://127.0.0.1:8090/mcp`, which `bachmcp.server claude` serves. Claude Desktop launches `main.py connect`, which answers it and passes each tool call to that same address. `main.py serve --stdio` is for a host that starts Bach itself.

A Claude you write to directly has no `prompt` line: its tools work for the **active instance**. While the hub answers a prompt from Max, they work for that prompt's instance. The instance's type decides what they accept.

| Tool | Arguments | For types | Sends to Max |
|---|---|---|---|
| `send_algorithm` | `code` | generator (`produce`), transformer (`transform`), selector (`select`) | (`server write_buffer` for a transformer or selector, to check on the score in the roll), then `<name> load_algo <name>.js` |
| `write_score` | `score`, `add` | writer | `server write_buffer`, (`<name> tonedivision`), `<name> load_roll <name>.json` |
| `read_score` | `voice`, `from_ms`, `to_ms` | any | `server write_buffer` |
| `clear_score` | — | writer | `<name> clear` |
| `p2mc` `mc2p` `get_midicents` `transpose` `reverse` `mirror` `force_scale` `get_chord` `get_scale` | pitch arguments | any | nothing (computed in Python) |

| Also offered to Claude | What |
|---|---|
| the server instructions | the skill (`BACH_SKILL.md`) |
| prompts `score`, `algo` | the two ways of working |
| resources `bach://skill`, `bach://docs/<instrument>` | the skill and the instrument docs |

With `main.py serve --stdio` the host is the model, so a prompt from Max is answered with `<name> error "no local model here: this Bach serves Claude through MCP"`.

---

## 6. Who answers a prompt (inside Python)

Not a separate part on the wire. With `bachmcp.server local`, the hub hands each prompt to the engine (`chat/engine.py`), which calls the tools in-process. With `bachmcp.server claude`, it starts one `claude -p` per prompt (`chat/headless.py`), which calls them over MCP and resumes the instance's session on the next prompt. The lines out are the same. Each instance's type fixes the mode and the tools.

| Type | Mode | Tools | The model writes |
|---|---|---|---|
| `generator` | algo | `send_algorithm` | `function produce(p)` |
| `transformer` | algo | `send_algorithm` | `function transform(source, p)` |
| `selector` | algo | `send_algorithm` | `function select(source, p)` |
| `writer` | score | `write_score` `read_score` `clear_score` + the pitch tools | the notes, as JSON |

---

## 7. Files that scores and products travel through

| File | Written by | Read by |
|---|---|---|
| `<package>/buffer.txt` | `bach.roll` (`writetxt`, after `server write_buffer`) | `bachmcp.server`, which converts it |
| `<package>/buffer.json` | `bachmcp.server`, as bachjson-complete | `read_score`, `write_score`, `send_algorithm`'s check |
| `<playground>/algorithms/<name>.js` | `send_algorithm` (after the check passes), or you | the instance (`load_algo`; it reloads when the file changes) |
| `<playground>/algorithms/.history/<name>-<date>.js` | `send_algorithm`, the version it replaced | you |
| `<playground>/scores/<name>.json` | `write_score`; an instance's `write_to_playground` | the writer's roll (not built) |
| `<playground>/prompts/<name>.jsonl` | the hub, one message per line, after each answer (with Claude, also its session id) | the hub, when the instance is next prompted or a page connects |
| `<playground>/prompts/<name>-<date>.jsonl` | `<name> new`, the conversation it put aside | you |
