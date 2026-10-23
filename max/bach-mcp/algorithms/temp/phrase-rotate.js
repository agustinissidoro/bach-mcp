// Segment the score into phrases (chords separated by more than `gap` ms of silence) and, in every
// phrase at once, cyclically rotate one chosen property across its notes: pitch, duration, onset or velocity.
// rotation 0 leaves each phrase as it was; k shifts the values by k positions (forward or backward).
const params = {
  gap:      { type: "slider", range: [50, 2000], value: 300, unit: "ms" },
  level:    { type: "menu", options: ["pitch", "duration", "onset", "velocity"], value: "pitch" },
  rotation: { type: "slider", range: [0, 16], value: 1 },
  direction:{ type: "menu", options: ["forward", "backward"], value: "forward" },
};

function transform(source, p) {
  const out = copy(source);
  const rot = (p.direction === "backward") ? -p.rotation : p.rotation;

  for (const voice of out.voices) {
    phrases(voice.chords, p.gap).forEach((phrase) => {
      if (phrase.length < 2) return;
      const n = phrase.length;
      const shift = ((rot % n) + n) % n;

      if (p.level === "onset") {
        // rotate the onsets: reorder when the notes of the phrase sound, keeping their own durations.
        const starts = phrase.map((c) => c.onset);
        const base = Math.min(...starts);
        for (let i = 0; i < n; i++) {
          phrase[i].onset = base + starts[(i + shift) % n];
        }
      } else if (p.level === "pitch") {
        // rotate the pitch of each chord across the notes of the phrase.
        const bases = phrase.map((c) => Math.min(...c.notes.map((nt) => nt.pitch)));
        for (let i = 0; i < n; i++) {
          const target = bases[(i + shift) % n];
          const delta = target - bases[i];
          for (const nt of phrase[i].notes) nt.pitch = clamp(nt.pitch + delta, 1200, 12700);
        }
      } else if (p.level === "duration") {
        // rotate the duration of each chord across the notes of the phrase.
        const durs = phrase.map((c) => c.notes[0].dur);
        for (let i = 0; i < n; i++) {
          const dur = durs[(i + shift) % n];
          for (const nt of phrase[i].notes) nt.dur = dur;
        }
      } else if (p.level === "velocity") {
        // rotate the velocity of each chord across the notes of the phrase.
        const vels = phrase.map((c) => c.notes[0].vel);
        for (let i = 0; i < n; i++) {
          const vel = clamp(vels[(i + shift) % n], 1, 127);
          for (const nt of phrase[i].notes) nt.vel = vel;
        }
      }
    });
  }
  return out;
}
