// Two interleaved chromatic lines from the same start: line 1 overblown to its
// 3rd partial (fingered + 1902 mc), line 2 at its fingered pitch. Line 2 grows:
// after each note of line 1, one more note of line 2 is inserted between it and
// the next. Both lines are identical chromatic runs, offset by `offset`.
const params = {
  start:   { type: "slider", range: [3600, 7200], value: 3800, unit: "mc" },
  offset:  { type: "slider", range: [0, 600], value: 100, unit: "mc" },
  notes:   { type: "slider", range: [8, 64], value: 20 },
  tempo:   { type: "slider", range: [60, 480], value: 150, unit: "ms" },
  phrase:  { type: "slider", range: [2, 16], value: 8 },
  gap:     { type: "slider", range: [300, 2000], value: 600, unit: "ms" },
};

function produce(p) {
  const s = score();
  const v = s.voice("Flute");
  const step = SEMITONE; // chromatic, whole semitones

  // Build the combined sequence of line-1 notes and inserted line-2 notes.
  const seq = [];
  let l1 = 0, l2 = 0; // how many of each line have been placed
  while (l1 < p.notes) {
    seq.push({ line: 1, k: l1 });   // one note of line 1
    l1++;
    if (l1 < p.notes) {             // then insert `l1` notes of line 2
      for (let j = 0; j < l1 && l2 < p.notes; j++) {
        seq.push({ line: 2, k: l2 });
        l2++;
      }
    }
  }

  const d = p.tempo;
  let t = 0;
  seq.forEach((item, i) => {
    const pitch = p.start + item.k * step + (item.line === 2 ? p.offset : 0);
    const fields = item.line === 1 ? { slots: { 22: ["harmonic"] } } : {};
    v.note(t, Math.round(pitch), d * 0.92, fields);
    t += d;
    // a breath: a gap after every `phrase` notes of line 1
    if (item.line === 1 && l1 % p.phrase === 0 && l1 < p.notes) t += p.gap;
  });
  return s;
}
