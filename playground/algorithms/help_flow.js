// Segments the score into phrases (silence longer than `gap` ms), then transposes every phrase as a whole so that one of its notes lands on the target pitch: the `pivot`-th note of the phrase (1-based), or its last one when the phrase is shorter. The pivot and target apply to every segment, so all phrases share the chosen reference point.
const params = {
  gap:        { type: "slider", range: [100, 2000], value: 400, unit: "ms" },
  pivotIndex: { type: "slider", range: [1, 20], value: 1 },
  target:     { type: "slider", range: [3600, 9600], value: 6400, unit: "mc" },
  spread:     { type: "slider", range: [0, 1200], value: 0, unit: "mc" },
};

function transform(source, p) {
  const out = copy(source);
  for (const voice of out.voices) {
    const parts = phrases(voice, p.gap);
    let phraseNo = 0;
    for (const part of parts) {
      if (!part.length) continue;
      phraseNo++;
      const n = part.length;
      // pivot: the requested note of the phrase, or its last one when out of range
      const k = Math.min(p.pivotIndex - 1, n - 1);
      // a chord may carry several notes: the pivot is the one sounding at that onset
      const pivotPitch = part[k].notes[0].pitch;
      // step the phrases so the shared pivot point walks by `spread` (0 = all land on the same target)
      const goal = p.target + phraseNo * p.spread;
      const shift = goal - pivotPitch;
      for (const chord of part) {
        for (const note of chord.notes) {
          note.pitch = clamp(Math.round(note.pitch + shift), 1200, 12700);
        }
      }
    }
  }
  return out;
}
