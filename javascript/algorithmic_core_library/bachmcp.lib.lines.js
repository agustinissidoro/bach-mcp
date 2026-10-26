/*
bachmcp.lib.lines.js
--------------------
Lines and shapes: a melodic line through the music, its intervals, contour, turns and rhythm.

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

const { chordsOf, notesOf } = need("bachmcp.lib.gather.js");

/**
 * A melodic line through the music: at each onset, the highest pitch ("top"), the lowest
 * ("bottom") or their mean ("mean"). A list of pitches, one per onset.
 */
function melody(x, which = "top") {
  const byOnset = new Map();
  for (const n of notesOf(x)) {
    if (!byOnset.has(n.onset)) byOnset.set(n.onset, []);
    byOnset.get(n.onset).push(n.pitch);
  }
  return [...byOnset.values()].map((ps) => {
    if (which === "bottom") return Math.min(...ps);
    if (which === "mean") return ps.reduce((a, b) => a + b, 0) / ps.length;
    return Math.max(...ps);
  });
}

/** The steps between successive values: intervals([6000, 6400, 6200]) = [400, -200]. */
function intervals(values) {
  const out = [];
  for (let i = 1; i < values.length; i++) out.push(values[i] - values[i - 1]);
  return out;
}

/** Up (1), same (0) or down (-1) from each pitch to the next, of a list of pitches or of melody(x, which). */
function contour(x, which = "top") {
  const values = Array.isArray(x) && x.every((v) => typeof v === "number") ? x : melody(x, which);
  return intervals(values).map(Math.sign);
}

/** Where a list of values turns: {peaks, troughs}, the indices of its local highs and lows (inner values only). */
function turns(values) {
  const peaks = [];
  const troughs = [];
  for (let i = 1; i < values.length - 1; i++) {
    let j = i + 1;
    while (j < values.length - 1 && values[j] === values[i]) j++;  // a plateau counts once, at its start
    if (values[i] > values[i - 1] && values[i] > values[j]) peaks.push(i);
    if (values[i] < values[i - 1] && values[i] < values[j]) troughs.push(i);
  }
  return { peaks, troughs };
}

/** The times between successive onsets, in milliseconds. */
function iois(x) {
  const onsets = [...new Set(chordsOf(x).map((c) => c.onset))];
  return intervals(onsets);
}

module.exports = { melody, intervals, contour, turns, iois };
