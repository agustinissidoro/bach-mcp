// Remove every note that is a flat: its pitch class (mod 1200) lands on one of the five sharp-accidental
// semitones C# D# F# G# A# (the black keys, spelled as sharps). Chords that lose all their notes are dropped.
// The filter applies to every voice at once; optionally keep the first voice as an untouched reference.
const params = {
  accidentals: { type: "menu", options: ["sharps", "all_accidentals"], value: "sharps" },
  all_voices:  { type: "toggle", value: true },
};

function transform(source, p) {
  const out = copy(source);

  // Pitch classes (mod 1200) that count as flats.
  // sharps = the black keys spelled as sharps: C# D# F# G# A#.
  // all_accidentals = every chromatic semitone that is not a natural white key, same set here,
  // but also strips enharmonic spellings like Bb (=A#) by class alone.
  const flats = new Set([100, 300, 600, 800, 1000]);

  out.voices.forEach((voice, vi) => {
    if (!p.all_voices && vi === 0) return; // keep first voice as reference

    voice.chords = voice.chords.filter((chord) => {
      chord.notes = chord.notes.filter((nt) => !flats.has(((nt.pitch % 1200) + 1200) % 1200));
      return chord.notes.length > 0; // drop chords that became empty
    });
  });

  return out;
}
