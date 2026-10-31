// Segments the score into phrases; transposes every phrase so that its pivot note (by index, clamped to the last note if out of range) lands on the target pitch. The same pivot index and target apply to all phrases.
const params = {
  gap:        { type: "slider", range: [50, 500], value: 300, unit: "ms" },
  pivotNote:  { type: "slider", range: [1, 5], value: 1 },
  target:     { type: "slider", range: [1200, 12700], value: 6400, unit: "mc" },
  register:   { type: "range", range: [1200, 12700], value: [1200, 12700], unit: "mc" },
};

function pivotPitch(phrase, idx) {
  const notes = phrase.flatMap((c) => c.notes);
  if (!notes.length) return null;
  const i = Math.max(0, Math.min(idx - 1, notes.length - 1));
  return notes[i].pitch;
}

function transform(source, p) {
  const out = copy(source);
  for (const voice of out.voices) {
    const parts = phrases(voice, p.gap);
    for (const part of parts) {
      const pv = pivotPitch(part, p.pivotNote);
      if (pv === null) continue;
      const shift = p.target - pv;
      for (const chord of part) {
        for (const note of chord.notes) {
          let np = note.pitch + shift;
          while (np < p.register[0]) np += 1200;
          while (np > p.register[1]) np -= 1200;
          note.pitch = Math.round(np);
        }
      }
    }
  }
  return out;
}
