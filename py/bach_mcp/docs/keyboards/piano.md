---
aliases: [piano, pianos, pianoforte, grand piano, upright piano, pno, pf, klavier, flügel]
family: keyboards
---
# Piano

register: 2100–10800
- 2100–3600 low: deep and long-ringing; close chords sound thick
- 3600–8400 middle: full and even, the core of the instrument
- 8400–10800 high: bright, with a short decay; above about 9000 the strings have no dampers, so notes ring on after release
expanded_register: none on a standard 88-key piano. Some Bösendorfer models extend the bass down to 1700 or 1200.
transposing: no
clefs: FG; FFG when the left hand stays below about 3600, FGG when the right hand stays above about 9600, FFGG for both
techniques:
- every note has a fixed attack and then decays: no crescendo or diminuendo on a held note; shape loudness from note to note with "vel"
- a note sounds for its "dur" in this score; to mimic the sustain pedal, lengthen the durations and write "text": "ped." where it goes down
- una corda (soft pedal): "text": "una corda"; back with "text": "tre corde"
- sostenuto pedal: "text": "sost. ped."
- staccato: "art": "staccato"; accent: "art": "accent"; tenuto: "art": "tenuto"; marcato: "art": "marcato"
- trill: "art": "trill"; repeated-note or chord tremolo: "art": "tremolo"
- glissando: a fast run over the white (or black) keys; write each note, about 15–30 ms apart. A continuous "gliss" is impossible on the piano
- clusters, adjacent keys pressed with the palm or forearm: a chord of every semitone, or of the white keys only, within the span
- silently pressed keys: "head": "diamond" with "vel": 1 (see Harmonics)
- inside the piano: plucked string "text": "pizz."; string muted by a finger while the key is played: "head": "cross" with "text": "muted"
- hands: one hand spans about 1200 (an octave), large hands 1400–1600, at most five notes per hand; a chord must split into two hands, each within its span; wider chords are arpeggiated
- repeated notes on one key up to about 12–15 per second

## Harmonics
Both techniques use the harmonic series of a string: partial n sounds at its
pitch + 1200·log2(n): 2 → +1200, 3 → +1902, 4 → +2400, 5 → +2786, 6 → +3102.

Silent keys (sympathetic resonance): a key held down without sound lifts its
damper. A short, loud note whose partial matches the held string makes it ring
on. With equal-tempered keys: a held key 1200, 1900, 2400, 2800 or 3100 above
the struck note rings; +1200 and +2400 match exactly and ring strongest, +2800
is 14 cents off and weaker. Write the held key with "head": "diamond" and
"vel": 1 (almost silent in bach), starting before the struck note and lasting
as long as the resonance should sound; the struck note short and loud ("art":
"staccato", "dyn": "ff").

Touched harmonics (inside the piano): a finger touches the string lightly at a
node while the key is played, and the string sounds partial n: touching at 1/2
of its length gives +1200, at 1/3 +1902, at 1/4 +2400, at 1/5 +2786. Easiest on
the low wound strings, below about 4800. Write the sounding pitch with "art":
"harmonic" and "text": "touch node".
