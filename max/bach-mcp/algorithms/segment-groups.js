// A source line of notes with variable gaps. Any gap longer than the silence
// threshold ends a group and starts a new one. Each group is then transposed so
// its first note lands on a target pitch: in "per-group" mode each group gets
// its own target (a walk), in "shared" mode every group's first note is
// transposed to the same pitch.
const params = {
  times:       { type: "slider", range: [4, 48], value: 20 },
  gap:         { type: "slider", range: [120, 1200], value: 400, unit: "ms" },
  silence:     { type: "slider", range: [120, 2400], value: 900, unit: "ms" },
  register:    { type: "range", range: [3600, 9600], value: [5400, 8400], unit: "mc" },
  step:        { type: "slider", range: [50, 700], value: 250, unit: "mc" },
  groupPitch:  { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" },
  sharedPitch: { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" },
  mode:        { type: "menu", options: ["per-group", "shared"], value: "per-group" },
  duration:    { type: "slider", range: [120, 1200], value: 350, unit: "ms" },
  seed:        { type: "seed", value: 1 },
};

function generate(p, input) {
  const s = score();
  const v = s.voice("Line");
  const r = rng("line");

  // 1. Build the source line: a walk of pitches with variable gaps.
  //    Gaps are drawn so some exceed the silence threshold, creating groups.
  const notes = [];
  let pitch = p.register[0] + r.float(0, p.register[1] - p.register[0]);
  let t = 0;
  for (let i = 0; i < p.times; i++) {
    notes.push({ onset: t, pitch: snap(pitch, QUARTERTONE) });
    // advance pitch by a melodic step, folded into the register
    pitch = fold(pitch + r.gauss(0, p.step), p.register[0], p.register[1]);
    // gap: mostly short, sometimes a long silence that will split a group
    const long = r.chance(0.35);
    const g = long
      ? p.silence * r.float(1.2, 2.2)
      : p.gap * r.float(0.6, 1.1);
    t += p.duration + g;
  }

  // 2. Segment: a gap longer than the silence threshold ends a group.
  const groups = [];
  let cur = [notes[0]];
  for (let i = 1; i < notes.length; i++) {
    const gap = notes[i].onset - (notes[i - 1].onset + p.duration);
    if (gap > p.silence) {
      groups.push(cur);
      cur = [notes[i]];
    } else {
      cur.push(notes[i]);
    }
  }
  groups.push(cur);

  // 3. Transpose each group so its first note lands on a target pitch.
  //    per-group: each group's target is a walk around groupPitch.
  //    shared:    every group's target is the same sharedPitch.
  const gr = rng("group");
  let target = p.groupPitch;
  groups.forEach((g, gi) => {
    let tp;
    if (p.mode === "shared") {
      tp = p.sharedPitch;
    } else {
      tp = target;
      target = fold(target + gr.gauss(0, p.step * 1.5), p.register[0], p.register[1]);
    }
    const first = g[0].pitch;
    const shift = tp - first;
    g.forEach((n) => {
      v.note(n.onset, n.pitch + shift, p.duration, { head: gi % 2 ? "diamond" : "black" });
    });
    s.marker(g[0].onset, "G" + (gi + 1));
  });

  return s;
}
