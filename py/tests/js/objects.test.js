// The runner (v8: bachmcp.runner.js) as each type, run on a stand-in for Max.
// Outlets: 0 score, 1 bach.roll, 2 panel, 3 done bang, 4 status (dumpout).
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

/** The runner as one type: [v8 bachmcp.runner.js <type>]. */
function runner(type) {
  return load("bachmcp.runner.js", { args: [type] });
}

/** Every message out of an outlet, as [selector, ...atoms] (the status outlet: without the name). */
function from(m, index) {
  return m.out.filter((o) => o[0] === index).map((o) => o.slice(index === 4 ? 2 : 1));
}

function scoreOut(m) {
  const msg = last(m.out, 0, "dictionary");
  return msg ? readDict(msg[2]) : null;
}

test("load: spec to the panel, algo_loaded, and no run; bang: the score, then done", () => {
  const m = runner("generator");
  m.send("set_name", "algo");
  m.send("load", tempFile(ALGO));
  assert.deepEqual(from(m, 4), [["algo_loaded", "test_algo.js"]], "a load is not a run");
  assert.equal(scores(m), 0);
  assert.equal(from(m, 3).length, 0);
  m.send("bang");
  const spec = JSON.parse(last(m.out, 2, "spec")[2]);
  assert.equal(spec.title, "test_algo");
  assert.deepEqual(spec.params.map((p) => [p.name, p.type]), [["times", "slider"], ["register", "range"], ["mode", "menu"], ["seed", "seed"]]);
  assert.deepEqual(from(m, 4).map((o) => o.slice(0, 3)), [["algo_loaded", "test_algo.js"], ["algo_done", 4, last(m.out, 4)[4]]]);
  const score = scoreOut(m);
  assert.deepEqual(score.voices[0].chords.map((c) => c.notes[0].pitch), [6000, 6400, 6800, 7200]);
  assert.equal(last(m.out, 2, "status")[2], "ok");
  assert.deepEqual(m.out.slice(-2).map((o) => o.slice(0, 2)), [[0, "dictionary"], [3, "bang"]], "done comes after the score");
});

test("a parameter message updates the panel and runs again (debounced)", () => {
  const m = runner("generator");
  m.send("load", tempFile(ALGO));
  const before = m.out.length;
  m.send("param", "times", 2.6);
  m.send("param", "mode", "down");
  assert.deepEqual(last(m.out, 2, "set"), [2, "set", "mode", "down"]);
  assert.deepEqual(m.out.slice(before).filter((o) => o[1] === "set")[0], [2, "set", "times", 3]);
  assert.equal(m.out.slice(before).filter((o) => o[0] === 0).length, 0, "nothing runs before the task fires");
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes[0].pitch), [7200, 6600, 6000]);
  assert.deepEqual(last(m.out, 4).slice(0, 4), [4, "algo", "algo_done", 3]);
});

test("unknown parameters and bad values are reported, not fatal", () => {
  const m = runner("generator");
  m.send("param", "tempo", 3);
  assert.match(last(m.out, 4)[3], /no algorithm loaded/);
  m.send("load", tempFile(ALGO));
  m.send("param", "tempo", 3);
  assert.match(last(m.out, 4)[3], /"tempo" is not a parameter. Parameters: times, register, mode, seed/);
  m.send("param", "mode", "sideways");
  assert.match(last(m.out, 2, "status")[3], /cannot use/);
});

test("reloading keeps values of parameters that keep their name and type", () => {
  const file = tempFile(ALGO);
  const m = runner("generator");
  m.send("load", file);
  m.send("param", "times", 8);
  m.send("param", "register", 4800, 6000);
  m.flush();
  fs.writeFileSync(file, ALGO.replace('register: { type: "range"', 'register: { type: "slider"').replace(
    "value: [6000, 7200]", "value: 6000").replace("lerp(p.register[0], p.register[1],", "lerp(p.register, p.register + 1200,"));
  m.flush(true); // the watcher notices the change
  const spec = JSON.parse(last(m.out, 2, "spec")[2]);
  const values = Object.fromEntries(spec.params.map((p) => [p.name, p.value]));
  assert.equal(values.times, 8);
  assert.equal(values.register, 6000, "the type changed: back to the declared value");
  assert.equal(scoreOut(m).voices[0].chords.length, 8);
});

