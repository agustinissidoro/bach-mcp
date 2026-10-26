// bachmcp.lib.likeness.js: comparing passages. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib, piece } = require("./fixtures.js");

test("similarity hears a transposed, faster repeat as alike, and something else as not", () => {
  const voice = piece().voices[0].chords;
  const [a, b, other] = lib.phrases(voice, 400);
  assert.ok(lib.similarity(a, a) > 0.99);
  assert.ok(lib.similarity(a, b) > 0.8, `repeat: ${lib.similarity(a, b)}`);
  assert.ok(lib.similarity(a, other) < 0.6, `other: ${lib.similarity(a, other)}`);
  assert.deepEqual(lib.classify([a, b, other]), ["A", "A", "B"]);
  assert.deepEqual(lib.classify([a, b, other], 1.01), ["A", "B", "C"]);
  const f = lib.features(a);
  assert.deepEqual([f.start, f.end, f.notes, f.contour.join(" ")], [0, 1250, 4, "1 1 1"]);
});
