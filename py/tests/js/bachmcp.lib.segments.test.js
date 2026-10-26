// bachmcp.lib.segments.js: phrases and sections. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib, piece } = require("./fixtures.js");

test("phrases and sections", () => {
  const s = piece();
  assert.deepEqual(lib.phrases(s, 400).map((p) => p[0].onset), [0, 2000, 4000]);
  assert.deepEqual(lib.phrases(s.voices[0].chords, 400).map((p) => p.length), [4, 4, 2]);
  assert.deepEqual(lib.sections(s).map((p) => p.length), [10, 2], "at the markers, all voices");
  delete s.markers;
  assert.deepEqual(lib.sections(s, 600).map((p) => p.length), [5, 5, 2], "at long silences without markers");
});

test("chordEnd and phrases on chords out of order", () => {
  const chords = [
    { onset: 0, notes: [{ pitch: 6000, dur: 1000 }, { pitch: 6400, dur: 200 }] },
    { onset: 1200, notes: [{ pitch: 6200, dur: 100 }] },   // 200 ms after the long note ends
    { onset: 1800, notes: [{ pitch: 6500, dur: 100 }] },   // 500 ms of silence before it
    { onset: 600, notes: [{ pitch: 6700, dur: 100 }] },    // out of order, inside the first note
  ];
  assert.equal(lib.chordEnd(chords[0]), 1000);
  assert.deepEqual(lib.phrases(chords, 300).map((g) => g.map((c) => c.onset)), [[0, 600, 1200], [1800]]);
  assert.deepEqual(lib.phrases(chords, 150).map((g) => g.length), [2, 1, 1]);
});
