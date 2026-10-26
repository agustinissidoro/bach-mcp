---
aliases: [double bass, double basses, contrabass, contrabasses, string bass, upright bass, cb, contrabbasso, contrebasse, contrabajo, kontrabass]
family: strings
---
# Double bass

register: 2800–5500
- 2800–3800 (E and A strings): the deepest string sound; slow to speak, blurred in fast passages
- 3800–5000 (D and G strings): clearer and more melodic
- 5000–5500: high, singing, close to the cello's tenor register
expanded_register: 2400–2800 only with a low C extension (common on orchestral basses) or 2300 on a five-string bass; 5500–6700 in solo writing (thumb position). Natural harmonics reach higher (see Harmonics).
transposing: yes: sounds 1200 below written. Every value here is sounding pitch; write sounding pitch.
clefs: F8vb; G8vb for high solo passages and harmonics
techniques: the string-family techniques (strings/_family.md), plus:
- open strings 2800 3300 3800 4300, tuned in fourths
- pizz. is natural and resonant, ringing about 1–3 s in the low register
- slap pizz., the string slapped against the fingerboard: "text": "slap pizz."
- double stops are limited: mostly an open string with a stopped note
- low notes take time to speak: fast passages are clearer in the upper register

## Harmonics
A natural harmonic is a partial of an open string, played by touching the
string lightly at a node. Partial n sounds at the open string + 1200·log2(n):
2 → +1200, 3 → +1902, 4 → +2400, 5 → +2786, 6 → +3102, 7 → +3369, 8 → +3600.

```
string   partial 2     3     4     5     6     7     8
2800              4000  4702  5200  5586  5902  6169  6400
3300              4500  5202  5700  6086  6402  6669  6900
3800              5000  5702  6200  6586  6902  7169  7400
4300              5500  6202  6700  7086  7402  7669  7900
```

The long strings make harmonics easy and rich: partials 2 to 8, and higher,
are playable. The 7th partial sounds 31 cents below the tempered note. Artificial
harmonics are rare; natural ones are preferred. Harmonics are soft and pure, and
much lighter than the stopped notes.

Write the sounding pitch with "art": "harmonic"; bach plays the written pitch,
so the score sounds right. A harmonic glissando (the finger sliding lightly
along the string) is a fast run of these partials, about 40–80 ms apart.
