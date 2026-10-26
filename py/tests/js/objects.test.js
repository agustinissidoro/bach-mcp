// The runners (v8: bachmcp.runner.generator, bachmcp.runner.transformer),
// run on a stand-in for Max.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const vm = require("vm");
const { load, readDict, Dict } = require("./maxmock.js");

const ALGO = `// one line
const params = {
  times: { type: "slider", range: [1, 64], value: 4 },
  register: { type: "range", range: [3600, 9600], value: [6000, 7200] },
  mode: { type: "menu", options: ["up", "down"] },
  seed: { type: "seed", value: 1 },
};
function generate(p, input) {
  const s = score();
  const v = s.voice("Flute");
  for (let i = 0; i < p.times; i++) {
    const k = p.mode === "up" ? i : p.times - 1 - i;
    v.note(i * 100, lerp(p.register[0], p.register[1], k / Math.max(1, p.times - 1)), 100);
  }
  if (input) for (const voice of input.voices) s.voices.push(voice);
  return s;
}
`;

function tempFile(text) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "bachmcp-"));
  const file = path.join(dir, "test_algo.js");
  fs.writeFileSync(file, text);
  return file;
}

function last(out, index, selector) {
  for (let i = out.length - 1; i >= 0; i--) {
    if (out[i][0] === index && (selector === undefined || out[i][1] === selector)) return out[i];
  }
  return null;
}

function scoreOut(m) {
  const msg = last(m.out, 0, "dictionary");
  return msg ? readDict(msg[2]) : null;
}

test("load: spec to the panel, score out, loaded to the status outlet", () => {
  const m = load("bachmcp.runner.generator.js");
  m.send("setname", "algo");
  m.send("load", tempFile(ALGO));
  const spec = JSON.parse(last(m.out, 1, "spec")[2]);
  assert.equal(spec.title, "test_algo");
  assert.deepEqual(spec.params.map((p) => [p.name, p.type]), [["times", "slider"], ["register", "range"], ["mode", "menu"], ["seed", "seed"]]);
  assert.deepEqual(last(m.out, 2), [2, "algo", "algo_loaded", "test_algo.js", 4, last(m.out, 2)[5]]);
  const score = scoreOut(m);
  assert.deepEqual(score.voices[0].chords.map((c) => c.notes[0].pitch), [6000, 6400, 6800, 7200]);
  assert.equal(last(m.out, 1, "status")[2], "ok");
});

test("a parameter message updates the panel and runs again (debounced)", () => {
  const m = load("bachmcp.runner.generator.js");
  m.send("load", tempFile(ALGO));
  const before = m.out.length;
  m.send("times", 2.6);
  m.send("mode", "down");
  assert.deepEqual(last(m.out, 1, "set"), [1, "set", "mode", "down"]);
  assert.deepEqual(m.out.slice(before).filter((o) => o[1] === "set")[0], [1, "set", "times", 3]);
  assert.equal(m.out.slice(before).filter((o) => o[0] === 0).length, 0, "nothing runs before the task fires");
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes[0].pitch), [7200, 6600, 6000]);
  assert.deepEqual(last(m.out, 2).slice(0, 4), [2, "algo", "algo_done", 3]);
});

test("unknown parameters and bad values are reported, not fatal", () => {
  const m = load("bachmcp.runner.generator.js");
  m.send("tempo", 3);
  assert.match(last(m.out, 2)[3], /no algorithm loaded/);
  m.send("load", tempFile(ALGO));
  m.send("tempo", 3);
  assert.match(last(m.out, 2)[3], /"tempo" is not a parameter. Parameters: times, register, mode, seed/);
  m.send("mode", "sideways");
  assert.match(last(m.out, 1, "status")[3], /cannot use/);
});

test("reloading keeps values of parameters that keep their name and type", () => {
  const file = tempFile(ALGO);
  const m = load("bachmcp.runner.generator.js");
  m.send("load", file);
  m.send("times", 8);
  m.send("register", 4800, 6000);
  m.flush();
  fs.writeFileSync(file, ALGO.replace('register: { type: "range"', 'register: { type: "slider"').replace(
    "value: [6000, 7200]", "value: 6000").replace("lerp(p.register[0], p.register[1],", "lerp(p.register, p.register + 1200,"));
  m.flush(true); // the watcher notices the change
  const spec = JSON.parse(last(m.out, 1, "spec")[2]);
  const values = Object.fromEntries(spec.params.map((p) => [p.name, p.value]));
  assert.equal(values.times, 8);
  assert.equal(values.register, 6000, "the type changed: back to the declared value");
  assert.equal(scoreOut(m).voices[0].chords.length, 8);
});