test("a broken file keeps the last good score and names the line", () => {
  const file = tempFile(ALGO);
  const m = runner("generator");
  m.send("load", file);
  m.send("bang");
  const good = last(m.out, 0, "dictionary");
  assert.ok(good);
  const dones = from(m, 3).length;
  fs.writeFileSync(file, ALGO.replace("const s = score();", "const s = score();\n  undefinedThing();"));
  m.send("reload");
  assert.deepEqual(last(m.out, 4).slice(2), ["algo_loaded", "test_algo.js"], "it compiles; a load runs nothing");
  m.send("bang");
  assert.match(last(m.out, 4)[3], /undefinedThing is not defined \(line 10\)/);
  assert.equal(last(m.out, 0, "dictionary"), good);
  assert.equal(from(m, 3).length, dones, "no done after a failed run");
});

test("a runner refuses an algorithm of the other kind", () => {
  const g = runner("generator");
  g.send("set_name", "scales1");
  g.send("load", tempFile(TRANSFORMER));
  assert.deepEqual(last(g.out, 4), [4, "scales1", "algo_error", "this is a generator: the file must define function produce(p) { ... }"]);
  const t = runner("transformer");
  t.send("load", tempFile(ALGO));
  assert.match(last(t.out, 4)[3], /this is a transformer: the file must define function transform\(source, p\)/);
  assert.equal(last(t.out, 2, "spec"), null, "nothing reaches the panel");
});

test("the setname message can carry a file to load", () => {
  const m = runner("generator");
  m.send("set_name", "algo", tempFile(ALGO));
  assert.deepEqual(last(m.out, 4), [4, "algo", "algo_loaded", "test_algo.js"]);
});

const TRANSFORMER = `const params = { shift: { type: "slider", range: [-1200, 1200], value: 100 } };
function transform(source, p) { const out = copy(source); eachNote(out, (n) => { n.pitch += p.shift; }); return out; }`;

function scorePitches(m) {
  return scoreOut(m).voices.map((v) => v.chords.map((c) => c.notes[0].pitch));
}

test("a score at the inlet is the source; a generator needs none; the spec says the type", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  assert.equal(last(m.out, 2, "source"), null, "the source's notes are not sent to the panel (for now)");
  const p = runner("generator");
  p.send("load", tempFile(ALGO));
  const spec = JSON.parse(last(p.out, 2, "spec")[2]);
  assert.deepEqual(Object.keys(spec), ["title", "description", "path", "type", "params"], "the algorithm's spec, nothing else");
  assert.equal(spec.type, "generator");
  assert.equal(p.named.length, 0);
});

// A score arriving at the inlet as a dictionary, as every object sends one.
let inputCount = 0;
function inputFrom(m, pitch) {
  const d = new Dict(`input_${++inputCount}`);
  d.parse(JSON.stringify({ voices: [{ chords: [{ onset: 0, notes: [{ pitch, dur: 1000, vel: 100 }] }] }] }));
  m.send("dictionary", d.name);
}

