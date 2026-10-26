// bachmcp.lib.harmony.js: harmony. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib, n, c } = require("./fixtures.js");

test("harmony: pitch classes, prime form, interval vector, field", () => {
  assert.deepEqual(lib.pcs([6000, 7200, 6450, 3700]), [0, 100, 450]);
  assert.deepEqual(lib.primeForm([6000, 6400, 6700]), [0, 3, 7], "major triad");
  assert.deepEqual(lib.primeForm([6000, 6300, 6700]), [0, 3, 7], "minor triad: the same class");
  assert.deepEqual(lib.primeForm([6000, 6100, 6400, 6600]), [0, 1, 4, 6], "all-interval tetrachord");
  assert.deepEqual(lib.primeForm([6500, 6000, 7700, 6200]), [0, 2, 5], "duplicates and octaves count once");
  assert.deepEqual(lib.intervalVector([6000, 6100, 6400, 6600]), [1, 1, 1, 1, 1, 1]);
  assert.deepEqual(lib.intervalVector([6000, 6400, 6700]), [0, 0, 1, 1, 1, 0]);
  const f = lib.field([c(0, n(6000, 500)), c(500, n(7200, 250)), c(750, n(6000, 250))]);
  assert.deepEqual(f, [{ pitch: 6000, weight: 750 }, { pitch: 7200, weight: 250 }]);
  assert.deepEqual(lib.field([c(0, n(6000, 500)), c(500, n(7200, 250))], { classes: true }), [{ pitch: 0, weight: 750 }]);
});
