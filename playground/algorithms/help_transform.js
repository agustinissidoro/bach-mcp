// The help patch's algorithm: transposes every note of the source by "shift".
const params = {
  shift: { type: "slider", range: [-1200, 1200], value: 700, unit: "mc" },
};

function transform(source, p) {
  const out = copy(source);
  eachNote(out, (n) => { n.pitch += p.shift; });
  return out;
}
