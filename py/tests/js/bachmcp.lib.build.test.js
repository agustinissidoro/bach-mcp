// bachmcp.lib.build.js: making and handling scores. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib } = require("./fixtures.js");

test("the score builder writes bachjson-complete directly", () => {
  const s = lib.score();
  const v = s.voice("Piano");
  v.chord(0, [4800, 6400], 1000, { vel: 40, slots: { 20: ["p"], 23: ["diamond"] } });
  v.note(1000, 6700, 500).notes[0].slots = { 24: ["dolce"] };
  s.voice("Piano").note(2000, { pitch: 6000, dur: 250, breakpoints: [[0, 0, 0], [1, 200, 0]] }, 999);
  s.voice("Cello", "F").note(0, 3600, 3000);
  s.marker(0, "A");
  assert.equal(v.end, 2250);
  assert.equal(s.end, 3000);
  assert.deepEqual(JSON.parse(JSON.stringify(s)), {
    header: { voicenames: [["Piano"], ["Cello"]], clefs: ["G", "F"], markers: [{ onset: 0, name: ["A"], role: "none" }] },
    voices: [
      { chords: [
        { onset: 0, notes: [
          { pitch: 4800, dur: 1000, vel: 40, slots: { 20: ["p"], 23: ["diamond"] }, flag: 0 },
          { pitch: 6400, dur: 1000, vel: 40, slots: { 20: ["p"], 23: ["diamond"] }, flag: 0 }], flag: 0 },
        { onset: 1000, notes: [{ pitch: 6700, dur: 500, vel: 80, flag: 0, slots: { 24: ["dolce"] } }], flag: 0 },
        { onset: 2000, notes: [{ pitch: 6000, dur: 250, vel: 80, breakpoints: [[0, 0, 0], [1, 200, 0]], flag: 0 }], flag: 0 },
      ], flag: 0 },
      { chords: [{ onset: 0, notes: [{ pitch: 3600, dur: 3000, vel: 80, flag: 0 }], flag: 0 }], flag: 0 },
    ],
  });
  const chord = s.voices[0].chords[0];
  chord.notes[1].slots[20] = ["f"];
  assert.deepEqual(chord.notes[0].slots[20], ["p"], "each note has its own slots");
});

test("copy and eachNote", () => {
  const s = { voices: [{ chords: [{ onset: 0, notes: [{ pitch: 6000, dur: 1000 }, { pitch: 6400, dur: 200 }] }] }] };
  const copied = lib.copy(s);
  lib.eachNote(copied, (n) => { n.pitch += 1; });
  assert.equal(copied.voices[0].chords[0].notes[1].pitch, 6401);
  assert.equal(s.voices[0].chords[0].notes[1].pitch, 6400);
});