test("a broken file keeps the last good score and names the line", () => {
  const file = tempFile(ALGO);
  const m = load("bachmcp.runner.generator.js");
  m.send("load", file);
  const good = last(m.out, 0, "dictionary");
  fs.writeFileSync(file, ALGO.replace("const s = score();", "const s = score();\n  undefinedThing();"));
  m.send("reload");
  assert.match(last(m.out, 2)[3], /undefinedThing is not defined \(line 10\)/);
  assert.equal(last(m.out, 0, "dictionary"), good);
});

test("a runner refuses an algorithm of the other kind", () => {
  const g = load("bachmcp.runner.generator.js");
  g.send("setname", "scales1");
  g.send("load", tempFile(TRANSFORMER));
  assert.deepEqual(last(g.out, 2), [2, "scales1", "algo_error", "this is a generator: the file must define function produce(p) { ... }"]);
  const t = load("bachmcp.runner.transformer.js");
  t.send("load", tempFile(ALGO));
  assert.match(last(t.out, 2)[3], /this is a transformer: the file must define function transform\(source, p\)/);
  assert.equal(last(t.out, 1, "spec"), null, "nothing reaches the panel");
});

test("the setname message can carry a file to load", () => {
  const m = load("bachmcp.runner.generator.js");
  m.send("setname", "algo", tempFile(ALGO));
  assert.equal(last(m.out, 2)[2], "algo_loaded");
});

const TRANSFORMER = `const params = { shift: { type: "slider", range: [-1200, 1200], value: 100 } };
function transform(source, p) { const out = copy(source); eachNote(out, (n) => { n.pitch += p.shift; }); return out; }`;

function scorePitches(m) {
  return scoreOut(m).voices.map((v) => v.chords.map((c) => c.notes[0].pitch));
}

test("a score at the inlet is the source; a producer needs none", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  assert.deepEqual(last(m.out, 1, "source"), [1, "source", 1, "inlet"]);
  const p = load("bachmcp.runner.generator.js");
  p.send("load", tempFile(ALGO));
  assert.equal(JSON.parse(last(p.out, 1, "spec")[2]).kind, "producer");
  assert.equal(p.named.length, 0);
});

// A score arriving at the inlet as a dictionary, as every object sends one.
let inputCount = 0;
function inputFrom(m, pitch) {
  const d = new Dict(`input_${++inputCount}`);
  d.parse(JSON.stringify({ voices: [{ chords: [{ onset: 0, notes: [{ pitch, dur: 1000, vel: 100 }] }] }] }));
  m.send("input", "dictionary", d.name);
}

test("keep: the first score at the inlet becomes the source and is saved; later ones are ignored", () => {
  const file = tempFile(TRANSFORMER);
  const sourceFile = file.replace(/\.js$/, ".source.json");
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", file);
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  assert.equal(JSON.parse(fs.readFileSync(sourceFile, "utf8")).voices[0].chords[0].notes[0].pitch, 3600, "saved next to the algorithm");
  inputFrom(m, 4800);
  m.flush();
  m.send("shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]], "still the original");
  const again = load("bachmcp.runner.transformer.js");
  again.send("load", file);
  assert.deepEqual(scorePitches(again), [[3700]], "reopened: the saved source");
  m.send("capture");
  inputFrom(m, 4800);
  m.flush();
  assert.deepEqual(scorePitches(m), [[5000]], "capture: the next input is the new source");
});

test("without a source a transformer waits for one", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  assert.equal(scoreOut(m), null);
  assert.ok(m.posts.some((t) => /waiting for a source/.test(t)));
  inputFrom(m, 6000);
  m.flush();
  assert.deepEqual(scorePitches(m), [[6100]]);
  assert.equal(last(m.out, 2)[2], "algo_loaded");
});

test("follow: every score at the inlet becomes the source; only the first one runs by itself", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("sourcemode", "follow");
  assert.deepEqual(last(m.out, 1, "sourcemode"), [1, "sourcemode", "follow"]);
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  const runs = m.out.filter((o) => o[0] === 0).length;
  inputFrom(m, 3700);  // the result, back from the roll
  m.flush();
  assert.equal(m.out.filter((o) => o[0] === 0).length, runs, "no run: no loop through the roll");
  assert.deepEqual(last(m.out, 1, "source"), [1, "source", 1, "inlet"]);
  m.send("shift", 100);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]], "the next change transforms the latest score");
  m.send("sourcemode", "maybe");
  assert.match(last(m.out, 2)[3], /sourcemode is keep or follow/);
});
