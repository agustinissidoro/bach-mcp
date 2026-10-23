// Every phrase of the source (its notes separated by more than `gap` of silence) moves so that it starts on a target: one pitch for all, or a pitch that steps on from phrase to phrase.
const params = {
  gap:      { type: "slider", range: [50, 2000], value: 300, unit: "ms" },
  target:   { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" },
  step:     { type: "slider", range: [-700, 700], value: 200, unit: "mc" },
  register: { type: "range", range: [1200, 12700], value: [1200, 12700], unit: "mc" },
  mode:     { type: "menu", options: ["stepping", "same"], value: "stepping" },
};

function transform(source, p) {
  const out = copy(source);
  for (const voice of out.voices) {
    phrases(voice.chords, p.gap).forEach((phrase, i) => {
      const goal = p.mode === "same" ? p.target : fold(p.target + i * p.step, p.register[0], p.register[1]);
      const first = Math.min(...phrase[0].notes.map((n) => n.pitch));
      for (const chord of phrase) {
        for (const note of chord.notes) note.pitch = clamp(note.pitch + goal - first, 1200, 12000);
      }
    });
  }
  return out;
}
