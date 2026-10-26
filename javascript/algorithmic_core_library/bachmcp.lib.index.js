/*
bachmcp.lib.index.js
--------------------
The algorithmic core library: everything an algorithm file has in scope, without
imports. This file is the one list of it. Each topic is a file of its own:

    bachmcp.lib.units.js       SEMITONE ... SECOND, pitch(), name() (and the pitch range, the note limit)
    bachmcp.lib.build.js       score(), voices, notes and chords; copy, eachNote
    bachmcp.lib.random.js      rng(name), seeded Math.random
    bachmcp.lib.numbers.js     lerp, clamp, rescale, wrap, fold, snap, seq, linspace, sum, accumulate, env, warp
    bachmcp.lib.procedures.js  iterate, walk, markov, rewrite, automaton, euclid
    bachmcp.lib.gather.js      chordsOf, notesOf, pitchesOf, chordEnd, span, between, sounding
    bachmcp.lib.segments.js    phrases, sections
    bachmcp.lib.lines.js       melody, intervals, contour, turns, iois
    bachmcp.lib.texture.js     ambitus, centroid, profile
    bachmcp.lib.harmony.js     pcs, primeForm, intervalVector, field
    bachmcp.lib.likeness.js    features, similarity, classify
    (bachmcp.lib.base.js       AlgoError and two checks, for the files here: not in scope)

To add to the library: a file here, its names in TOPICS below, and their
description in the skill (py/bach_mcp/prompt/BACH_SKILL.md; a test checks that
every name in scope is described there), and a test in py/tests/js.

The same files run in Max (v8, through the search path) and in Node (the check
that runs before a file reaches Max), so an algorithm behaves the same in both.
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

const { seeded } = need("bachmcp.lib.random.js");

// Every topic whose names are all in scope.
const TOPICS = [
  "units", "build", "numbers", "procedures",
  "gather", "segments", "lines", "texture", "harmony", "likeness",
].map((topic) => need(`bachmcp.lib.${topic}.js`));

const NOT_IN_SCOPE = [
  "Score", "Voice", "MEASURES",
  "MIN_CENTS", "MAX_CENTS", "MAX_NOTES", "fmt", "nameToCents", "centsToName",  // for the loader and the parameters
];

/** The names in scope in an algorithm file, for one run: the topics, plus its seeded rng and Math. */
function makeLibrary(state) {
  const scope = {};
  for (const topic of TOPICS) {
    for (const [key, value] of Object.entries(topic)) if (!NOT_IN_SCOPE.includes(key)) scope[key] = value;
  }
  return Object.assign(scope, seeded(state));
}

const LIBRARY = Object.keys(makeLibrary({ seed: 0, streams: new Map() }));

module.exports = { makeLibrary, LIBRARY, ...Object.assign({}, ...TOPICS), ...need("bachmcp.lib.random.js") };
