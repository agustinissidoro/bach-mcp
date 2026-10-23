// Voices leave one pitch together and drift apart by random walks; notes get longer as they spread.
const params = {
  voices:   { type: "slider", range: [1, 6], value: 3 },
  times:    { type: "slider", range: [4, 96], value: 32 },
  center:   { type: "slider", range: [4800, 8400], value: 6700, unit: "mc" },
  step:     { type: "slider", range: [0, 600], value: 150, unit: "mc" },
  register: { type: "range", range: [1200, 12700], value: [1200, 12700], unit: "mc" },
  duration: { type: "range", range: [60, 2000], value: [120, 700], unit: "ms" },
  density:  { type: "curve", value: [[0, 1], [0.6, 0.7], [1, 0.3]] },
  seed:     { type: "seed", value: 1 },
};

function produce(p) {
  const s = score();
  const names = ["Flute", "Oboe", "Clarinet", "Violin", "Viola", "Cello"];
  for (let k = 0; k < p.voices; k++) {
    const v = s.voice(names[k]);
    const r = rng("voice" + k);
    const path = walk({ n: p.times, start: p.center, step: p.step,
                        min: p.register[0], max: p.register[1], rng: r });
    let t = 0;
    path.forEach((pitch, i) => {
      const spread = Math.abs(pitch - p.center) / (p.register[1] - p.register[0]);
      const dur = lerp(p.duration[0], p.duration[1], clamp(2 * spread, 0, 1));
      if (r.chance(p.density(i / (p.times - 1)))) {
        v.note(t, snap(pitch, QUARTERTONE), dur);
      }
      t += dur;
    });
  }
  return s;
}
