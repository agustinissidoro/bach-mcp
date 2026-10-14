---
aliases: [strings, string section, string orchestra, string quartet, string trio, bowed strings]
family: strings
---
# Bowed strings (violin, viola, cello, double bass)

Four strings, tuned in fifths (the double bass in fourths), bowed (arco) or
plucked (pizz.). Fretless: any pitch between semitones is playable exactly, so
quarter-tones and other microtones are written as plain midicents.

techniques:
- arco (bowed, the default): "text": "arco" to return from another technique
- pizzicato: "text": "pizz."; a plucked note that decays: lower notes ring longer
- left-hand pizzicato: "art": "lefthandpizzicato"
- snap (Bartók) pizzicato, string slapping the fingerboard: "text": "snap pizz."
- sul ponticello, bow near the bridge, glassy and rich in high partials: "text": "sul pont."
- sul tasto, bow over the fingerboard, soft and veiled: "text": "sul tasto"
- back to the normal bow position: "text": "ord."
- flautando, light fast bow, airy: "text": "flautando"
- col legno battuto, struck with the wood of the bow: "text": "col legno batt."
- col legno tratto, drawn with the wood: "text": "col legno tratto"
- mute on / off: "text": "con sord." / "senza sord."; it takes a few seconds to put on or take off
- bowed tremolo, fast repeated strokes on one note: "art": "tremolo"; measured: "art": "tremolo2" or "tremolo1"
- trill: "art": "trill"
- natural and artificial harmonics: "art": "harmonic" on the sounding pitch (see each instrument's Harmonics)
- glissando: "gliss" on the note; smooth along one string, any interval
- bow direction: "art": "downbow" / "upbow"
- overpressure, scratch tone, noise: "text": "overpressure"
- jeté / ricochet, the bow bouncing: "text": "jeté"
- bowing behind the bridge, tapping the body: "head": "cross" with "text": "behind the bridge" or "tap body"

articulations: "staccato" and "staccatissimo" are short separate bow strokes;
"tenuto" is full length with a slight separation; "accent" and "marcato" are a
stronger bow attack. There are no slurs in this score: for legato, let each
note last until the next onset.

constraints:
- double stops: two notes at once on two adjacent strings, one note per string;
  the lower note can be no lower than the lower string's open pitch.
- three or four notes bowed together are broken (played as a fast arpeggio from
  the bottom), except when short and loud; in pizz. they sound together.
- open strings ring longer, cannot take vibrato and cannot slide.