test("nondestructive: the first score at the inlet is held in memory; later ones are ignored until capture", () => {
  const file = tempFile(TRANSFORMER);
  const m = runner("transformer");
  m.send("load", file);
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  assert.ok(!fs.existsSync(file.replace(/\.js$/, ".source.json")), "nothing written to disk");
  inputFrom(m, 4800);
  m.flush();
  m.send("param", "shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]], "still the original");
  m.send("capture");
  assert.deepEqual(last(m.out, 1, "dump"), [1, "dump"], "asks the roll for its score");
  inputFrom(m, 4800);
  m.flush();
  assert.deepEqual(scorePitches(m), [[5000]], "capture: the next input is the new source");
});

test("write_to_playground writes the last score sent to the playground's scores folder", () => {
  const playground = fs.mkdtempSync(path.join(os.tmpdir(), "bachmcp-"));
  for (const dir of ["algorithms", "scores"]) fs.mkdirSync(path.join(playground, dir));
  const file = path.join(playground, "algorithms", "t1.js");
  fs.writeFileSync(file, TRANSFORMER);
  const m = runner("transformer");
  m.send("set_name", "t1");
  m.send("write_to_playground");
  assert.match(last(m.out, 4)[3], /no algorithm loaded/);
  m.send("load", file);
  m.send("write_to_playground");
  assert.match(last(m.out, 4)[3], /no score sent yet/);
  inputFrom(m, 3600);
  m.flush();
  m.send("write_to_playground");
  const written = path.join(playground, "scores", "t1.json");
  assert.deepEqual(JSON.parse(fs.readFileSync(written, "utf8")).voices[0].chords[0].notes.map((n) => n.pitch),
                   scorePitches(m)[0], "the result, not the source");
});

test("verbose 0 (default): only errors reach the Max console", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  assert.equal(m.posts.length, 0, "nothing said");
  m.send("load", "/nowhere/x.js");
  assert.ok(m.posts.some((t) => /error: cannot read/.test(t)), "errors are always said");
});

