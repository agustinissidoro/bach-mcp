/*
bachmcp.lib.harmony.js
----------------------
Harmony: pitch classes, set classes (prime form, interval vector) and the harmonic field.
The set-class functions work in twelve equal semitones: microtones are rounded.

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

const { notesOf, pitchesOf } = need("bachmcp.lib.gather.js");

function pitchList(x) {
  return Array.isArray(x) && x.every((v) => typeof v === "number") ? x : pitchesOf(x);
}

/** The pitch classes of the music (or of a list of pitches), in midicents 0..1199, each once, ascending. */
function pcs(x) {
  return [...new Set(pitchList(x).map((p) => ((p % 1200) + 1200) % 1200))].sort((a, b) => a - b);
}

function semitoneClasses(x) {
  return [...new Set(pitchList(x).map((p) => ((Math.round(p / 100) % 12) + 12) % 12))].sort((a, b) => a - b);
}

/**
 * The set class of the music's pitch classes, as its prime form in semitones (Rahn):
 * primeForm([6000, 6400, 6700]) = [0, 3, 7]. Any transposition or inversion gives the same.
 */
function primeForm(x) {
  const set = semitoneClasses(x);
  if (set.length < 2) return set.map(() => 0);
  let best = null;
  for (const form of [set, set.map((p) => (12 - p) % 12).sort((a, b) => a - b)]) {
    for (let r = 0; r < form.length; r++) {
      const rotated = form.slice(r).concat(form.slice(0, r));
      const candidate = rotated.map((p) => (p - rotated[0] + 12) % 12);
      if (!best || packedBefore(candidate, best)) best = candidate;
    }
  }
  return best;
}

function packedBefore(a, b) {
  for (let i = a.length - 1; i > 0; i--) {
    if (a[i] !== b[i]) return a[i] < b[i];
  }
  return false;
}

/** How many of each interval class (1 to 6 semitones) the pitch classes hold: a list of six counts. */
function intervalVector(x) {
  const set = semitoneClasses(x);
  const out = [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < set.length; i++) {
    for (let j = i + 1; j < set.length; j++) {
      const d = set[j] - set[i];
      out[Math.min(d, 12 - d) - 1]++;
    }
  }
  return out;
}

/**
 * The harmonic field: every pitch the music uses with how long it sounds in total, low to
 * high, as [{pitch, weight}] (weight in ms). With {classes: true}, pitch classes (0..1199).
 */
function field(x, { classes = false } = {}) {
  const weights = new Map();
  for (const n of notesOf(x)) {
    const key = classes ? ((n.pitch % 1200) + 1200) % 1200 : n.pitch;
    weights.set(key, (weights.get(key) || 0) + n.dur);
  }
  return [...weights.entries()].sort((a, b) => a[0] - b[0]).map(([pitch, weight]) => ({ pitch, weight }));
}

module.exports = { pcs, primeForm, intervalVector, field };
