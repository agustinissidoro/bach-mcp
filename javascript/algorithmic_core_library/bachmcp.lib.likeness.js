/*
bachmcp.lib.likeness.js
-----------------------
Comparing passages: a summary of each (features), how alike two are (similarity), and
letters by likeness (classify).

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

const { chordsOf, notesOf, span } = need("bachmcp.lib.gather.js");
const { melody, intervals, contour, iois } = need("bachmcp.lib.lines.js");
const { ambitus, centroid } = need("bachmcp.lib.texture.js");

/**
 * A summary of a passage: {start, end, dur, chords, notes, ambitus, centroid, density
 * (attacks per second), melody (top line), contour, intervals, iois}.
 */
function features(x) {
  const chords = chordsOf(x);
  const [start, end] = span(chords);
  const line = melody(chords);
  const attacks = notesOf(chords).length;
  return {
    start, end, dur: end - start, chords: chords.length, notes: attacks,
    ambitus: ambitus(chords), centroid: centroid(chords),
    density: end > start ? (attacks * 1000) / (end - start) : 0,
    melody: line, contour: contour(line), intervals: intervals(line), iois: iois(chords),
  };
}

function resample(values, n) {
  if (!values.length) return new Array(n).fill(0);
  if (values.length === 1) return new Array(n).fill(values[0]);
  return Array.from({ length: n }, (_, i) => {
    const pos = (i * (values.length - 1)) / (n - 1);
    const lo = Math.floor(pos);
    const hi = Math.min(values.length - 1, lo + 1);
    return values[lo] + (values[hi] - values[lo]) * (pos - lo);
  });
}

function editDistance(a, b) {
  const row = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    let diagonal = row[0];
    row[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const above = row[j];
      row[j] = Math.min(row[j] + 1, row[j - 1] + 1, diagonal + (a[i - 1] === b[j - 1] ? 0 : 1));
      diagonal = above;
    }
  }
  return row[b.length];
}

/**
 * How alike two passages are as gestures, from 0 (nothing in common) to 1 (the same):
 * their contours, the sizes of their intervals and their rhythms (in proportion, so a
 * transposed, faster or slower repeat still counts as alike).
 */
function similarity(a, b) {
  const fa = features(a);
  const fb = features(b);
  const longest = Math.max(fa.contour.length, fb.contour.length);
  const shape = longest ? 1 - editDistance(fa.contour, fb.contour) / longest : 1;
  const ia = resample(fa.intervals, 16);
  const ib = resample(fb.intervals, 16);
  const steps = 1 - Math.min(1, ia.reduce((s, v, i) => s + Math.abs(v - ib[i]), 0) / 16 / 600);
  const ratios = (xs) => {
    const mean = xs.length ? xs.reduce((s, v) => s + v, 0) / xs.length : 0;
    return mean ? xs.map((v) => v / mean) : xs;
  };
  const ra = resample(ratios(fa.iois), 16);
  const rb = resample(ratios(fb.iois), 16);
  const rhythm = 1 - Math.min(1, ra.reduce((s, v, i) => s + Math.abs(v - rb[i]), 0) / 16);
  return 0.4 * shape + 0.3 * steps + 0.3 * rhythm;
}

/**
 * Letters for passages by likeness: each passage gets the letter of the first earlier one
 * at least `threshold` alike (0..1), else a new letter. classify(phrases(x, 400)) = ["A", "B", "A", "C"].
 */
function classify(passages, threshold = 0.75) {
  const firsts = [];
  return passages.map((passage) => {
    let best = -1;
    let score = threshold;
    firsts.forEach((first, i) => {
      const s = similarity(first, passage);
      if (s >= score) {
        best = i;
        score = s;
      }
    });
    if (best < 0) {
      firsts.push(passage);
      best = firsts.length - 1;
    }
    return best < 26 ? String.fromCharCode(65 + best) : `Z${best - 25}`;
  });
}

module.exports = { features, similarity, classify };