test("load_algo reports a file it cannot load; try_load_algo stays silent", () => {
  const m = runner("transformer");
  m.send("set_name", "t1");
  m.send("load_algo", "/nowhere/x.js");
  assert.deepEqual(last(m.out, 4).slice(1, 3), ["t1", "algo_error"]);
  assert.match(last(m.out, 4)[3], /^error: impossible to load \/nowhere\/x\.js/);
  m.send("load_algo", tempFile("const params = {}; function transform(source, p) { return ; "));
  assert.match(last(m.out, 4)[3], /^error: impossible to load test_algo\.js/);
  const before = m.out.length;
  m.send("try_load_algo", "/nowhere/x.js");
  m.send("try_load_algo", tempFile(ALGO));  // a generator: not for a transformer
  assert.equal(m.out.length, before, "silent");
  m.send("try_load_algo", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
});

test("a load without a source runs nothing; the first run asks the roll for a dump, and processes what comes in", () => {
  const m = runner("transformer");
  m.send("set_name", "t1");
  m.send("load", tempFile(TRANSFORMER));
  assert.equal(scoreOut(m), null);
  assert.equal(last(m.out, 1, "dump"), null, "no dump on load");
  assert.deepEqual(from(m, 4), [["algo_loaded", "test_algo.js"]], "loaded, nothing ran");
  m.send("dump");
  assert.deepEqual(last(m.out, 1, "dump"), [1, "dump"], "asks the roll for its score");
  assert.deepEqual(last(m.out, 4), [4, "t1", "processing", 1]);
  inputFrom(m, 6000);
  assert.deepEqual(scorePitches(m), [[6100]], "the answer is processed at once");
  assert.equal(last(m.out, 4, "t1")[2], "algo_done");
});

test("nondestructive: once the source is held, a change runs without a dump", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  const dumps = () => m.out.filter((o) => o[0] === 1 && o[1] === "dump").length;
  const before = dumps();
  m.send("param", "shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]]);
  assert.equal(dumps(), before, "no dump");
});

test("destructive: every run is change, dump, process; an unasked input is never transformed by itself", () => {
  const m = runner("transformer");
  m.send("set_name", "t1");
  m.send("source_mode", 0);
  assert.deepEqual(last(m.out, 2, "source_mode"), [2, "source_mode", 0]);
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
  m.send("param", "shift", 200);
  m.flush();
  assert.equal(dumps(), d + 1, "the change asks for a dump");
  assert.deepEqual(last(m.out, 4), [4, "t1", "processing", 1]);
  assert.equal(outs(), runs, "nothing goes out before the score comes in");
  m.send("param", "shift", 300);
  m.flush();
  assert.equal(dumps(), d + 1, "already asked: no second dump");
  inputFrom(m, 5000);  // the roll answers, edited by hand
  assert.ok(m.out.some((o) => o[0] === 4 && o[2] === "processing" && o[3] === 0));
  assert.deepEqual(scorePitches(m), [[5300]], "processed with the latest value");
  m.send("dump");
  assert.equal(dumps(), d + 2, "dump asks too");
  m.wait(2999);
  assert.equal(m.out.some((o) => o[2] === "timeout"), false, "still waiting");
  m.wait(3000);
  assert.deepEqual(m.out.slice(-2), [[4, "t1", "timeout", 1], [4, "t1", "processing", 0]], "nothing came in");
  m.send("param", "shift", 100);
  m.flush();
  assert.equal(dumps(), d + 3, "the next change asks again");
  m.send("source_mode", 2);
  assert.match(last(m.out, 4)[3], /source_mode is 0 \(destructive\) or 1/);
});

test("auto_dump 0: a parameter change outputs nothing until dump", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  m.send("auto_dump", 0);
  inputFrom(m, 3600);
  m.flush();
  const outs = () => m.out.filter((o) => o[0] === 0).length;
  const runs = outs();
  m.send("param", "shift", 500);
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
  m.send("dictionary", d.name);
}

const THREE = { voices: [{ chords: [
  { onset: 0, notes: [{ pitch: 5500, dur: 500, vel: 90 }, { pitch: 6400, dur: 500, vel: 90 }] },
  { onset: 500, notes: [{ pitch: 7200, dur: 500, vel: 90 }] },
] }] };

test("a selector outputs the selected notes flagged 16, then clearselection and sel note", () => {
  const m = runner("selector");
  m.send("set_name", "s1");
  m.send("load", tempFile(SELECTOR));
  assert.equal(last(m.out, 1), null, "no dump on load");
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  const bach = m.out.filter((o) => o[0] === 1).map((o) => o.slice(1).join(" "));
  assert.deepEqual(bach, ["dump", "clearselection", "sel note [ 1 1 2 ] [ 1 2 1 ]"], "dump asks for the score, then selects in it");
  const only = scoreOut(m);
  assert.equal(only.header, undefined, "no slot declared");
  assert.deepEqual(only.voices[0].chords.map((c) => [c.flag, c.notes.map((n) => [n.pitch, n.flag])]), [[0, [[6400, 16]]], [0, [[7200, 16]]]]);
  assert.ok(m.out.findIndex((o) => o[0] === 0) < m.out.findIndex((o) => o[0] === 1 && o[1] === "clearselection"), "the score before the commands");
  assert.match(last(m.out, 2, "status")[3], /2 notes selected/);
  assert.deepEqual(last(m.out, 4).slice(0, 4), [4, "s1", "algo_done", 2]);
  m.send("dump_selection_only", 0);
  assert.deepEqual(last(m.out, 2, "dump_selection_only"), [2, "dump_selection_only", 0]);
  m.send("capture");
  const marked = JSON.parse(JSON.stringify(THREE));
  marked.voices[0].chords[0].flag = 16;            // a chord selected in the roll: cleared, written on notes
  marked.voices[0].chords[0].notes[1].flag = 2;    // muted: kept
  inputScore(m, marked);
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => [c.flag, c.notes.map((n) => n.flag)]), [[0, [0, 18]], [0, [16]]],
    "the whole source, flagged on notes only, other bits kept");
  m.send("clear_selection");
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => [c.flag, c.notes.map((n) => n.flag)]), [[0, [0, 2]], [0, [0]]]);
  assert.deepEqual(last(m.out, 1), [1, "clearselection"]);
});

