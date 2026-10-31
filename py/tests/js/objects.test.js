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

test("write_to_playground writes the last score sent to the playground's scores folder", () => {
  const playground = fs.mkdtempSync(path.join(os.tmpdir(), "bachmcp-"));
  for (const dir of ["algorithms", "scores"]) fs.mkdirSync(path.join(playground, dir));
  const file = path.join(playground, "algorithms", "t1.js");
  fs.writeFileSync(file, TRANSFORMER);
  const m = load("bachmcp.runner.transformer.js");
  m.send("set_name", "t1");
  m.send("write_to_playground");
  assert.match(last(m.out, 2)[3], /no algorithm loaded/);
  m.send("load", file);
  m.send("write_to_playground");
  assert.match(last(m.out, 2)[3], /no score sent yet/);
  inputFrom(m, 3600);
  m.flush();
  m.send("write_to_playground");
  const written = path.join(playground, "scores", "t1.json");
  assert.deepEqual(JSON.parse(fs.readFileSync(written, "utf8")).voices[0].chords[0].notes.map((n) => n.pitch),
                   scorePitches(m)[0], "the result, not the source");
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

test("a load runs nothing; the first run asks the roll for a dump, and processes what comes in", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("set_name", "t1");
  m.send("load", tempFile(TRANSFORMER));
  assert.equal(scoreOut(m), null);
  assert.equal(last(m.out, 1, "dump"), null, "no dump on load");
  assert.equal(last(m.out, 2, "t1"), null, "no algo_loaded: nothing ran");
  m.send("dump");
  assert.deepEqual(last(m.out, 1, "dump"), [1, "dump"], "asks the roll for its score");
  assert.deepEqual(last(m.out, 2), [2, "t1", "processing", 1]);
  inputFrom(m, 6000);
  assert.deepEqual(scorePitches(m), [[6100]], "the answer is processed at once");
  assert.equal(last(m.out, 2, "t1")[2], "algo_done");
});

test("nondestructive: once the source is held, a change runs without a dump", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  const dumps = () => m.out.filter((o) => o[0] === 1 && o[1] === "dump").length;
  const before = dumps();
  m.send("shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]]);
  assert.equal(dumps(), before, "no dump");
});

test("destructive: every run is change, dump, process; an unasked input is never transformed by itself", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("set_name", "t1");
  m.send("source_mode", 0);
  assert.deepEqual(last(m.out, 1, "source_mode"), [1, "source_mode", 0]);
  m.send("load", tempFile(TRANSFORMER));
  m.send("dump");
  inputFrom(m, 3600);  // the answer to the dump
  assert.deepEqual(scorePitches(m), [[3700]]);
  const outs = () => m.out.filter((o) => o[0] === 0).length;
  const dumps = () => m.out.filter((o) => o[0] === 1 && o[1] === "dump").length;
  let runs = outs();
  inputFrom(m, 4000);  // unasked, e.g. the result coming back through a roll
  m.flush();
  assert.equal(outs(), runs, "no loop");
  const d = dumps();
  m.send("shift", 200);
  m.flush();
  assert.equal(dumps(), d + 1, "the change asks for a dump");
  assert.deepEqual(last(m.out, 2), [2, "t1", "processing", 1]);
  assert.equal(outs(), runs, "nothing goes out before the score comes in");
  m.send("shift", 300);
  m.flush();
  assert.equal(dumps(), d + 1, "already asked: no second dump");
  inputFrom(m, 5000);  // the roll answers, edited by hand
  assert.ok(m.out.some((o) => o[0] === 2 && o[2] === "processing" && o[3] === 0));
  assert.deepEqual(scorePitches(m), [[5300]], "processed with the latest value");
  m.send("dump");
  assert.equal(dumps(), d + 2, "dump asks too");
  m.wait(2999);
  assert.equal(m.out.some((o) => o[2] === "timeout"), false, "still waiting");
  m.wait(3000);
  assert.deepEqual(m.out.slice(-2), [[2, "t1", "timeout", 1], [2, "t1", "processing", 0]], "nothing came in");
  m.send("shift", 100);
  m.flush();
  assert.equal(dumps(), d + 3, "the next change asks again");
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

// ── The selector, and the transformer's input_mode ──────────────────────── //

const SELECTOR = `const params = { above: { type: "slider", range: [0, 12700], value: 6000 } };
function select(source, p) {
  const out = [];
  eachNote(source, (n) => { if (n.pitch > p.above) out.push(n); });
  return out;
}
`;

function inputScore(m, score) {
  const d = new Dict(`input_${++inputCount}`);
  d.parse(JSON.stringify(score));
  m.send("input", "dictionary", d.name);
}

const THREE = { voices: [{ chords: [
  { onset: 0, notes: [{ pitch: 5500, dur: 500, vel: 90 }, { pitch: 6400, dur: 500, vel: 90 }] },
  { onset: 500, notes: [{ pitch: 7200, dur: 500, vel: 90 }] },
] }] };

test("a selector outputs the selected notes flagged in the slot, then clearselection and sel note", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("set_name", "s1");
  m.send("load", tempFile(SELECTOR));
  assert.equal(last(m.out, 1), null, "no dump on load");
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  const bach = m.out.filter((o) => o[0] === 1).map((o) => o.slice(1).join(" "));
  assert.deepEqual(bach, ["dump", "clearselection", "sel note [ 1 1 2 ] [ 1 2 1 ]"], "dump asks for the score, then selects in it");
  const only = scoreOut(m);
  assert.deepEqual(only.header.slotinfo["11"], { name: ["selected"], type: ["int"], range: [0, 1], default: [0] });
  assert.deepEqual(only.voices[0].chords.map((c) => c.notes.map((n) => [n.pitch, n.slots["11"][0]])), [[[6400, 1]], [[7200, 1]]]);
  assert.ok(m.out.findIndex((o) => o[0] === 0) < m.out.findIndex((o) => o[0] === 1 && o[1] === "clearselection"), "the score before the commands");
  assert.match(last(m.out, 2, "status")[3], /2 notes selected/);
  assert.deepEqual(last(m.out, 3).slice(0, 4), [3, "s1", "algo_done", 2]);
  m.send("dump_selection_only", 0);
  assert.deepEqual(last(m.out, 2, "dump_selection_only"), [2, "dump_selection_only", 0]);
  m.send("dump");
  inputScore(m, THREE);
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes.map((n) => n.slots["11"][0])), [[0, 1], [1]], "the whole source, flagged");
  m.send("clear_selection");
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes.map((n) => n.slots["11"][0])), [[0, 0], [0]]);
  assert.deepEqual(last(m.out, 1), [1, "clearselection"]);
});

