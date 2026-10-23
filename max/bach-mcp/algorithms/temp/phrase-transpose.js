// Segment the score into phrases (chords separated by more than `gap` of silence) and move each phrase as a whole so that its first note lands on a target pitch: one target for all, or a target that steps on from phrase to phrase.
const params = {
  gap:      { type: "slider", range: [50, 2000], value: 300, unit: "ms" },
  target:   { type: "slider", range: [1200, 12700], value: 5500, unit: "mc" },
  step:     { type: "slider", range: [-1200, 1200], value: 300, unit: "mc" },
  register: { type: "range", range: [1200, 12700], value: [1200, 12700], unit: "mc" },
  mode:     { type: "menu", options: ["same", "stepping"], value: "same" },
};

function transform(source, p) {
  const out = copy(source);
  for (const voice of out.voices) {
    let i = 0;
    phrases(voice.chords, p.gap).forEach((phrase) => {
      // Goal pitch: one target for all, or a target that steps on per phrase.
      const goal = p.mode === "same" ? p.target : fold(p.target + i * p.step, p.register[0], p.register[1]);
      // The first note of the phrase is the lowest pitch sounding at its onset.
      const first = Math.min(...phrase[0].notes.map((n) => n.pitch));
      const shift = goal - first;
      for (const chord of phrase) {
        for (const note of chord.notes) {
          // Move the whole phrase by `shift`, folding back into the register.
          note.pitch = fold(note.pitch + shift, p.register[0], p.register[1]);
        }
      }
      i++;
    });
  }
  return out;
}
