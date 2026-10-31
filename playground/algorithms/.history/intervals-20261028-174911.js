// Segments the score into phrase groups (silence longer than `gap` separates two phrases), then selects, inside each group only, the adjacent notes whose interval matches the chosen kind.
const params = {
  gap:    { type: "slider", range: [50, 3000], value: 600, unit: "ms" },
  kind:   { type: "menu", options: ["semitone", "quartertone", "any", "range"], value: "semitone" },
  low:    { type: "slider", range: [0, 1200], value: 100, unit: "mc" },
  high:   { type: "slider", range: [0, 1200], value: 500, unit: "mc" },
  exact:  { type: "slider", range: [50, 1200], value: 100, unit: "mc" },
};

function select(source, p) {
  const picked = [];
  for (const voice of source.voices) {
    const parts = phrases(voice, p.gap);
    for (const part of parts) {
      const notes = [];
      for (const chord of part) for (const n of chord.notes) notes.push(n);
      notes.sort((a, b) => a.onset - b.onset);
      const inGroup = new Set();
      for (let i = 0; i + 1 < notes.length; i++) {
        const d = Math.abs(notes[i + 1].pitch - notes[i].pitch);
        let ok;
        if (p.kind === "semitone") ok = d === Math.round(p.exact / 100) * 100;
        else if (p.kind === "quartertone") ok = d === Math.round(p.exact / 50) * 50;
        else if (p.kind === "any") ok = d > 0;
        else ok = d >= p.low && d <= p.high;
        if (ok) { inGroup.add(notes[i]); inGroup.add(notes[i + 1]); }
      }
      for (const n of notes) if (inGroup.has(n)) picked.push(n);
    }
  }
  return picked;
}
