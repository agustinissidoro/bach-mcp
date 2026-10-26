// bachmcp.lib.numbers.js: numbers and shapes. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib } = require("./fixtures.js");

test("numbers and shapes", () => {
  assert.deepEqual(lib.accumulate([100, 200, 50], 1000), [1000, 1100, 1300]);
  assert.deepEqual(lib.linspace(0, 1, 5), [0, 0.25, 0.5, 0.75, 1]);
  assert.deepEqual(lib.seq(3, 10, 5), [10, 15, 20]);
  assert.equal(lib.fold(13, 0, 10), 7);
  assert.equal(lib.wrap(13, 0, 10), 3);
  assert.equal(lib.snap(6037, 50), 6050);
  assert.equal(lib.rescale(5, 0, 10, 100, 200), 150);
  assert.equal(lib.env([[0, 0], [1, 10]])(0.3), 3);
  assert.equal(lib.warp(0.5, 0), 0.5);
  assert.ok(lib.warp(0.5, 3) < 0.5);
});
