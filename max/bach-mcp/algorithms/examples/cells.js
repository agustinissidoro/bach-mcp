// An elementary cellular automaton read as harmony: each row is a moment, and each live cell sounds one pitch of a field built up from a base by a fixed interval.
const params = {
  rule:     { type: "menu", options: [30, 45, 73, 90, 105, 110, 150], value: 90 },
  cells:    { type: "slider", range: [5, 24], value: 13 },
  times:    { type: "slider", range: [4, 64], value: 24 },
  base:     { type: "slider", range: [3600, 6000], value: 4800, unit: "mc" },
  interval: { type: "slider", range: [50, 700], value: 350, unit: "mc" },
  rate:     { type: "curve", range: [80, 600], value: [[0, 400], [0.5, 120], [1, 500]], unit: "ms" },
  legato:   { type: "slider", range: [0.2, 2], value: 0.9, step: 0.05 },
  random:   { type: "toggle", value: false },
  seed:     { type: "seed", value: 1 },
};

function generate(p) {
  const s = score();
  const piano = s.voice("Piano");
  const r = rng("start");
  const first = p.random ? seq(p.cells).map(() => (r.chance(0.4) ? 1 : 0)) : p.cells;
  const rows = automaton(p.rule, first, p.times);
  let t = 0;
  rows.forEach((row, i) => {
    const ioi = p.rate(i / (p.times - 1));
    const pitches = [];
    row.forEach((alive, k) => {
      const pitch = p.base + k * p.interval;
      if (alive && pitch <= 10800) pitches.push(pitch);
    });
    const live = row.filter((c) => c).length / p.cells;
    if (pitches.length) {
      piano.chord(t, pitches, ioi * p.legato, { vel: Math.round(lerp(30, 110, live)), dyn: i === 0 ? "mp" : undefined });
    }
    t += ioi;
  });
  return s;
}
