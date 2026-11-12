// bachmcp.lib.markers.js: markers with a role, the measures bach.quantize reads. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib } = require("./fixtures.js");

const brief = (x) => lib.markersOf(x).map((m) => [m.onset, m.role].concat(m.content ? [m.content] : []));

test("each role writes its marker into the header, in time order, tempo before its barline", () => {
  const s = lib.score();
  lib.barline(s, 2000);
  lib.division(s, 1000);
  lib.timesig(s, 0, [3, 4]);
  lib.tempo(s, 0, 90);
  lib.subdivision(s, 500, "u");
  assert.deepEqual(s.header.markers, [
    { onset: 0, name: [], role: "tempo", content: ["1/4", 90] },
    { onset: 0, name: [], role: "timesig", content: [3, 4] },
    { onset: 500, name: ["u"], role: "subdivision" },
    { onset: 1000, name: [], role: "division" },
    { onset: 2000, name: [], role: "barline" },
  ]);
  assert.deepEqual(lib.markersOf(s, "barline").map((m) => m.onset), [2000]);
});

test("one opening of a measure at one time: a timesig takes a barline's place, never both", () => {
  const s = lib.score();
  lib.barline(s, 0);
  lib.timesig(s, 0, [4, 4]);
  lib.barline(s, 0);
  lib.timesig(s, 0, [5, 8]);
  lib.barline(s, 1000);
  lib.barline(s, 1000);
  assert.deepEqual(brief(s), [[0, "timesig", [5, 8]], [1000, "barline"]]);
});

test("they work on a plain score, such as a transformer's source, and keep its labels", () => {
  const source = { voices: [], header: { markers: [{ onset: 500, name: ["A"], role: "none" }] } };
  lib.grid(source, { bar: 1000, count: 2 });
  assert.deepEqual(brief(source), [[0, "timesig", [4, 4]], [500, "none"], [1000, "barline"], [2000, "barline"]]);
  lib.clearGrid(source);
  assert.deepEqual(source.header.markers, [{ onset: 500, name: ["A"], role: "none" }]);
  const bare = { voices: [] };
  lib.barline(bare, 0);
  assert.equal(bare.header.markers.length, 1);
  assert.deepEqual(lib.markersOf({ voices: [] }), []);
});

test("grid: equal measures, a closing barline, n - 1 beats, and chained grids", () => {
  const s = lib.score();
  let end = lib.grid(s, { timesig: [3, 4], bar: 1500, count: 2, beats: true });
  assert.equal(end, 3000);
  end = lib.grid(s, { start: end, timesig: [[2, 2, 3], 8], bar: 1750, count: 1 });
  assert.equal(end, 4750);
  assert.deepEqual(brief(s), [
    [0, "timesig", [3, 4]], [500, "division"], [1000, "division"],
    [1500, "barline"], [2000, "division"], [2500, "division"],
    [3000, "timesig", [[2, 2, 3], 8]], [3250, "subdivision"], [3500, "division"], [3750, "subdivision"],
    [4000, "division"], [4250, "subdivision"], [4500, "subdivision"],
    [4750, "barline"],
  ]);
});

test("mistakes are said in words", () => {
  const s = lib.score();
  assert.throws(() => lib.timesig(s, 0, [4, 3]), /a time signature is \[numerator, denominator\]/);
  assert.throws(() => lib.timesig(s, 0, "4/4"), /a time signature is/);
  assert.throws(() => lib.barline(s, "0"), /onset must be a number of milliseconds/);
  assert.throws(() => lib.barline(0), /the first argument is the score/);
  assert.throws(() => lib.tempo(s, 0, 60, 0.25), /the figure is a note value as text/);
  assert.throws(() => lib.grid(s, { count: 2 }), /bar is how long one measure lasts/);
  assert.throws(() => lib.grid(s, { bar: 1000, count: 1.5 }), /count is a whole number of measures/);
});

test("score().marker takes a content too", () => {
  const s = lib.score().marker(0, "A").marker(0, "", "timesig", [2, 4]);
  assert.deepEqual(s.header.markers, [{ onset: 0, name: ["A"], role: "none" }, { onset: 0, name: [], role: "timesig", content: [2, 4] }]);
});
