/*
bachmcp.lib.texture.js
----------------------
Register and texture: the ambitus and centre of the music, and how density, polyphony,
register, spread or loudness change over time (profile).

Music here (x) is any of: a score {voices}, a voice {chords}, one chord, or an array
of chords. Pitches in midicents, times in milliseconds. The chords returned are the
score's own, not copies: a transformer reads copy(source) and changes what it finds.
*/
"use strict";

// Max finds a file by its name, on the search path; Node by where it is.
function need(name) {
  const places = ["", "./", "../", "../algorithmic_core_library/", "../runners/"];
  for (const place of places) {
    try {
      return require(place + name);
    } catch (e) {
      if (place === places[places.length - 1]) throw e;
    }
  }
}

const { notesOf, pitchesOf, span } = need("bachmcp.lib.gather.js");

/** [lowest, highest] pitch of the music; null when it has no notes. */
function ambitus(x) {
  const ps = pitchesOf(x);
  return ps.length ? [Math.min(...ps), Math.max(...ps)] : null;
}

/** The mean pitch, each note weighted by its duration; null when there are no notes. */
function centroid(x) {
  const ns = notesOf(x);
  const total = ns.reduce((a, n) => a + n.dur, 0);
  if (!ns.length) return null;
  if (!total) return ns.reduce((a, n) => a + n.pitch, 0) / ns.length;
  return ns.reduce((a, n) => a + n.pitch * n.dur, 0) / total;
}

const MEASURES = ["density", "polyphony", "register", "spread", "top", "bottom", "loudness"];

/**
 * How one property of the music changes over time, measured in windows of `window` ms
 * every `step` ms:
 *   density    attacks per second       polyphony  notes sounding at once (on average)
 *   register   mean sounding pitch      spread     highest minus lowest sounding pitch
 *   top        highest sounding pitch   bottom     lowest sounding pitch
 *   loudness   mean velocity of the attacks
 * Returns a function of time in ms (linear between windows; silent windows are skipped
 * for the pitch measures), with .times (the windows' centres) and .values (null where silent).
 */
function profile(x, measure = "density", { window = 1000, step } = {}) {
  if (!MEASURES.includes(measure)) throw new Error(`profile: measure is one of ${MEASURES.join(", ")}, got ${measure}`);
  window = Math.max(1, window);
  step = Math.max(1, step || window / 2);
  const ns = notesOf(x);
  const [start, end] = span(x);
  const times = [];
  const values = [];
  for (let t = start; t < end || t === start; t += step) {
    const from = t;
    const to = t + window;
    const attacks = ns.filter((n) => n.onset >= from && n.onset < to);
    const heard = ns.filter((n) => n.onset < to && n.end > from);
    const overlap = (n) => Math.min(n.end, to) - Math.max(n.onset, from);
    let v = null;
    if (measure === "density") v = (attacks.length * 1000) / window;
    else if (measure === "polyphony") v = heard.reduce((a, n) => a + overlap(n), 0) / window;
    else if (measure === "loudness") v = attacks.length ? attacks.reduce((a, n) => a + n.vel, 0) / attacks.length : 0;
    else if (heard.length) {
      const ps = heard.map((n) => n.pitch);
      if (measure === "top") v = Math.max(...ps);
      else if (measure === "bottom") v = Math.min(...ps);
      else if (measure === "spread") v = Math.max(...ps) - Math.min(...ps);
      else {
        const w = heard.reduce((a, n) => a + overlap(n), 0);
        v = heard.reduce((a, n) => a + n.pitch * overlap(n), 0) / w;
      }
    } else if (measure === "spread") v = 0;
    times.push(from + window / 2);
    values.push(v);
    if (end <= start) break;
  }
  const known = times.map((t, i) => [t, values[i]]).filter((pt) => pt[1] !== null);
  const f = (t) => {
    if (!known.length) return null;
    if (t <= known[0][0]) return known[0][1];
    for (let i = 1; i < known.length; i++) {
      if (t <= known[i][0]) {
        const [t0, v0] = known[i - 1];
        const [t1, v1] = known[i];
        return v0 + ((v1 - v0) * (t - t0)) / (t1 - t0);
      }
    }
    return known[known.length - 1][1];
  };
  f.times = times;
  f.values = values;
  return f;
}

module.exports = { ambitus, centroid, profile, MEASURES };
