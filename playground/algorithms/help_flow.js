// The help patch's algorithm for bachmcp.gui.params: transposes, mirrors around an axis
// and scales the velocities of the source, so that the panel shows several kinds of parameter.
const params = {
  shift:    { type: "slider", range: [-1200, 1200], value: 0, unit: "mc" },
  mirror:   { type: "toggle", value: false },
  axis:     { type: "slider", range: [3600, 8400], value: 6000, unit: "mc" },
  dynamics: { type: "menu", options: ["same", "softer", "louder"], value: "same" },
};

function transform(source, p) {
  const out = copy(source);
  const factor = { same: 1, softer: 0.6, louder: 1.4 }[p.dynamics];
  eachNote(out, (n) => {
    if (p.mirror) n.pitch = 2 * p.axis - n.pitch;
    n.pitch += p.shift;
    n.vel = Math.max(1, Math.min(127, Math.round(n.vel * factor)));
  });
  return out;
}
