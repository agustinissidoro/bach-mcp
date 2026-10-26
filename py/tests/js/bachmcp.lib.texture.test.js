// bachmcp.lib.texture.js: register and texture. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib, n, c, piece } = require("./fixtures.js");

test("register: ambitus and centroid", () => {
  const s = piece();
  assert.deepEqual(lib.ambitus(s), [3600, 7900]);
  assert.equal(lib.ambitus([]), null);
  assert.equal(lib.centroid([c(0, n(6000, 300), n(7200, 100))]), 6300);
  assert.equal(lib.centroid([]), null);
});

test("a profile measures in windows and reads between them", () => {
  const s = piece();
  const density = lib.profile(s, "density", { window: 1000 });
  assert.equal(density.times[0], 500);
  assert.equal(density.values[0], 6, "six attacks in the first second");
  assert.equal(density(500), 6);
  const top = lib.profile(s, "top", { window: 1000, step: 1000 });
  assert.deepEqual(top.values, [6700, 6700, 7200, null, 7900, 7100]);
  assert.equal(top(3500), (7200 + 7900) / 2, "silent windows are skipped");
  const polyphony = lib.profile([c(0, n(6000, 1000), n(6400, 1000))], "polyphony", { window: 1000 });
  assert.equal(polyphony.values[0], 2);
  assert.throws(() => lib.profile(s, "brightness"), /measure is one of density/);
});
