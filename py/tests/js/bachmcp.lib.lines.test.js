// bachmcp.lib.lines.js: lines and shapes. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib, piece } = require("./fixtures.js");

test("lines, intervals, contours and turns", () => {
  const s = piece();
  const first = lib.phrases(s, 400)[0];
  assert.deepEqual(lib.melody(first), [6000, 6200, 6400, 6700]);
  assert.deepEqual(lib.melody(first, "bottom"), [3600, 6200, 6400, 6700]);
  assert.deepEqual(lib.intervals([6000, 6400, 6200]), [400, -200]);
  assert.deepEqual(lib.contour([6000, 6400, 6400, 6200]), [1, 0, -1]);
  assert.deepEqual(lib.contour(first), [1, 1, 1]);
  assert.deepEqual(lib.turns([1, 3, 2, 2, 5, 0]), { peaks: [1, 4], troughs: [2] });
  assert.deepEqual(lib.iois(s.voices[0].chords.slice(0, 4)), [250, 250, 250]);
});
