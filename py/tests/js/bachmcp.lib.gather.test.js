// bachmcp.lib.gather.js: gathering music. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib, n, c, piece } = require("./fixtures.js");

test("chords of any music, in time order, and they are the score's own", () => {
  const s = piece();
  const chords = lib.chordsOf(s);
  assert.equal(chords.length, 12);
  assert.deepEqual(chords.slice(0, 3).map((ch) => ch.onset), [0, 0, 250]);
  assert.equal(lib.chordsOf(s.voices[1]).length, 2);
  assert.equal(lib.chordsOf(chords[0]).length, 1);
  assert.equal(lib.chordsOf([[chords[0]], [chords[1]]]).length, 2, "arrays of phrases are flattened");
  chords[2].notes[0].pitch = 6100;
  assert.equal(s.voices[0].chords[1].notes[0].pitch, 6100, "a change reaches the score");
  assert.deepEqual(lib.chordsOf(null), []);
});

test("notes, pitches, span, between, sounding", () => {
  const s = piece();
  assert.deepEqual(lib.notesOf(s).slice(0, 3).map((x) => x.pitch), [3600, 4300, 6000]);
  assert.equal(lib.notesOf(s)[0].end, 1250);
  assert.deepEqual(lib.span(s), [0, 6000]);
  assert.deepEqual(lib.span([]), [0, 0]);
  assert.deepEqual(lib.between(s, 2000, 2300).map((ch) => ch.onset), [2000, 2000, 2125, 2250]);
  assert.deepEqual(lib.sounding(s, 1000).map((ch) => ch.notes[0].pitch), [3600, 6700]);
});
