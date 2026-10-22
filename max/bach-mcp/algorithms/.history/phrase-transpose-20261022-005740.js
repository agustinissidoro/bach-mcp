// Segment the current score into phrases (chords separated by more than `gap` of silence),
// then transpose each phrase as a whole so that its first note lands on a target pitch.
// "stepping" sends each successive phrase to a target stepped by `step`;
// "same" sends every phrase to one shared target.
const params = {
  gap:      { type: "slider", range: [50, 2000], value: 300, unit: "ms" },
  target:   { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" },
  step:     { type: "slider", range: [-1200, 1200], value: 400, unit: "mc" },
  register: { type: "range", range: [3600, 9600], value: [4800, 8400], unit: "mc" },
  mode:     { type: "menu", options: ["stepping", "same"], value: "stepping" },
};

function transform(source, p) {
  const out = copy(source);
  let index = 0;
  for (const voice of out.voices) {
    phrases(voice.chords, p.gap).forEach((phrase) => {
      // Where this phrase's first note should land.
      const goal = p.mode === "same" ? p.target : fold(p.target + index * p.step, p.register[0], p.register[1]);
      index++;

      // The first note of the phrase: earliest onset, then lowest pitch within it.
      let firstChord = phrase[0];
      for (const chord of phrase) {
        if (chord.onset < firstChord.onset) firstChord = chord;
      }
      const firstPitch = Math.min(...firstChord.notes.map((n) => n.pitch));

      // Shift the whole phrase so that first note sits on the goal.
      const shift = goal - firstPitch;
      for (const chord of phrase) {
        for (const note of chord.notes) {
          note.pitch = clamp(note.pitch + shift, p.register[0], p.register[1]);
        }
      }
    });
  }
  return out;
}
