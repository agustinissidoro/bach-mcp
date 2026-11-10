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
  Claude ──MCP──► the 15 tools: for the active instance (the Claude Code Bach starts: its prompt's)
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
| An instance cannot be named like a line's first word: `server`, `bach`, `state`, `instances`, `set_playground`, `set_active_instance`, `add_instance_names_map`, `clear_instance_names_map` | `server warning "an instance cannot be named server: rename it"` |

Ports and the address are in `bachmcp.toml`: `[max] send_port` (3000, Python → Max), `[max] receive_port` (3001, Max → Python), `[server] port` (8090, the page and `/mcp`).

**Instance types:** `generator` · `transformer` · `selector` · `writer`

---

## 1. Inside Max

The patches were not opened for this map. What is said here of `bachmcp.server` and of the named sends is as it was last written down; the runner and the panel are as their JavaScript is now.

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

Python can also ask for the map: `server get_instances` (section 3) is answered with `instances <name> <type> ...` (section 2).

### Instance objects

One object for every type: `bachmcp.algorithm` (and `bachmcp.bpatcher.algorithm`, which holds it with its panel). `prompt`, `name` and `open` are the patch's; everything else is a message of `[v8 bachmcp.runner.js <type>]`, whose header is the full list.

| Message | Generator | Transformer | Selector | What it does |
|---|:---:|:---:|:---:|---|
| `prompt <text>` | ✓ | ✓ | ✓ | sends `<name> prompt <text>` to Python |
| `name <name>` · `open` | ✓ | ✓ | ✓ | renames the instance · opens the algorithm's code |
| `type generator\|transformer\|selector` | ✓ | ✓ | ✓ | what the runner is from now on; a loaded file must be of the new type |
| `set_name <name> [file]` | ✓ | ✓ | ✓ | the name the runner reports with (and a file to load) |
| `load <path>` · `load_algo <path>` · `try_load_algo <path>` · `reload` | ✓ | ✓ | ✓ | loads a file (`try_load_algo` is silent if it cannot). A load is not a run |
| `bang` · `dump` | ✓ | ✓ | ✓ | the score of the current settings: the last one again if nothing changed, else a run |
| `run` · `repeat` | ✓ | ✓ | ✓ | runs now, changed or not · the last score again |
| `param <param> <value...>` | ✓ | ✓ | ✓ | sets a parameter. A bare `<param> <value...>` is refused |
| `get_specs` | ✓ | ✓ | ✓ | the spec to the panel again; answers `<name> specs 1/0` |
| `sync <message...>` | ✓ | ✓ | ✓ | the panel's values after a load, applied without a run |
| `auto_dump 0/1` | ✓ | ✓ | ✓ | 1: output on every parameter change |
| `snap 0/1/3` | ✓ | ✓ | ✓ | output pitches: semitones, quarter tones, free |
| `bypass 0/1` | ✓ | ✓ | ✓ | scores at the inlet pass through, runs do nothing |
| `write_to_playground` | ✓ | ✓ | ✓ | writes the last score to `scores/<name>.json` |
| `verbose 0/1` · `watch 0/1` | ✓ | ✓ | ✓ | say what happens · reload when the file changes |
| `source_mode 0/1` | kept | ✓ | ✓ | 0 destructive, 1 non-destructive |
| `process_only_selection 0/1` | kept | ✓ | ✓ | 1: work only on the selected notes (bach's flag 16) |
| `dump_selection_only 0/1` | kept | kept | ✓ | the score out: only the selected notes, or the whole source flagged |
| `involutive 0/1` | kept | kept | kept | kept for later: ignored for now |
| `dictionary <name>` | only while bypassed | ✓ | ✓ | a score in |
| `input clear` | | ✓ | ✓ | forget the source |
| `capture` | | ✓ | ✓ | asks the roll for its score; the next one in becomes the source |
| `dump_selection` · `clear_selection` | | | ✓ | the selected notes as a score · nothing selected |

"kept": every runner takes the setting and keeps it across a type change; that type does not use it. Old names still taken: `input_mode` (now `process_only_selection`), `input dictionary <name>` (now `dictionary <name>`), `selection_slot` (ignored).

The runner's outlets are the same for every type:

| Outlet | What comes out |
|---|---|
| 0 | the score: `dictionary <name>` (bachjson-complete) |
| 1 | to `bach.roll`: `dump`, `clearselection`, `sel note [v c n] ...` (a generator sends nothing here) |
| 2 | to `bachmcp.gui.params` |
| 3 | `bang`: a process is done, after its score |
| 4 | dumpout, each line starting with the name: `<name> algo_loaded <file>`, `algo_done <notes> <ms>`, `algo_error <message>`, `error <message>`, `processing 0/1`, `timeout 1`, `specs 0/1` |

Errors are also printed in the Max console. These status lines stay in Max: Python does not get them.

**The panel.** `bachmcp.gui.params` takes from the runner's outlet 2: `spec <JSON>`, `set <param> <value...>`, `status ok|error <text>`, `type`, `clear`, and each setting's value back (`bypass`, `snap`, `source_mode`, `process_only_selection`, `dump_selection_only`, `involutive`, `auto_dump`). It sends to the runner's inlet: `param <name> <value...>`, `sync <message...>` after each spec, `bypass`, `repeat`, `snap`, `source_mode`, `process_only_selection`, `dump_selection_only`, `capture`, `write_to_playground`, and `set_as_active_instance`, which is for the patch (the runner does not take it). From the server, for its instance: `prompt <stage> [detail]` draws the prompt's progress. By hand: `set_name <name>`, `set_type <type>`, `one_line_description <text>`, `reset`, `bang`, `clear`, `autosize 0/1`.

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
| `set_active_instance` | `<name> [<type>]` | the instance the menu shows and that Claude's tools work for; with the type, an instance not yet in the map joins it | Max · page · terminal · the tool `set_active_instance` |
| `instances` | `<name> <type> ...` | Max's whole map, in answer to `server get_instances`: it replaces Python's | Max |

### Instance commands

| Command | Arguments | What Python does | Sent by |
|---|---|---|---|
| `<name> prompt` | `<text>` | queues a prompt for that instance's conversation | instance object · page · terminal |
| `<name> stop` | — | stops the answer being written, or removes the prompt from the queue | page · terminal |
| `<name> new` | — | starts a new conversation; the old one is kept as `prompts/<name>-<date>-<time>.jsonl`. An instance that changes type starts one too | page · terminal |

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
| `<name> tool <tool> <first line of the result>` | a tool ran | ✓ | ✓ |
| `<name> answer <text>` | the whole answer, once | ✓ | ✓ |
| `<name> done <tokens> <ms>` | finished | ✓ | ✓ |
| `<name> stopped` | stopped by `stop` | ✓ | ✓ |
| `<name> error <message>` | refused or failed (no instance, no playground, no model …) | ✓ | ✓ |
| `<name> thinking` | its turn started (Max gets `server prompt <name> starting` instead) | — | ✓ |
| `<name> delta <text>` | a piece of the answer as it is written | — | ✓ |
| `<name> reasoning <text>` | a piece of the reasoning | — | ✓ |
| `<name> note <text>` | instrument docs added, a reply asked again | — | ✓ |
| `<name> tool_call <tool> <arguments as JSON>` | a tool call, in full | — | ✓ |
| `<name> tool_result <tool> <result>` | a tool's whole answer | — | ✓ |
| `<name> history <JSON>` | a saved conversation, sent when a page connects | — | ✓ |
| `state <state> <model> <message>` | the model's state: `starting`, `loading`, `ready`, `no_model`, `stopped`, `claude`, `off` | — | ✓ |

### What happens to a prompt (to Max and the page)

Whoever sent the prompt. A stage is said once, when it changes.

| Line | Meaning |
|---|---|
| `server prompt <name> received` | Bach has it |
| `server prompt <name> queued <n>` | `<n>` prompts are answered before it |
| `server prompt <name> starting` | its turn: the model is being set up (Claude Code starts) |
| `server prompt <name> sent` | the model has the prompt, and later each tool's answer |
| `server prompt <name> thinking` · `writing` | it reasons · it writes the answer |
| `server prompt <name> calling <tool>` | it writes a tool call |
| `server prompt <name> running <tool>` | the tool runs, in Bach |
| `server prompt <name> done <tokens> <ms>` · `stopped` · `error <message>` | how it ended |

### Lines for the server object (Python → Max only, except `warning`)

Every one starts with `server`, so `bachmcp.server` routes on the second word and passes everything else to the instances.

| Line | When |
|---|---|
| `server status 1` | Bach started (sent unasked), and in answer to `bach status` |
| `server status 0` | Bach's last message before it goes off (sent unasked) |
| `server warning <text>` | anything to fix (bad path, unknown type, unknown instance …). The hub's warnings also reach the page |
| `server write_buffer` | a tool wants the score: `read_score`, `write_score`, or `send_algorithm` for a transformer or selector |
| `server get_instances` | the tools `get_instances` and `set_active_instance` ask for the map; Max answers `instances <name> <type> ...` within 1.5 s, else the last map is used |
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

Claude Code connects to `http://127.0.0.1:8090/mcp`, which `bachmcp.server claude` serves. The `claude -p` that Bach starts for a prompt connects to `/mcp/headless/score` or `/mcp/headless/algo` instead: that mode's tools only, no instructions. Claude Desktop launches `main.py connect`, which answers it and passes each tool call to that same address, over one session it keeps open (and opens again by itself when Bach restarts). `main.py serve --stdio` is for a host that starts Bach itself.

A Claude you write to directly has no `prompt` line: its tools work for the **active instance**, which it can list and choose with `get_instances` and `set_active_instance`, also while a prompt from Max is being answered for another instance. The Claude Code that Bach starts for a prompt works for that prompt's instance. The instance's type decides what the tools accept.

No tool runs on the server's event loop: each call has its own thread, so the page and the other sessions go on while one waits for Max or for Node. They still run one at a time, since they share Max's answers.

| Tool | Arguments | For types | Sends to Max |
|---|---|---|---|
| `send_algorithm` | `code` | generator (`produce`), transformer (`transform`), selector (`select`) | (`server write_buffer` for a transformer or selector, to check on the score in the roll), then `<name> load_algo <name>.js` |
| `write_score` | `score`, `add` | writer | `server write_buffer`, (`<name> tonedivision`), `<name> load_roll <name>.json` |
| `read_score` | `voice`, `from_ms`, `to_ms` | any | `server write_buffer` |
| `clear_score` | — | writer | `<name> clear` |
| `p2mc` `mc2p` `get_midicents` `transpose` `reverse` `mirror` `force_scale` `get_chord` `get_scale` | pitch arguments | any | nothing (computed in Python) |
| `get_instances` | — | any (not in an instance's own conversation) | `server get_instances` |
| `set_active_instance` | `name` | any (not in an instance's own conversation) | `set_active_instance <name>`, and `server get_instances` if the name is not in the map |

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
| `<playground>/prompts/<name>-<date>-<time>.jsonl` | `<name> new` or a change of type: the conversation put aside | you |
