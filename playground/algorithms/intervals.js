// Segments the score into phrase groups (silence longer than `gap` separates two phrases), then selects, strictly inside each group, the adjacent notes whose interval satisfies the condition — equal to, greater than, smaller than or between two bounds.
const params = {
  gap:      { type: "slider", range: [50, 3000], value: 600, unit: "ms" },
  cond:     { type: "menu", options: ["equal", "greater", "smaller", "between"], value: "equal" },
  interval: { type: "slider", range: [0, 1200], value: 100, unit: "mc" },
  low:      { type: "slider", range: [0, 1200], value: 100, unit: "mc" },
  high:     { type: "slider", range: [0, 1200], value: 500, unit: "mc" },
};

function select(source, p) {
  const matches = (d) => {
    if (p.cond === "equal") return d === Math.round(p.interval / 50) * 50;
    if (p.cond === "greater") return d > p.interval;
    if (p.cond === "smaller") return d < p.interval;
    return d >= p.low && d <= p.high;
  };
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
        if (matches(d)) { inGroup.add(notes[i]); inGroup.add(notes[i + 1]); }
      }
      for (const n of notes) if (inGroup.has(n)) picked.push(n);
    }
  }
  return picked;
}