test("selections are not cumulative: each run clears the previous one (involutive ignored)", () => {
  const m = runner("selector");
  m.send("load", tempFile(SELECTOR));
  m.send("involutive", 1);
  m.send("source_mode", 0);
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  m.send("param", "above", 7000);
  m.flush();
  assert.deepEqual(last(m.out, 1), [1, "dump"], "a change asks the roll for its score");
  inputScore(m, THREE);
  assert.deepEqual(m.out.filter((o) => o[0] === 1).slice(-2).map((o) => o.slice(1).join(" ")),
    ["clearselection", "sel note [ 1 2 1 ]"]);
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes.map((n) => n.pitch)), [[7200]]);
});

test("a selector refuses a result that is not notes of the source", () => {
  const m = runner("selector");
  m.send("load", tempFile(`const params = {};
function select(source, p) { return [[1, 9, 1]]; }`));
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  assert.match(last(m.out, 4)[3], /not a note of the source/);
});

test("a destructive selector: an unasked input becomes the source but is not selected in; no answer times out", () => {
  const m = runner("selector");
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
  assert.deepEqual(last(m.out, 4), [4, "s1", "processing", 1]);
  m.wait(3000);
  assert.deepEqual(m.out.slice(-2), [[4, "s1", "timeout", 1], [4, "s1", "processing", 0]]);
});

test("input_mode 1: a transformer changes only the selected notes; a note inherits its chord's flag 16", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  m.send("input_mode", 1);
  m.send("selection_slot", 11);  // ignored, old patches send it
  const flagged = JSON.parse(JSON.stringify(THREE));
  flagged.voices[0].chords[1].flag = 16;
  flagged.voices[0].chords[1].notes[0].flag = 0;
  inputScore(m, flagged);
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => [c.onset, c.notes.map((n) => n.pitch)]),
    [[0, [5500, 6400]], [500, [7300]]]);
  const bare = runner("transformer");
  bare.send("load", tempFile(TRANSFORMER));
  bare.send("input_mode", 1);
  inputScore(bare, THREE);
  bare.flush();
  assert.deepEqual(scoreOut(bare).voices[0].chords.map((c) => c.notes.map((n) => n.pitch)), [[5500, 6400], [7200]],
    "nothing selected: nothing changes");
});

// ── snap, bypass, repeat ────────────────────────────────────────────────── //

test("snap rounds the output's pitches: 0 semitones, 1 quarter tones, 3 free", () => {
  const m = runner("generator");
  m.send("load", tempFile(`const params = {};
function produce(p) { return { voices: [{ chords: [{ onset: 0, notes: [{ pitch: 6030, dur: 500, vel: 90 }, { pitch: 6080, dur: 500, vel: 90 }] }] }] }; }`));
  m.send("bang");
  const pitches = () => scoreOut(m).voices[0].chords[0].notes.map((n) => n.pitch);
  assert.deepEqual(pitches(), [6030, 6080]);
  m.send("snap", 0);
  m.flush();
  assert.deepEqual(pitches(), [6000, 6100]);
  assert.deepEqual(last(m.out, 2, "snap"), [2, "snap", 0]);
  m.send("snap", 1);
  m.flush();
  assert.deepEqual(pitches(), [6050, 6100]);
  m.send("snap", 2);
  assert.match(last(m.out, 4)[3], /snap is 0/);
});

test("bypass passes the input straight through; repeat sends the last score again", () => {
  const m = runner("transformer");
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
  assert.deepEqual(last(m.out, 2, "bypass"), [2, "bypass", 1]);
  m.send("dump");
  assert.equal(outs().length, before + 1, "no run while bypassed");
  inputScore(m, THREE);
  assert.deepEqual(last(m.out, 0), [0, "dictionary", `input_${inputCount}`], "the input as it came");
});

test("a selector's repeat sends the score and the commands again", () => {
  const m = runner("selector");
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
  const m = runner("selector");
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
  const m = runner("selector");
  m.send("load", tempFile(SELECTOR));
  m.send("dump");
  inputScore(m, THREE);
  m.flush();
  m.send("param", "above", 7000);
  m.flush();
  const bach = m.out.filter((o) => o[0] === 1).map((o) => o.slice(1).join(" "));
  assert.deepEqual(bach, ["dump", "clearselection", "sel note [ 1 1 2 ] [ 1 2 1 ]", "clearselection", "sel note [ 1 2 1 ]"]);
  m.send("capture");
  assert.deepEqual(last(m.out, 1), [1, "dump"]);
  assert.deepEqual(last(m.out, 2, "source_mode"), null);
  m.send("source_mode", 0);
  assert.deepEqual(last(m.out, 2, "source_mode"), [2, "source_mode", 0]);
});