test("selections are not cumulative: each run clears the previous one (involutive ignored)", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("load", tempFile(SELECTOR));
  m.send("involutive", 1);
  m.send("source_mode", 0);
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  m.send("above", 7000);
  m.flush();
  assert.deepEqual(last(m.out, 1), [1, "dump"], "a change asks the roll for its score");
  inputScore(m, THREE);
  assert.deepEqual(m.out.filter((o) => o[0] === 1).slice(-2).map((o) => o.slice(1).join(" ")),
    ["clearselection", "sel note [ 1 2 1 ]"]);
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes.map((n) => n.pitch)), [[7200]]);
});

test("a selector refuses a result that is not notes of the source", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("load", tempFile(`const params = {};
function select(source, p) { return [[1, 9, 1]]; }`));
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  assert.match(last(m.out, 3)[3], /not a note of the source/);
});

test("a destructive selector: an unasked input becomes the source but is not selected in; no answer times out", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("set_name", "s1");
  m.send("load", tempFile(SELECTOR));
  m.send("source_mode", 0);
  m.send("dump");
  inputScore(m, THREE);  // the answer to the dump
  const sels = () => m.out.filter((o) => o[0] === 1 && o[1] !== "dump").length;
  const n = sels();
  inputScore(m, THREE);  // unasked, e.g. the roll after the sel
  m.flush();
  assert.equal(sels(), n, "no loop");
  m.send("dump");
  assert.deepEqual(last(m.out, 3), [3, "s1", "processing", 1]);
  m.wait(3000);
  assert.deepEqual(m.out.slice(-2), [[3, "s1", "timeout", 1], [3, "s1", "processing", 0]]);
});

test("input_mode 1: a transformer changes only the notes flagged in the slot named selected", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  m.send("input_mode", 1);
  const flagged = JSON.parse(JSON.stringify(THREE));
  flagged.header = { slotinfo: { "7": { name: ["selected"], type: ["int"] } } };
  flagged.voices[0].chords[0].notes[1].slots = { "7": [1] };
  inputScore(m, flagged);
  m.flush();
  const out = scoreOut(m);
  assert.deepEqual(out.voices[0].chords.map((c) => [c.onset, c.notes.map((n) => n.pitch)]),
    [[0, [5500]], [0, [6500]], [500, [7200]]]);
  assert.deepEqual(out.header, flagged.header);
  const bare = load("bachmcp.runner.transformer.js");
  bare.send("load", tempFile(TRANSFORMER));
  bare.send("input_mode", 1);
  inputScore(bare, THREE);
  bare.flush();
  assert.match(last(bare.out, 2)[3], /no slot named "selected"/);
});

