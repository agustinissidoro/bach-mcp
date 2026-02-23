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
- You judge that algorithmic generation is clearly the right fit and you **suggest it first** — e.g. "I could write this as bell code that loops — want that instead?"

For everything else, use `send_score_to_max()`.

The tool prepends `"bell "` to the code so the patch can route it to `bach.eval`
separately from regular `roll` llll messages.

### Bell basics

Variables use `$` prefix. Statements end with `;`. Assignment: `:=` (declare), `=` (update).
The last expression in the program is the output — it should be a valid roll score.

```bell
$t := 0.;
$voice := null;
for $p in [6000 6200 6400 6500 6700 6900 7100 7200] do
    $voice = $voice , [$t [$p 500. 100 0] 0];
    $t = $t + 500.;
end;
"roll" [$voice 0]
```

### Pitch arithmetic
Middle C = 6000. Semitone = 100. Octave = 1200.
`$p + 700` = fifth up. `$p - 1200` = octave down.
`round(random(6000, 7200) / 100) * 100` = random chromatic pitch in range.

### Useful patterns

**Random chromatic pitches:**
```bell
$voice := null; $t := 0.;
for $i from 1 to 16 do
    $p := round(random(6000, 7200) / 100) * 100;
    $voice = $voice , [$t [$p 250. 90 0] 0];
    $t = $t + 250.;
end;
"roll" [$voice 0]
```

**Serial row:**
```bell
$row := [0 2 4 5 7 9 11 1 3 6 8 10];
$t := 0.; $voice := null;
for $pc in $row do
    $voice = $voice , [$t [($pc * 100 + 6000) 400. 100 0] 0];
    $t = $t + 400.;
end;
"roll" [$voice 0]
```

**Multi-voice:**
```bell
$v1 := null; $v2 := null; $t := 0.;
for $p in [6700 6900 7100 6700] do
    $v1 = $v1 , [$t [$p 500. 100 0] 0];
    $t = $t + 500.;
end;
$v2 := [[0. [4800. 2000. 80 0] 0] 0];
"roll" [$v1 0] $v2
```

### Slots in bell
Same syntax as raw llll — embed directly in the note list:
```bell
$note := [$p 500. 100 [slots [22 staccato] [20 f]] 0];
```

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
