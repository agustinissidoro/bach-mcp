// bachmcp.lib.index.js: what an algorithm file has in scope. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { lib, loader, LIB_DIR, piece } = require("./fixtures.js");

test("the index puts every topic in scope, and nothing else", () => {
  const fs = require("fs");
  const path = require("path");
  const topics = fs.readdirSync(LIB_DIR).filter((f) => /^bachmcp\.lib\.\w+\.js$/.test(f))
    .map((f) => f.split(".")[2]).filter((t) => !["index", "base", "random"].includes(t));
  for (const topic of topics) {
    for (const name of Object.keys(require(path.join(LIB_DIR, `bachmcp.lib.${topic}.js`)))) {
      if (!["Score", "Voice", "MEASURES", "MIN_CENTS", "MAX_CENTS", "MAX_NOTES", "fmt", "nameToCents", "centsToName"].includes(name)) assert.ok(lib.LIBRARY.includes(name), `${topic}: ${name} is not in scope`);
    }
  }
  assert.ok(lib.LIBRARY.includes("rng") && lib.LIBRARY.includes("Math"));
  assert.ok(!lib.LIBRARY.includes("AlgoError") && !lib.LIBRARY.includes("Score"));
  assert.equal(new Set(lib.LIBRARY).size, lib.LIBRARY.length, "no name twice");
});

test("in scope in an algorithm file", () => {
  const code = `
    const params = { gap: { type: "slider", range: [100, 2000], value: 400, unit: "ms" } };
    function transform(source, p) {
      const out = copy(source);
      const parts = phrases(out, p.gap);
      const labels = classify(parts);
      parts.forEach((part, i) => {
        if (labels[i] !== "A") return;
        const centre = centroid(part);
        for (const ch of part) for (const nt of ch.notes) nt.pitch = Math.round(2 * centre - nt.pitch);
      });
      return out;
    }`;
  const compiled = loader.compile(code);
  const source = { voices: [piece().voices[0]] };
  const result = loader.run(compiled, { gap: 400 }, source);
  const pitches = result.score.voices[0].chords.map((ch) => ch.notes[0].pitch);
  assert.deepEqual(pitches.slice(0, 4), [6800, 6600, 6400, 6100], "phrase A inverted around its centre (6400)");
  assert.deepEqual(pitches.slice(8), [7900, 7100], "phrase B untouched");
  for (const name of ["sections", "profile", "primeForm", "similarity", "between"]) assert.ok(lib.LIBRARY.includes(name), name);
});
