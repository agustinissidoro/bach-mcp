---
name: bach-mcp
description: >
  Essential knowledge for working with bach.roll in Max/MSP via the Bach MCP server.
  Read at session start and whenever constructing llll strings, configuring voices/clefs,
  or interpreting dump() output.
---

# Bach MCP Skill

## SESSION PROTOCOL

Start every session with `dump(mode="body")`. Before editing, always dump first.
Skip only when the user has just told you the exact state.

- Notes/chords/voices → `dump(mode="body")`
- Clefs/voicenames → `dump(mode="header")`
- ⚠️ Never invent score contents. If dump times out, say so and retry.

---

## LLLL SCORE SYNTAX

Hierarchy (inside out):

```
NOTE   [ pitch_cents  duration_ms  velocity  [specs...]  flag ]
CHORD  [ onset_ms  NOTE  NOTE ...  flag ]
VOICE  [ CHORD  CHORD ...  flag ]
SCORE  roll [VOICE1] [VOICE2] ...
```

- `pitch_cents`: middle C = 6000, one semitone = 100. C4=4800 D5=6200 E5=6400 G5=6700 A5=6900
- `flag`: 0=normal 1=locked 2=muted 4=solo. Usually 0, may be omitted.
- `specs`: optional, between velocity and flag — `[breakpoints...]` `[slots...]` `[name...]`

⚠️ Voices are SEPARATE top-level lllls — never nest them in an extra bracket.
```
RIGHT: roll [VOICE1] [VOICE2]
WRONG: roll [ [VOICE1] [VOICE2] ]
```

### Examples

```
# One note — C5, 500ms, vel 100
roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ]

# Two notes in sequence
roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] [ 500. [ 6200. 500. 100 0 ] 0 ] 0 ]

# Chord — C+E at 0ms
roll [ [ 0. [ 6000. 1000. 100 0 ] [ 6400. 1000. 100 0 ] 0 ] 0 ]

# Two voices
roll [ [ 0. [ 6000. 500. 100 0 ] 0 ] 0 ] [ [ 0. [ 4800. 500. 90 0 ] 0 ] 0 ]
```

---

## SLOTS

Per-note data containers. Default slots: **20**=dynamics, **22**=articulations, **23**=notehead.

```
[slots [slot_number CONTENT] [slot_number CONTENT] ...]
```

### Dynamics (slot 20)
Symbols: `pp p mp mf f ff fff sfz o` (o = niente)
Hairpins: `<` cresc, `>` dim, `<<` exp cresc, `>>` exp dim, `=` steady, `|` end at tail

```
[slots [20 f]]          # forte
[slots [20 p<]]         # cresc from p (continues to next note)
[slots [20 p<|]]        # cresc ending at this note's tail
[slots [20 o<<f>>o]]    # dal niente → f → al niente
```
Multi-note cresc: note1 `[slots [20 p<]]` / note2 `[slots [20 f]]`

### Articulations (slot 22)
Common: `staccato` `accent` `fermata` `trill` `portato` `martellato`
         `upbowing` `downbowing` `tremolo1` `tremolo2` `tremolo3`
Shortcuts: `stacc` `acc` `ferm` `tr` `port` `mart` `ubow` `dbow` `trem1/2/3`
Multiple: space-separated — `[slots [22 staccato accent]]`

### Noteheads (slot 23)
`default` `diamond` `cross` `white` `black` `whole` `doublewhole` `none` `plus`
`blacksquare` `whitesquare` `blacktriangle` `whitetriangle`

### Combining
```
[slots [23 diamond] [22 trill] [20 mp]]   # harmonics + trill + mp
[slots [22 staccato] [20 p<]]             # staccato + cresc
```

### Breakpoints (glissandi)
```
[breakpoints [0 0 0] [rel_x delta_cents slope] ... [1 delta_cents slope]]
```
- First point always `[0 0 0]`, last always starts with `1`
- `delta_cents`: offset from base pitch; `slope`: -1 to 1 (0=linear)

```
[breakpoints [0 0 0] [1 200 0]]    # gliss up 200 cents
```

---

## LAYOUT — VOICES / STAVES / PARTS

- **VOICE** = one musical stream. One entry in clefs/voicenames/numvoices.
- **STAFF** = visual line. Multi-staff clefs (FG, FFGG) give one voice multiple staves.
- **PART** = bracket group. Sum of numparts must equal numvoices.

Common clefs: `G` treble, `F` bass, `Alto`, `Tenor`, `Percussion` (full word, capital P)
Multi-staff: `FG` = grand staff (1 voice, 2 staves). `FFGG` = choir (1 voice, 4 staves).

