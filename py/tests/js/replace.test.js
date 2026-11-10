// bachmcp.bpatcher.replace.js: [bachmcp.transformer t1] becomes [bpatcher @name bachmcp.bpatcher.algorithm @args t1 transformer].
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { load } = require("./maxmock.js");

/** The script in a stand-in abstraction; returns what it made of it. */
function replaced(args, typed) {
  const made = [];
  const parent = {
    newdefault: (x, y, cls, ...words) => { const bp = { cls, words }; made.push(bp); return bp; },
    remove: (box) => { made.removed = box; },
  };
  const box = { rect: [10, 20, 90, 42] };
  const m = load("bachmcp.bpatcher.replace.js", { args, globals: { patcher: { box, parentpatcher: parent } } });
  if (typed.length) m.send("list", ...typed);
  else m.send("bang");
  m.flush();
  return { made, box, posts: m.posts };
}

test("a fixed type comes right after the typed name: #1 the name, #2 the type", () => {
  const r = replaced(["bachmcp.bpatcher.algorithm", 288, 365, "transformer"], ["t1"]);
  assert.deepEqual(r.made[0].words, ["@name", "bachmcp.bpatcher.algorithm", "@args", "t1", "transformer"]);
  assert.deepEqual(Array.from(r.made[0].rect), [10, 20, 298, 385]);
  assert.equal(r.made.removed, r.box, "the small box goes");
  const more = replaced(["bachmcp.bpatcher.algorithm", 288, 365, "selector"], ["s1", "extra"]);
  assert.deepEqual(more.made[0].words.slice(2), ["@args", "s1", "selector", "extra"]);
});

test("with a fixed type, no name: it says so and stays", () => {
  const r = replaced(["bachmcp.bpatcher.algorithm", 288, 365, "generator"], []);
  assert.equal(r.made.length, 0);
  assert.match(r.posts.join(""), /bachmcp\.generator: give the instance a name, e\.g\. \[bachmcp\.generator t1\]/);
});

test("without fixed arguments, as before: the typed ones, or none", () => {
  assert.deepEqual(replaced(["bachmcp.bpatcher.thing", 100, 50], ["a", "b"]).made[0].words, ["@name", "bachmcp.bpatcher.thing", "@args", "a", "b"]);
  assert.deepEqual(replaced(["bachmcp.bpatcher.thing", 100, 50], []).made[0].words, ["@name", "bachmcp.bpatcher.thing"]);
});