test("process_only_selection: a transformer changes only the notes flagged 16", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  m.send("process_only_selection", 1);
  const flagged = JSON.parse(JSON.stringify(THREE));
  flagged.voices[0].chords[0].notes[1].flag = 18;  // muted and selected
  inputScore(m, flagged);
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => [c.onset, c.notes.map((n) => n.pitch)]),
    [[0, [5500]], [0, [6500]], [500, [7200]]]);
  assert.deepEqual(last(m.out, 2, "process_only_selection"), [2, "process_only_selection", 1]);
});

test("process_only_selection: a selector picks only among the flagged notes, addressed in the whole score", () => {
  const m = runner("selector");
  m.send("load", tempFile(SELECTOR));
  m.send("process_only_selection", 1);
  m.send("dump");
  const flagged = JSON.parse(JSON.stringify(THREE));
  flagged.voices[0].chords[1].notes[0].flag = 16;
  inputScore(m, flagged);
  m.flush();
  assert.deepEqual(m.out.filter((o) => o[0] === 1).slice(-1)[0].slice(1).join(" "), "sel note [ 1 2 1 ]",
    "6400 is above 6000 but not flagged: only 7200");
});

test("the comment that opens the file reaches the panel in the spec", () => {
  const m = runner("generator");
  m.send("load", tempFile("// Notes that climb\n" + ALGO.replace(/^\/\/.*\n/, "")));
  assert.equal(JSON.parse(last(m.out, 2, "spec")[2]).description, "Notes that climb");
  const plain = runner("generator");
  plain.send("load", tempFile(ALGO.replace(/^\/\/.*\n/, "")));
  assert.equal(JSON.parse(last(plain.out, 2, "spec")[2]).description, "");
});

// ── bang, auto_dump, the type ───────────────────────────────────────────── //

const runs = (m) => m.out.filter((o) => o[0] === 4 && o[2] === "algo_done").length;
const scores = (m) => m.out.filter((o) => o[0] === 0).length;

test("bang: the same score again when nothing changed, a new run when something did", () => {
  const m = runner("generator");
  m.send("load", tempFile(ALGO));
  assert.equal(runs(m), 0, "a load is not a run");
  m.send("bang");
  assert.equal(runs(m), 1);
  m.send("bang");
  assert.equal(runs(m), 1, "nothing changed: no run");
  assert.equal(scores(m), 2, "but the score goes out again");
  assert.equal(from(m, 3).length, 2, "done after each bang, run or not");
  assert.deepEqual(m.out.slice(-2).map((o) => o[0]), [0, 3]);
  m.send("repeat");
  assert.equal(from(m, 3).length, 2, "repeat is not a process: no done");
  m.send("param", "times", 2);
  m.flush();
  assert.equal(runs(m), 2, "auto_dump 1: a change runs");
  m.send("bang");
  assert.equal(runs(m), 2);
  m.send("run");
  assert.equal(runs(m), 3, "run always runs");
  assert.equal(from(m, 3).length, 5);
});

test("auto_dump 0: a change outputs nothing; bang runs with the latest settings", () => {
  const m = runner("generator");
  m.send("auto_dump", 0);
  assert.deepEqual(last(m.out, 2, "auto_dump"), [2, "auto_dump", 0], "echoed to the panel");
  m.send("load", tempFile(ALGO));
  assert.equal(scores(m), 0);
  m.send("param", "times", 2);
  m.flush();
  assert.equal(scores(m), 0);
  m.send("bang");
  assert.equal(scoreOut(m).voices[0].chords.length, 2);
  m.send("bang");
  assert.equal(runs(m), 1, "unchanged since: no second run");
  m.send("auto_dump", 2);
  assert.deepEqual(last(m.out, 4).slice(2, 3), ["error"]);
});