Piano: `clefs("FG") numvoices(1) numparts("1")` — one voice, grand staff.
Two independent hands: `clefs("G F") numvoices(2) numparts("2")`

⚠️ Layout tools (`numvoices`, `clefs`, `numparts`, `stafflines`, `voicenames`) **delete content** if called on an existing score. Only call them when the user explicitly changes instrumentation or on a fresh score.
- Read voice count → `getnumvoices()`
- Read layout → `dump(mode="header")`

---

## BELL CODE (bach.eval)

Use `send_bell_to_eval()` **only when**:
- The user explicitly asks for bell code, or
- You judge that algorithmic generation is clearly the right fit and you **suggest it first**.

For everything else, use `send_score_to_max()`.

The tool prepends `"bell "` to the code so the patch can route it to `bach.eval`
separately from regular `roll` llll messages.

---

### ⚠️ FLAT STRING — PARENTHESES ARE THE ONLY SCOPE MECHANISM

Bell has **no indentation, no blocks, no `end` keyword**. Hierarchy and scope are expressed exclusively through `( )`.

Bell code is sent as a **single flat string** through Max messaging — no newlines, no indentation.
Statements are separated by `;`. Wherever you need to group multiple statements (loop bodies, nested expressions, precedence), use `( )`.

```
RIGHT: for $p in [6000 6200 6400] do ($v _= [$t [$p 500. 100 0] 0]; $t += 500.)
WRONG: for $p in [6000 6200 6400] do
           $v _= [$t [$p 500. 100 0] 0];    ← no newlines, no indentation
           $t += 500.
       end                                    ← no end keyword
```

---

### Symbols — SINGLE QUOTES ONLY

Symbols must use **single quotes**: `'roll'`, `'null'`, `'foo'`.
Double quotes are not correct bell syntax (Max artefact).

```
RIGHT: 'roll' [$v 0]
WRONG: "roll" [$v 0]
```

---

### Variables

Local variables: `$name`. Only one assignment operator: `=`.
The `;` sequences statements and returns the last value.

```
$side = 5; $area = $side * $side; $area
```

Reserved (cannot use as variable names): `$x1 $x2 ... $xN`, `$i1 $r1 $f1 $p1 $o1`, `$args`, `$argcount`.

---

### Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `=` | assignment | `$x = 5` |
| `+` `-` `*` `/` `%` | arithmetic | standard precedence |
| `==` `!=` `<` `>` `<=` `>=` | comparison | returns 1 or 0 |
| `&&` `\|\|` | boolean (short-circuit) | `$x > 0 && $x < 10` |
| `&&&` `\|\|\|` | conditional boolean (returns values) | `$a \|\|\| 'default'` |
| `,` | llll concatenation | `$v , [$t [$p 500. 100 0] 0]` |
| `_=` | append-assign | `$v _= x` → same as `$v = $v , x` |
| `+=` `-=` `*=` `/=` | compound assign | `$x += 1` |
| `:` | element retrieval (1-indexed) | `$x:2` → 2nd element |
| `::` | pick/unwrap sublist | `$x::2` → contents of 2nd sublist |
| `.` | key access | `$list.john` → value after key `john` |
| `...` | range (inclusive) | `1...5` → `1 2 3 4 5` |
| `:*` | repeat | `'foo' :* 3` → `'foo' 'foo' 'foo'` |
| `;` | sequence | evaluates both, returns second |

**Unary minus:** no space between `-` and its operand.
- `$x -10` → concatenation of `$x` and `-10`
- `$x-10` → subtraction

**Implicit list construction:** values side by side assemble into an llll.
`'foo' $x 'bar'` → llll of three elements.

**Precedence:** arithmetic > concatenation. Use parens liberally.

---

### Conditionals

```
if <cond> then <expr>
if <cond> then <expr> else <expr>
if <cond> then <expr> else if <cond> then <expr> else <expr>
```

Truthiness: `null` and `0` are false; everything else is true.
⚠️ Use parens with nested ifs to avoid dangling-else ambiguity.

---

### Loops

**`while ... do`** — repeat while condition true, return last body value:
```
$i = 0; while $i < 8 do $i += 1
```

**`while ... collect`** — collect all body values into an llll:
```
$i = 0; while $i < 8 collect ($i += 1)
```

**`for $x in <llll> do`** — iterate llll elements, return last body value:
```
for $p in [6000 6200 6400 6500] do $p
```

**`for $x in <llll> collect`** — iterate and collect all body values:
```
for $p in [6000 6200 6400 6500] collect $p + 100
```