// ── snap, bypass, repeat ────────────────────────────────────────────────── //

test("snap rounds the output's pitches: 0 semitones, 1 quarter tones, 3 free", () => {
  const m = load("bachmcp.runner.generator.js");
  m.send("load", tempFile(`const params = {};
function produce(p) { return { voices: [{ chords: [{ onset: 0, notes: [{ pitch: 6030, dur: 500, vel: 90 }, { pitch: 6080, dur: 500, vel: 90 }] }] }] }; }`));
  m.flush();
  const pitches = () => scoreOut(m).voices[0].chords[0].notes.map((n) => n.pitch);
  assert.deepEqual(pitches(), [6030, 6080]);
  m.send("snap", 0);
  m.flush();
  assert.deepEqual(pitches(), [6000, 6100]);
  assert.deepEqual(last(m.out, 1, "snap"), [1, "snap", 0]);
  m.send("snap", 1);
  m.flush();
  assert.deepEqual(pitches(), [6050, 6100]);
  m.send("snap", 2);
  assert.match(last(m.out, 2)[3], /snap is 0/);
});

test("bypass passes the input straight through; repeat sends the last score again", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  const outs = () => m.out.filter((o) => o[0] === 0);
  const before = outs().length;
  m.send("repeat");
  assert.equal(outs().length, before + 1);
  assert.deepEqual(scoreOut(m).voices[0].chords[0].notes.map((n) => n.pitch), [5600, 6500]);
  m.send("bypass", 1);
  assert.deepEqual(last(m.out, 1, "bypass"), [1, "bypass", 1]);
  m.send("dump");
  assert.equal(outs().length, before + 1, "no run while bypassed");
  inputScore(m, THREE);
  assert.deepEqual(last(m.out, 0), [0, "dictionary", `input_${inputCount}`], "the input as it came");
});

test("a selector's repeat sends the score and the commands again", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("load", tempFile(SELECTOR));
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  const n = m.out.length;
  m.send("repeat");
  assert.deepEqual(m.out.slice(n).map((o) => o[0] === 0 ? o[0] : o.slice(0, 2).join(" ")),
    [0, "1 clearselection", "1 sel"]);
});

test("a selector's snap rounds the pitches of its output score", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("load", tempFile(SELECTOR));
  m.send("snap", 0);
  m.send("dump");
  const odd = JSON.parse(JSON.stringify(THREE));
  odd.voices[0].chords[1].notes[0].pitch = 7230;
  inputScore(m, odd);
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes.map((n) => n.pitch)), [[6400], [7200]]);
});

test("a non-destructive selector (default) asks once, then selects again in the held source", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("load", tempFile(SELECTOR));
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  m.send("above", 7000);
  m.flush();
  const bach = m.out.filter((o) => o[0] === 1).map((o) => o.slice(1).join(" "));
  assert.deepEqual(bach, ["dump", "clearselection", "sel note [ 1 1 2 ] [ 1 2 1 ]", "clearselection", "sel note [ 1 2 1 ]"]);
  m.send("capture_source");
  assert.deepEqual(last(m.out, 1), [1, "dump"]);
  assert.deepEqual(last(m.out, 2, "source_mode"), null);
  m.send("source_mode", 0);
  assert.deepEqual(last(m.out, 2, "source_mode"), [2, "source_mode", 0]);
});

test("process_only_selection: a transformer changes only the notes flagged in selection_slot (default 11)", () => {
  const m = load("bachmcp.runner.transformer.js");
  m.send("load", tempFile(TRANSFORMER));
  m.send("process_only_selection", 1);
  const flagged = JSON.parse(JSON.stringify(THREE));
  flagged.voices[0].chords[0].notes[1].slots = { "11": [1] };
  inputScore(m, flagged);
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => [c.onset, c.notes.map((n) => n.pitch)]),
    [[0, [5500]], [0, [6500]], [500, [7200]]]);
  assert.deepEqual(last(m.out, 1, "process_only_selection"), [1, "process_only_selection", 1]);
});

test("process_only_selection: a selector picks only among the flagged notes, addressed in the whole score", () => {
  const m = load("bachmcp.runner.selector.js");
  m.send("load", tempFile(SELECTOR));
  m.send("process_only_selection", 1);
  m.send("dump");
  const flagged = JSON.parse(JSON.stringify(THREE));
  flagged.voices[0].chords[1].notes[0].slots = { "11": [1] };
  inputScore(m, flagged);
  m.flush();
  assert.deepEqual(m.out.filter((o) => o[0] === 1).slice(-1)[0].slice(1).join(" "), "sel note [ 1 2 1 ]",
    "6400 is above 6000 but not flagged: only 7200");
});