test("a transformer holding a source does not run on a new file; a destructive one always asks on bang", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, 3600);
  m.flush();
  const n = scores(m);
  m.send("load", tempFile(TRANSFORMER.replace("value: 100", "value: 200")));
  assert.equal(scores(m), n, "a load is not a run");
  m.send("bang");
  assert.deepEqual(scorePitches(m), [[3800]], "the held source, with the new file");
  m.send("source_mode", 0);
  const dumps = () => m.out.filter((o) => o[0] === 1 && o[1] === "dump").length;
  const d = dumps();
  m.send("bang");
  assert.equal(dumps(), d + 1, "the roll may have changed: asks again");
});

test("type: the runner becomes another type; a file of the old type is refused", () => {
  const m = runner("generator");
  m.send("set_name", "a1");
  m.send("load", tempFile(ALGO));
  m.send("type", "transformer");
  assert.deepEqual(last(m.out, 2, "type"), [2, "type", "transformer"]);
  assert.match(last(m.out, 4, "a1")[3], /this is a transformer: the file must define function transform/);
  m.send("bang");
  assert.equal(last(m.out, 1, "dump"), null, "nothing loaded for it: no run");
  m.send("type", "selector");
  m.send("load", tempFile(SELECTOR));
  m.send("bang");
  inputScore(m, THREE);
  assert.deepEqual(from(m, 1).slice(-2).map((o) => o.join(" ")), ["clearselection", "sel note [ 1 1 2 ] [ 1 2 1 ]"]);
  m.send("type", "sorter");
  assert.match(last(m.out, 4)[3], /type is generator, transformer or selector/);
});

test("a message the type does not take is refused with error; a runner without a type loads nothing", () => {
  const g = runner("generator");
  g.send("set_name", "g1");
  g.send("capture");
  assert.deepEqual(last(g.out, 4), [4, "g1", "error", "capture: a generator does not take it"]);
  g.send("dump_selection");
  assert.match(last(g.out, 4)[3], /a generator does not take it/);
  const t = runner("transformer");
  t.send("clear_selection");
  assert.match(last(t.out, 4)[3], /clear_selection: a transformer does not take it/);
  const none = load("bachmcp.runner.js");
  none.send("load", tempFile(ALGO));
  assert.match(last(none.out, 4)[3], /no type/);
  const at = load("bachmcp.runner.js", { args: ["@type", "selector"] });
  at.send("load", tempFile(SELECTOR));
  assert.equal(JSON.parse(last(at.out, 2, "spec")[2]).type, "selector");
});

test("every outlet carries only its own messages", () => {
  const m = runner("selector");
  m.send("load", tempFile(SELECTOR));
  m.send("bang");
  inputScore(m, THREE);
  m.send("param", "above", 7000);
  m.flush();
  m.send("bang");
  assert.deepEqual([...new Set(from(m, 0).map((o) => o[0]))], ["dictionary"]);
  assert.ok(from(m, 1).every((o) => ["dump", "clearselection", "sel"].includes(o[0])));
  assert.ok(from(m, 2).every((o) => ["spec", "set", "status", "source"].includes(o[0])));
  assert.deepEqual([...new Set(from(m, 3).map((o) => o[0]))], ["bang"]);
  assert.ok(from(m, 4).every((o) => ["algo_loaded", "algo_done", "processing"].includes(o[0])));
});

test("a selector's done bang comes after its score and its commands to bach", () => {
  const m = runner("selector");
  m.send("load", tempFile(SELECTOR));
  m.send("bang");
  inputScore(m, THREE);
  assert.deepEqual(m.out.slice(-4).map((o) => o.slice(0, 2).join(" ")), ["0 dictionary", "1 clearselection", "1 sel", "3 bang"]);
});

