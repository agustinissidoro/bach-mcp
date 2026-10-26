// bachmcp.lib.procedures.js: processes that unfold step by step. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib } = require("./fixtures.js");

test("procedures", () => {
  assert.deepEqual(lib.euclid(3, 8), [1, 0, 0, 1, 0, 0, 1, 0]);
  assert.deepEqual(lib.euclid(3, 8, 1), [0, 0, 1, 0, 0, 1, 0, 1]);
  assert.equal(lib.rewrite("A", { A: "AB", B: "A" }, 4), "ABAABABA");
  assert.deepEqual(lib.automaton(90, 7, 3).map((r) => r.join("")), ["0001000", "0010100", "0100010"]);
  assert.deepEqual(lib.iterate(4, 1, (x) => x * 2), [1, 2, 4, 8]);
  const r = lib.makeRandom(1);
  const w = lib.walk({ n: 200, start: 6000, step: 300, min: 5500, max: 6500, rng: r });
  assert.equal(w.length, 200);
  assert.ok(w.every((x) => x >= 5500 && x <= 6500));
  const chain = lib.markov({ a: { b: 1 }, b: ["a"] }, { n: 5, start: "a" });
  assert.deepEqual(chain, ["a", "b", "a", "b", "a"]);
  assert.deepEqual(lib.markov({ 6000: { 6200: 1 }, 6200: [] }, { n: 5, start: 6000 }), [6000, 6200]);
  assert.throws(() => lib.rewrite("A", { A: "AA" }, 40), /grew past/);
});
