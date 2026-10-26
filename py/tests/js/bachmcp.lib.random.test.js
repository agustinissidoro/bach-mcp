// bachmcp.lib.random.js: seeded randomness. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib } = require("./fixtures.js");

test("seeded random streams", () => {
  const g = lib.makeRandom("x");
  for (let i = 0; i < 100; i++) {
    const k = g.int(3, 5);
    assert.ok(k >= 3 && k <= 5 && Number.isInteger(k));
  }
  assert.deepEqual(g.shuffle([1, 2, 3, 4]).sort(), [1, 2, 3, 4]);
  assert.equal(g.weighted(["a", "b"], [0, 1]), "b");
  assert.equal(lib.makeRandom(7)(), lib.makeRandom(7)(), "the same seed, the same numbers");
  const { rng, Math: seededMath } = lib.seeded({ seed: 1, streams: new Map() });
  assert.equal(rng("a"), rng("a"), "one stream per name");
  assert.notEqual(rng("a"), rng("b"));
  assert.equal(typeof seededMath.random(), "number");
});