test("dictionary <name> is a score in; input dictionary <name> is its old form; input clear forgets the source", () => {
  const m = runner("transformer");
  m.send("load", tempFile(TRANSFORMER));
  const d = new Dict("old_form_in");
  d.parse(JSON.stringify({ voices: [{ chords: [{ onset: 0, notes: [{ pitch: 3600, dur: 1000, vel: 100 }] }] }] }));
  m.send("input", "dictionary", d.name);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  m.send("input", "clear");
  m.send("bang");
  assert.deepEqual(last(m.out, 1), [1, "dump"], "no source any more: a run asks the roll");
  m.send("input", "list");
  assert.match(last(m.out, 4)[3], /input takes clear/);
  const g = runner("generator");
  g.send("bypass", 1);
  g.send("dictionary", d.name);
  assert.deepEqual(last(g.out, 0), [0, "dictionary", "old_form_in"], "a bypassed generator passes it through");
});

test("parameters come in only with param: any name is free, a bare message is refused", () => {
  const m = runner("generator");
  m.send("set_name", "g1");
  m.send("load", tempFile(`const params = {
  type: { type: "slider", range: [0, 10], value: 1 },
  load: { type: "slider", range: [0, 10], value: 1 },
  pitch: { type: "slider", range: [3600, 8400], value: 6000, unit: "mc" },
};
function produce(p) { const s = score(); s.voice("Flute").note(0, p.pitch + p.type + p.load, 100); return s; }`));
  assert.equal(last(m.out, 4)[2], "algo_loaded", "type and load are parameter names like any other");
  m.send("param", "pitch", 7200);
  m.send("param", "type", 3);
  m.send("param", "load", 4);
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords[0].notes.map((n) => n.pitch), [7207]);
  assert.ok(!m.out.some((o) => o[0] === 2 && (o[1] === "type" || o[1] === "clear")), "param type 3 set the parameter, not the runner's type");
  assert.deepEqual(m.out.filter((o) => o[0] === 4 && o[2] === "error"), [], "nothing refused");
  const n = m.out.length;
  m.send("pitch", 6000);
  assert.deepEqual(m.out.slice(n), [[2, "status", "error", "pitch: not a message of the runner (a parameter is set with param pitch <value...>)"],
    [4, "g1", "error", "pitch: not a message of the runner (a parameter is set with param pitch <value...>)"]]);
  m.send("param");
  assert.match(last(m.out, 4)[3], /param needs a name/);
});

test("settings: every runner takes them, before its type too, and keeps them across a type change", () => {
  const m = load("bachmcp.runner.js");  // no type yet: patcherargs sends its attributes first
  m.send("set_name", "a1");
  for (const s of [["source_mode", 0], ["process_only_selection", 1], ["input_mode", 0], ["dump_selection_only", 0],
    ["involutive", 1], ["selection_slot", 11], ["auto_dump", 1]]) m.send(...s);
  assert.deepEqual(m.out.filter((o) => o[0] === 4), [], "nothing refused");
  m.send("type", "generator");
  m.send("source_mode", 1);
  m.send("source_mode", 0);
  assert.deepEqual(m.out.filter((o) => o[0] === 4), [], "a generator keeps them unused");
  m.send("capture");
  assert.match(last(m.out, 4)[3], /capture: a generator does not take it/, "actions stay the type's");
  m.send("type", "selector");
  m.send("load", tempFile(SELECTOR));
  m.send("bang");
  inputScore(m, THREE);
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes.map((n) => n.flag)), [[0, 16], [16]],
    "dump_selection_only 0, sent before the type: the whole source, flagged");
  const dumps = m.out.filter((o) => o[0] === 1 && o[1] === "dump").length;
  m.send("bang");
  assert.equal(m.out.filter((o) => o[0] === 1 && o[1] === "dump").length, dumps + 1, "source_mode 0, sent before the type: destructive");
  m.send("source_mode", 2);
  assert.match(last(m.out, 4)[3], /source_mode is 0 \(destructive\) or 1/);
});