**Range iteration** with `...`:
```
for $i in 1...16 collect $i * 100
```

**Multi-statement body** — wrap in `( )`:
```
$t = 0.; $v = 'null'; for $p in [6000 6200 6400] do ($v _= [$t [$p 500. 100 0] 0]; $t += 500.); $v
```

**Parallel iteration** (stops at shortest llll):
```
for $x in $x1, $y in $x2 collect $x + $y
```

**Address variable** (second name receives the index):
```
for $data $addr in $x1 collect $data + $addr
```

**`as` clause** — stop when condition becomes false:
```
for $x in $x1 as $x < 100 collect $x
```

---

### Score output from bell

The **last expression** is what `bach.eval` outputs.
For score generation it must be a valid roll llll, starting with the symbol `'roll'`.

```
$v = 'null'; $t = 0.; for $p in [6000 6200 6400 6500 6700] do ($v _= [$t [$p 500. 100 0] 0]; $t += 500.); 'roll' [$v 0]
```

---

### Pitch arithmetic

Middle C = 6000. Semitone = 100. Octave = 1200.
Fifth up = `$p + 700`. Octave down = `$p - 1200`.
Random chromatic pitch: `round(random(6000, 7200) / 100) * 100`

---

### Ready-to-send flat patterns

**C-major scale, one voice:**
```
$v = 'null'; $t = 0.; for $p in [6000 6200 6400 6500 6700 6900 7100 7200] do ($v _= [$t [$p 500. 100 0] 0]; $t += 500.); 'roll' [$v 0]
```

**16 random chromatic pitches:**
```
$v = 'null'; $t = 0.; for $i in 1...16 do ($p = round(random(6000, 7200) / 100) * 100; $v _= [$t [$p 250. 90 0] 0]; $t += 250.); 'roll' [$v 0]
```

**Serial row (12 pitches):**
```
$row = [0 2 4 5 7 9 11 1 3 6 8 10]; $v = 'null'; $t = 0.; for $pc in $row do ($v _= [$t [($pc * 100 + 6000) 400. 100 0] 0]; $t += 400.); 'roll' [$v 0]
```

**Two voices:**
```
$v1 = 'null'; $v2 = 'null'; $t = 0.; for $p in [6700 6900 7100 6700] do ($v1 _= [$t [$p 500. 100 0] 0]; $t += 500.); $v2 _= [0. [4800. 2000. 80 0] 0]; 'roll' [$v1 0] [$v2 0]
```

**Fibonacci sequence as rhythm (8 terms):**
```
$fibo = 1 1; while length($fibo) < 8 do $fibo _= ($fibo:-1 + $fibo:-2); $v = 'null'; $t = 0.; for $dur in $fibo do ($v _= [$t [6000. ($dur * 200.) 100 0] 0]; $t += $dur * 200.); 'roll' [$v 0]
```

### Slots in bell
Embed slot llll directly inside the note — same syntax as raw llll:
```
$v _= [$t [$p 500. 100 [slots [22 staccato] [20 f]] 0] 0]
```

---

⚠️ Bell runs inside Max — syntax errors are silent from the MCP side.
After sending, always `dump(mode="body")` to confirm the score was generated correctly.

---

## SCORE WRITING

- `send_score_to_max()` — **primary tool**. Replaces entire score content.
- `addchord()` / `addchords()` — add to existing score without replacing it.
- `add_single_note()` — convenience only, avoid for real work.
- `send_process_message_to_max()` — escape hatch for commands with no dedicated tool.

---

## MEMORY

Call `project_memory_read("project_name")` at the start of any session where the user mentions a project by name. It returns intent, workflow, notes, and voice roles from previous sessions.

Call `project_memory_write(...)` when:
- The user states what they want the piece to feel or be
- The approach or technique changes
- You learn something worth remembering (voice assignments, structural decisions, constraints)

Only write fields that are actually new or changed. Fields not supplied are preserved.

```
project_memory_read("")                  # list all known projects
project_memory_read("symphony_no1")      # read one project
project_memory_write(
    project="symphony_no1",
    intent="brooding, late-romantic, through-composed",
    workflow="building by voice — strings first, then winds layered in",
    notes="voice 1=violin I, voice 2=violin II, voice 3=viola, voice 4=cello"
)
```

---

## SCORE SNAPSHOT

Call `score_snapshot()` when:
- You have made several edits and want to visually verify the result
- Something seems wrong and you can't tell why from the llll alone
- The user asks to see the score

Do NOT call it after every single action — only when visual confirmation is genuinely needed. The image is returned as base64 and saved to `assets/screenshots/`.
