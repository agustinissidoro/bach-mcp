// bachmcp.lib.units.js: units and pitch names. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib } = require("./fixtures.js");

test("units and pitch names", () => {
  assert.deepEqual([lib.SEMITONE, lib.QUARTERTONE, lib.OCTAVE, lib.MIDDLE_C, lib.SECOND], [100, 50, 1200, 6000, 1000]);
  assert.equal(lib.pitch("Db4"), 6100);
  assert.equal(lib.name(6100), "C#4");
  assert.throws(() => lib.pitch("H2"), /a name is a letter/);
});
