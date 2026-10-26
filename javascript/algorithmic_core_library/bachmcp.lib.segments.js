/*
bachmcp.lib.segments.js
-----------------------
The parts of the music: phrases cut at silences, sections cut at markers.

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

const { chordsOf, chordEnd } = need("bachmcp.lib.gather.js");

/**
 * The chords in groups separated by silence: a new phrase starts wherever the silence
 * since everything before has stopped sounding is longer than `gap` milliseconds.
 */
function phrases(x, gap) {
  const out = [];
  let current = [];
  let sounded = -Infinity;
  for (const chord of chordsOf(x)) {
    if (current.length && chord.onset - sounded > gap) {
      out.push(current);
      current = [];
    }
    current.push(chord);
    sounded = Math.max(sounded, chordEnd(chord));
  }
  if (current.length) out.push(current);
  return out;
}

/**
 * The large parts of a score: cut at its markers when it has any, else at silences
 * longer than `gap` (default 1500 ms) across all voices.
 */
function sections(x, gap = 1500) {
  const markers = (x && Array.isArray(x.markers) ? x.markers : []).map((m) => m.onset).sort((a, b) => a - b);
  if (!markers.length) return phrases(x, gap);
  const cuts = markers.filter((t) => t > 0);
  const out = cuts.concat([Infinity]).map(() => []);
  for (const chord of chordsOf(x)) {
    let i = 0;
    while (i < cuts.length && chord.onset >= cuts[i]) i++;
    out[i].push(chord);
  }
  return out.filter((part) => part.length);
}

module.exports = { phrases, sections };
