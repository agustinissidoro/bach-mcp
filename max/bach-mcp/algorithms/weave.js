// One flute weaves a single scale out of two lines: a REAL line (low fingerings,
// the B-foot joint) and a HARMONIC line (overblown partials). Both lines are the
// SAME scale, so a harmonic pitch is a scale step and its real note is the
// fingering that produces it (partial n -> fingering + 1200*log2(n)).
// The two lines interleave, and each group adds one harmonic while the real
// notes stay fixed at one: 1 real + 1 harmonic, 1 real + 2 harmonics, ...
// Start at low B (B3 = 5900).

const params = {
  scale:    { type: "menu", options: ["chromatic", "whole", "minor", "major"], value: "chromatic" },
  groups:   { type: "slider", range: [2, 8], value: 6 },
  maxPart:  { type: "slider", range: [2, 6], value: 5 },
  start:    { type: "slider", range: [5400, 6300], value: 5900, unit: "mc" },
  realStep: { type: "slider", range: [0, 1200], value: 200 },
  harmStep: { type: "slider", range: [0, 1200], value: 200 },
  realDur:  { type: "slider", range: [200, 1600], value: 700, unit: "ms" },
  harmDur:  { type: "slider", range: [120, 1000], value: 400, unit: "ms" },
  gap:      { type: "slider", range: [0, 800], value: 220, unit: "ms" },
  seed:     { type: "seed", value: 1 },
};

function generate(p, input) {
  const s = score();
  const v = s.voice("Flute");
  const r = rng("weave");

  const steps = {
    chromatic: [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100],
    whole:     [0, 200, 400, 600, 800, 1000],
    minor:     [0, 200, 300, 500, 700, 800, 1000],
    major:     [0, 200, 400, 500, 700, 900, 1000],
  }[p.scale];
  const N = steps.length;
  const scalePitch = (i) => p.start + steps[((i % N) + N) % N];
  const log2 = (n) => Math.log(n) / Math.LN2;

  let t = 0;
  let realIdx = 0;
  let harmIdx = 0;

  for (let g = 0; g < p.groups; g++) {
    // one real note per group (the count stays the same)
    const real = scalePitch(realIdx);
    v.note(t, real, p.realDur, { dyn: g === 0 ? "p<" : "p", art: "tenuto" });
    t += p.realDur;

    // the number of harmonic notes grows: g + 1
    const nH = Math.min(g + 1, p.maxPart);
    for (let h = 0; h < nH; h++) {
      const part = 2 + h;                       // partials 2,3,4,...
      const pitch = scalePitch(harmIdx);        // a scale step, an octave up
      const fingering = pitch - 1200 * log2(part); // the real note that makes it
      v.note(t, pitch, p.harmDur, {
        dyn: "mp",
        art: "harmonic",
        text: "h" + part + "  fing " + Math.round(fingering / 100) + "c",
      });
      t += p.harmDur;
      harmIdx++;
    }
    realIdx++;
    t += p.gap;
  }

  return s;
}
