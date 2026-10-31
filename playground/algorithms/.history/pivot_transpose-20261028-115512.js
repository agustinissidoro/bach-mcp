// Each phrase after the first is inverted around its own centroid, then pulled toward the global register at that moment in time.
const params = {
  gap:    { type: "slider", range: [50, 2000], value: 300, unit: "ms" },
  pull:   { type: "slider", range: [0, 1], value: 0.5, step: 0.01 },
  invert: { type: "toggle", value: true },
};

function transform(source, p) {
  const out = copy(source);
  const reg = profile(out, "register", { window: 2000 });

  for (const voice of out.voices) {
    const parts = phrases(voice, p.gap);

    parts.forEach((part, i) => {
      if (i === 0) return; // first phrase stays as it was

      const centre = centroid(part);
      const [start, end] = span(part);
      const target = reg((start + end) / 2);
      const shift = p.pull * (target - centre);

      for (const chord of part) {
        for (const note of chord.notes) {
          let np = p.invert ? 2 * centre - note.pitch : note.pitch;
          note.pitch = clamp(Math.round(np + shift), 1200, 12700);
        }
      }
    });
  }

  return out;
}
