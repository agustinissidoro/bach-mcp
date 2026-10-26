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
  m.send("set_name", "algo");
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
  g.send("set_name", "scales1");
  g.send("load", tempFile(TRANSFORMER));
  assert.deepEqual(last(g.out, 2), [2, "scales1", "algo_error", "this is a generator: the file must define function produce(p) { ... }"]);
  const t = load("bachmcp.runner.transformer.js");
  t.send("load", tempFile(ALGO));
  assert.match(last(t.out, 2)[3], /this is a transformer: the file must define function transform\(source, p\)/);
  assert.equal(last(t.out, 1, "spec"), null, "nothing reaches the panel");
});

test("the setname message can carry a file to load", () => {
  const m = load("bachmcp.runner.generator.js");
  m.send("set_name", "algo", tempFile(ALGO));
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

test("nondestructive: the first score at the inlet is held in memory; later ones are ignored until capture_source", () => {
  const file = tempFile(TRANSFORMER);
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", file);
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  assert.ok(!fs.existsSync(file.replace(/\.js$/, ".source.json")), "nothing written to disk");
  inputFrom(m, 4800);
  m.flush();
  m.send("shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]], "still the original");
  m.send("capture_source");
  assert.deepEqual(last(m.out, 1, "dump"), [1, "dump"], "asks the roll for its score");
  inputFrom(m, 4800);
  m.flush();
  assert.deepEqual(scorePitches(m), [[5000]], "capture_source: the next input is the new source");
});

test("write_to_playground writes the source next to the algorithm, only when asked", () => {
  const file = tempFile(TRANSFORMER);
  const m = load("bachmcp.runner.transformer.js");
  m.send("set_name", "t1");
  m.send("write_to_playground");
  assert.match(last(m.out, 2)[3], /no source yet/);
  m.send("load", file);
  inputFrom(m, 3600);
  m.send("write_to_playground");
  const written = path.join(path.dirname(file), "t1.source.json");
  assert.equal(JSON.parse(fs.readFileSync(written, "utf8")).voices[0].chords[0].notes[0].pitch, 3600);
});

test("verbose 0 (default): only errors reach the Max console", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  assert.equal(m.posts.length, 0, "nothing said");
  m.send("load", "/nowhere/x.js");
  assert.ok(m.posts.some((t) => /error: cannot read/.test(t)), "errors are always said");
});

test("load_algo reports a file it cannot load; try_load_algo stays silent", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("set_name", "t1");
  m.send("load_algo", "/nowhere/x.js");
  assert.deepEqual(last(m.out, 2).slice(1, 3), ["t1", "algo_error"]);
  assert.match(last(m.out, 2)[3], /^error: impossible to load \/nowhere\/x\.js/);
  m.send("load_algo", tempFile("const params = {}; function transform(source, p) { return ; "));
  assert.match(last(m.out, 2)[3], /^error: impossible to load test_algo\.js/);
  const before = m.out.length;
  m.send("try_load_algo", "/nowhere/x.js");
  m.send("try_load_algo", tempFile(ALGO));  // a producer: not for a transformer
  assert.equal(m.out.length, before, "silent");
  m.send("try_load_algo", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
});

test("without a source a transformer waits for one", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("verbose", 1);
  m.send("load", tempFile(TRANSFORMER));
  assert.equal(scoreOut(m), null);
  assert.ok(m.posts.some((t) => /waiting for a source/.test(t)));
  inputFrom(m, 6000);
  m.flush();
  assert.deepEqual(scorePitches(m), [[6100]]);
  assert.equal(last(m.out, 2)[2], "algo_loaded");
});

test("destructive: every input is the source, never transformed by itself; processing until it comes back", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("set_name", "t1");
  m.send("source_mode", 0);
  assert.deepEqual(last(m.out, 1, "source_mode"), [1, "source_mode", 0]);
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  m.flush();
  assert.equal(scoreOut(m), null, "an input does not run");
  m.send("shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]]);
  assert.deepEqual(last(m.out, 2), [2, "t1", "processing", 1]);
  const outs = () => m.out.filter((o) => o[0] === 0).length;
  const runs = outs();
  m.send("shift", 300);
  m.flush();
  assert.equal(outs(), runs, "processing: the change is kept, nothing goes out");
  inputFrom(m, 5000);  // back from outside, edited
  m.flush();
  assert.deepEqual(last(m.out, 2), [2, "t1", "processing", 0]);
  assert.equal(outs(), runs, "the returning score is not transformed: no loop");
  m.send("dump");
  assert.deepEqual(scorePitches(m), [[5300]], "dump transforms the score that came back, with the kept value");
  m.send("bang");
  assert.deepEqual(scorePitches(m), [[5300]], "dump always outputs, from the last input, never from its own result");
  m.wait(2999);
  assert.equal(last(m.out, 2, "t1") && m.out.some((o) => o[2] === "timeout"), false, "still waiting");
  m.wait(3000);
  assert.deepEqual(m.out.slice(-2), [[2, "t1", "timeout", 1], [2, "t1", "processing", 0]], "nothing came back");
  m.send("shift", 100);
  m.flush();
  assert.deepEqual(scorePitches(m), [[5100]], "changes output again");
  m.send("source_mode", 2);
  assert.match(last(m.out, 2)[3], /source_mode is 0 \(destructive\) or 1/);
});

test("auto_dump 0: a parameter change outputs nothing until dump", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  m.send("auto_dump", 0);
  inputFrom(m, 3600);
  m.flush();
  const outs = () => m.out.filter((o) => o[0] === 0).length;
  const runs = outs();
  m.send("shift", 500);
  m.flush();
  assert.equal(outs(), runs);
  m.send("dump");
  assert.deepEqual(scorePitches(m), [[4100]]);
});
