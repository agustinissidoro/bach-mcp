# bachjson-complete — declaration

// this is a 1:1 translation of bach-lll syntax to json

```jsonc
{
  "header": {                                  // each element optional: present when bach writes it
    "slotinfo": {                              // by slot number "1" … "30"
      "1": { "<field>": [ … ] }                // free content. fields: name, type, range, slope, representation,
    },                                         // grid, ysnap, zsnap, domain, domainslope, color, default,
                                               // temporalmode, extend, width, height, copywhensplit, access,
                                               // follownotehead, key …
    "commands": {                              // by command number "1" … "30"
      "1": { "<field>": [ … ] }                // free content. fields: note, chord, rest, key
    },
    "clefs":        [ string ],                // one per voice, e.g. "G"
    "keys":         [ string ],                // one per voice, e.g. "CM"
    "voicenames":   [ [ string | integer | float ] ],  // one per voice: its names, [] for none
    "voicespacing": [ float ],                 // voices + 1
    "hidevoices":   [ integer ],               // one per voice, 0/1
    "groups":       [ [ [ integer, integer ] ] ],  // each group: its chords as [voice, chord], 1-based
    "markers": [
      {
        "onset": float,                        // ms
        "name": [ string | integer | float ],  // [] for none
        "role": string,                        // none | tempo | timesig | barline | division | subdivision
        "content": [ … ]                       // free content, only when role is not none
      }
    ],
    "stafflines":   [ integer | [ integer ] ],  // one per voice: a count, or the line positions
    "midichannels": [ integer ],               // one per voice
    "articulationinfo": [ [ … ] ],             // free content, one per custom articulation
    "noteheadinfo":     [ [ … ] ],             // free content, one per custom notehead
    "numparts":     [ integer ],
    "loop":         [ float, float ]           // start ms, end ms
  },

  "voices": [
    {
      "chords": [
        {
          "onset": float,                      // ms
          "notes": [
            {
              "pitch": float,                  // midicents, 6000 = middle C
              "spelling": string,              // optional: bach's spelled pitch, e.g. "Db5" (middle C = C5)
              "dur": float,                    // ms
              "vel": integer,                  // 1 … 127
              "graphic": [ … ],                // optional, free content (old files)
              "breakpoints": [                 // optional: first [0, 0, 0], last at x = 1
                [ float, float, float ]        // x, delta midicents, slope; or with a 4th: velocity
              ],
              "slots": {                       // optional, by slot number "1" … "30"
                "20": [ … ]                    // free content: the slot's items, meaning by its type in slotinfo
              },
              "articulations": [ string ],     // optional, e.g. "staccato"
              "name": [ string | integer | float ],  // optional
              "flag": integer                  // 1 locked + 2 muted + 4 solo
            }
          ],
          "name": [ string | integer | float ],  // optional
          "flag": integer
        }
      ],
      "flag": integer
    }
  ]
}
```
