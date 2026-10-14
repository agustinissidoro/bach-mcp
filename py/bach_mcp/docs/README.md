# Instrument docs

Reference for the model: one file per instrument, one `_family.md` per family.
Not wired in yet. The plan is that the gateway finds the files named in a
request and adds their relevant parts to the prompt, with no tool call.

Rules for every file:

- Every pitch is **sounding pitch in midicents** (6000 = middle C = C4), every
  time in milliseconds. Never written pitch, even for transposing instruments.
- Facts and possibilities, not advice: what the instrument can do, how it
  sounds and how to write it in the JSON score.
- JSON spellings (`"art"`, `"head"`) must be ones the translator accepts.
  `"text"` is free. `py/tests/test_docs.py` checks this.

## Instrument file

```markdown
---
aliases: [cello, violoncello, vc]   # names that find this file (lower case)
family: strings                     # the folder; its _family.md goes with it
---
# Cello

register: 3600–7600                 # usual range; sub-registers as a list below it
expanded_register: ...              # wider range, each part with its condition
transposing: no                     # or "yes: sounds 200 below written"
clefs: F; Tenor ..., G ...          # main clef; others and when they apply
techniques: the family techniques (strings/_family.md), plus:
- what is specific to this instrument, with its JSON spelling

## Harmonics
How they work, how to calculate them, the values, how to write them.
```

- **Core**: everything before the first `##`. Sent whenever the instrument is
  named, together with the family core. Keep it short.
- **Sections** (`## ...`): sent only when the request asks for them. Each one
  must stand alone, since it can be sent without the core.
- `clefs:` is read by the code, not sent to the model: bach.roll has one clef
  per voice, so clef changes cannot be written; the line says which clef suits
  a voice depending on where its notes lie.
- When names overlap ("flute" and "alto flute"), the longest alias wins.

## Family file

`_family.md` has the same front matter. Its core holds what all members share:
the techniques with their JSON spellings, how articulations are produced, and
the constraints common to the family.
