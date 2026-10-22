// The core library and loader of bach.mcp.algo. Run: node --test py/tests/js
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { JS_DIR } = require("./maxmock.js");

const core = require(path.join(JS_DIR, "bach.mcp.core.js"));

const SPIRAL = `
// A cell repeats; each pass starts one note later in the cell and rises by step.
const params = {
  cell:   { type: "list", range: [3600, 9600], value: [6200, 6500, 6900] },
  passes: { type: "slider", range: [1, 24], value: 3 },
  step:   { type: "slider", range: [-1200, 1200], value: 200, unit: "mc" },
  ioi:    { type: "slider", range: [40, 2000], value: 250, unit: "ms" },
  drift:  { type: "slider", range: [0, 100], value: 0 },
  seed:   { type: "seed", value: 1 },
};
function generate(p, input) {
  const s = score();
  const v = s.voice("Clarinet");
  const r = rng("drift");
  let n = 0;
  for (let pass = 0; pass < p.passes; pass++)
    for (let i = 0; i < p.cell.length; i++) {
      const pitch = p.cell[(i + pass) % p.cell.length] + pass * p.step + r.float(-p.drift, p.drift);
      v.note(n++ * p.ioi, pitch, p.ioi);
    }
  v.chords[0].dyn = "p<";
  return s;
}`;

function pitches(result) {
  return result.score.voices[0].chords.map((c) => c.notes[0].pitch);
}

test("the worked example of the skill, as an algorithm", () => {
  const c = core.compile(SPIRAL);
  const r = core.run(c, core.defaults(c.specs));
  assert.deepEqual(pitches(r), [6200, 6500, 6900, 6700, 7100, 6400, 7300, 6600, 6900]);
  assert.equal(r.notes, 9);
  assert.equal(r.canonical.voices[0].clef, "G");
});

test("the same values give the same score; the seed changes it", () => {
  const c = core.compile(SPIRAL);
  const values = Object.assign(core.defaults(c.specs), { drift: 80 });
  const a = core.run(c, values), b = core.run(c, values);
  assert.deepEqual(a.score, b.score);
  assert.notDeepEqual(core.run(c, Object.assign({}, values, { seed: 2 })).score, a.score);
});

test("random streams are independent: more passes do not reshuffle the first ones", () => {
  const code = `const params = { n: { type: "slider", range: [1, 50], value: 5 }, seed: { type: "seed", value: 7 } };
    function generate(p) { const s = score(); const v = s.voice("A"); const r = rng("pitch");
      for (let i = 0; i < p.n; i++) v.note(i * 100, 6000 + r.int(0, 1200), 100); return s; }`;
  const c = core.compile(code);
  const five = pitches(core.run(c, { n: 5, seed: 7 }));
  const nine = pitches(core.run(c, { n: 9, seed: 7 }));
  assert.deepEqual(nine.slice(0, 5), five);
});

test("Math.random is seeded too", () => {
  const code = `const params = { seed: { type: "seed", value: 3 } };
    function generate() { const s = score(); s.voice("A").note(0, 6000 + Math.floor(Math.random() * 1000), 100); return s; }`;
  const c = core.compile(code);
  assert.deepEqual(core.run(c, { seed: 3 }).score, core.run(c, { seed: 3 }).score);
});

test("parameter declarations are completed and checked", () => {
  const specs = core.normalizeParams({
    times: { type: "slider", range: [1, 64], value: 16 },
    amount: { type: "slider", range: [0, 1], value: 0.5 },
    register: { type: "range", range: [3600, 9600] },
    legato: { type: "toggle", value: 1 },
    mode: { type: "menu", options: ["up", "down"] },
    seed: { type: "seed" },
    shape: { type: "curve" },
    durs: { type: "list", range: [50, 2000], value: [250, 251.5] },
    knob: { type: "knob", min: 0, max: 10, default: 3 },
    labelled: { type: "slider", range: [0, 10], value: 2, label: "ignored" },
  });
  const by = Object.fromEntries(specs.map((s) => [s.name, s]));
  assert.equal(by.times.step, 1);
  assert.equal(by.amount.step, 0);
  assert.deepEqual(by.register.value, [3600, 9600]);
  assert.equal(by.legato.value, true);
  assert.equal(by.mode.value, "up");
  assert.equal(by.seed.value, 1);
  assert.deepEqual(by.shape.value, [[0, 0], [1, 1]]);
  assert.deepEqual(by.durs.value, [250, 251.5]); // a decimal makes the list continuous
  assert.equal(by.knob.type, "slider");
  assert.equal(by.knob.value, 3);
});

test("bad declarations are refused with a message the model can act on", () => {
  const bad = [
    [{ times: { type: "slider" } }, /"range" must be \[low, high\]/],
    [{ times: { type: "dial", range: [5, 1] } }, /low < high/],
    [{ "two words": { type: "toggle" } }, /not a usable name/],
    [{ load: { type: "toggle" } }, /Max uses for its own messages; rename/],
    [{ mode: { type: "menu" } }, /needs "options"/],
    [{ mode: { type: "menu", options: ["a"], value: "b" } }, /not one of the options/],
    [{ durs: { type: "list", range: [0, 1] } }, /a list needs "value"/],
    [{ x: { type: "wheel", range: [0, 1] } }, /unknown type/],
    [{ x: { type: "slider", range: [0, 1], colour: "red" } }, /unknown key "colour"/],
  ];
  for (const [params, message] of bad) assert.throws(() => core.normalizeParams(params), message);
  assert.throws(() => core.compile("function generate() {}"), /const params = \{ \.\.\. \} is missing/);
  assert.throws(() => core.compile("const params = {};"), /produce\(p\).*transform\(source, p\).*is missing/);
});

test("values from Max are clamped, snapped and typed", () => {
  const specs = core.normalizeParams({
    times: { type: "slider", range: [1, 64], value: 16 },
    register: { type: "range", range: [3600, 9600] },
    legato: { type: "toggle" },
    mode: { type: "menu", options: ["up", "down", 3] },
    shape: { type: "curve", range: [0, 10] },
    durs: { type: "list", range: [50, 2000], value: [250] },
  });
  const [times, register, legato, mode, shape, durs] = specs;
  assert.equal(core.coerce(times, [33.7]), 34);
  assert.equal(core.coerce(times, ["900"]), 64);
  assert.deepEqual(core.coerce(register, [9000, 4000]), [4000, 9000]);
  assert.equal(core.coerce(legato, [0]), false);
  assert.equal(core.coerce(legato, ["on"]), true);
  assert.equal(core.coerce(mode, ["down"]), "down");
  assert.equal(core.coerce(mode, [1]), "down");
  assert.equal(core.coerce(mode, ["3"]), 3);
  assert.deepEqual(core.coerce(shape, [0.1, 2, 0.5, 20, 0.9, 5]), [[0, 2], [0.5, 10], [1, 5]]);
  assert.deepEqual(core.coerce(durs, [10, 300, 5000]), [50, 300, 2000]);
  assert.throws(() => core.coerce(times, ["many"]), /cannot use/);
  assert.deepEqual(core.valueAtoms(shape, [[0, 1], [1, 2]]), [0, 1, 1, 2]);
  assert.deepEqual(core.valueAtoms(legato, true), [1]);
});

test("a curve parameter arrives as a function of 0..1", () => {
  const code = `const params = { shape: { type: "curve", range: [0, 100], value: [[0, 0], [0.5, 100], [1, 0]] } };
    function generate(p) { const s = score(); s.voice("A").note(0, 6000 + p.shape(0.25), 100); return s; }`;
  const c = core.compile(code);
  assert.equal(core.run(c, core.defaults(c.specs)).score.voices[0].chords[0].notes[0].pitch, 6050);
});

test("errors name the line of the file", () => {
  const code = 'const params = {};\nfunction generate(p) {\n  const x = 1;\n  return missing.value;\n}';
  const c = core.compile(code);
  assert.throws(() => core.run(c, {}), (e) => e.line === 4 && /missing is not defined/.test(e.message));
  assert.throws(() => core.compile("const params = {;"), /syntax error/);
  assert.throws(() => core.run(core.compile("const params = {}; function generate() {}"), {}), /returned nothing/);
  assert.throws(
    () => core.run(core.compile("const params = {}; function generate() { const s = score(); s.voice('A').note(0, NaN, 1); return s; }"), {}),
    /not valid: voice 1, chord 1, note 1: invalid pitch NaN/);
  assert.throws(
    () => core.run(core.compile("const params = {}; function generate() { const s = score(); s.voice('A').note(0, 60, 1); return s; }"), {}),
    /looks like a MIDI note number/);
});

test("names in the file can shadow the library", () => {
  const code = `const params = {};
    const lerp = (a, b) => a + b;
    function clamp() { return 1; }
    function generate() { const s = score(); s.voice("A").note(0, lerp(6000, clamp()), 100); return s; }`;
  assert.equal(core.run(core.compile(code), {}).score.voices[0].chords[0].notes[0].pitch, 6001);
});

test("the score builder writes the JSON score", () => {
  const s = core.score();
  const v = s.voice("Piano");
  v.chord(0, [4800, 6400], 1000, { dyn: "p", art: "tenuto", vel: 40, head: "diamond" });
  v.note(1000, 6700, 500).text = "dolce";
  s.voice("Piano").note(2000, { pitch: 6000, dur: 250, gliss: 200 }, 999);
  s.marker(0, "A");
  assert.deepEqual(JSON.parse(JSON.stringify(s)), {
    voices: [{ name: "Piano", chords: [
      { onset: 0, dyn: "p", art: "tenuto", notes: [
        { pitch: 4800, dur: 1000, vel: 40, head: "diamond" }, { pitch: 6400, dur: 1000, vel: 40, head: "diamond" }] },
      { onset: 1000, notes: [{ pitch: 6700, dur: 500 }], text: "dolce" },
      { onset: 2000, notes: [{ dur: 250, pitch: 6000, gliss: 200 }] },
    ] }],
    markers: [{ onset: 0, name: "A" }],
  });
  assert.equal(v.end, 2250);
  assert.equal(s.end, 2250);
});

test("procedures", () => {
  assert.deepEqual(core.euclid(3, 8), [1, 0, 0, 1, 0, 0, 1, 0]);
  assert.deepEqual(core.euclid(3, 8, 1), [0, 0, 1, 0, 0, 1, 0, 1]);
  assert.equal(core.rewrite("A", { A: "AB", B: "A" }, 4), "ABAABABA");
  assert.deepEqual(core.automaton(90, 7, 3).map((r) => r.join("")), ["0001000", "0010100", "0100010"]);
  assert.deepEqual(core.iterate(4, 1, (x) => x * 2), [1, 2, 4, 8]);
  assert.deepEqual(core.accumulate([100, 200, 50], 1000), [1000, 1100, 1300]);
  assert.deepEqual(core.linspace(0, 1, 5), [0, 0.25, 0.5, 0.75, 1]);
  assert.deepEqual(core.seq(3, 10, 5), [10, 15, 20]);
  assert.equal(core.fold(13, 0, 10), 7);
  assert.equal(core.wrap(13, 0, 10), 3);
  assert.equal(core.snap(6037, 50), 6050);
  assert.equal(core.rescale(5, 0, 10, 100, 200), 150);
  assert.equal(core.env([[0, 0], [1, 10]])(0.3), 3);
  assert.equal(core.warp(0.5, 0), 0.5);
  assert.ok(core.warp(0.5, 3) < 0.5);
  const r = core.makeRandom(1);
  const w = core.walk({ n: 200, start: 6000, step: 300, min: 5500, max: 6500, rng: r });
  assert.equal(w.length, 200);
  assert.ok(w.every((x) => x >= 5500 && x <= 6500));
  const chain = core.markov({ a: { b: 1 }, b: ["a"] }, { n: 5, start: "a" });
  assert.deepEqual(chain, ["a", "b", "a", "b", "a"]);
  assert.deepEqual(core.markov({ 6000: { 6200: 1 }, 6200: [] }, { n: 5, start: 6000 }), [6000, 6200]);
  assert.throws(() => core.rewrite("A", { A: "AA" }, 40), /grew past/);
  const g = core.makeRandom("x");
  for (let i = 0; i < 100; i++) {
    const k = g.int(3, 5);
    assert.ok(k >= 3 && k <= 5 && Number.isInteger(k));
  }
  assert.deepEqual(g.shuffle([1, 2, 3, 4]).sort(), [1, 2, 3, 4]);
  assert.equal(g.weighted(["a", "b"], [0, 1]), "b");
});

test("producers and transformers", () => {
  const producer = core.compile(`const params = {};
    function produce(p) { const s = score(); s.voice("A").note(0, 6000, 100); return s; }`);
  assert.equal(producer.kind, "producer");
  assert.equal(core.run(producer, {}).notes, 1);
  const legacy = core.compile(`const params = {};
    function generate(p, input) { const s = score(); s.voice("A").note(0, input ? 7000 : 6000, 100); return s; }`);
  assert.equal(legacy.kind, "producer");
  assert.equal(core.run(legacy, {}, { voices: [] }).score.voices[0].chords[0].notes[0].pitch, 7000);
  assert.throws(() => core.compile("const params = {}; function produce(p) {} function transform(s, p) {}"), /not both/);
});

test("a transformer always starts again from the original source", () => {
  const t = core.compile(`const params = { shift: { type: "slider", range: [-1200, 1200], value: 100 } };
    function transform(source, p) { eachNote(source, (n) => { n.pitch += p.shift; }); return source; }`);
  assert.equal(t.kind, "transformer");
  const source = { voices: [{ chords: [{ onset: 0, notes: [{ pitch: 6000, dur: 100 }] }] }] };
  const pitch = (r) => r.score.voices[0].chords[0].notes[0].pitch;
  assert.equal(pitch(core.run(t, { shift: 100 }, source)), 6100);
  assert.equal(pitch(core.run(t, { shift: 300 }, source)), 6300, "from the original, not from 6100");
  assert.equal(source.voices[0].chords[0].notes[0].pitch, 6000, "the source itself is untouched");
  assert.throws(() => core.run(t, { shift: 1 }, null), /no source score yet/);
  assert.throws(() => core.run(core.compile("const params = {}; function transform(s, p) { return null; }"), {}, source),
    /transform\(\) returned nothing/);
});

test("score helpers for transformers", () => {
  const chords = [
    { onset: 0, notes: [{ pitch: 6000, dur: 1000 }, { pitch: 6400, dur: 200 }] },
    { onset: 1200, notes: [{ pitch: 6200, dur: 100 }] },   // 200 ms after the long note ends
    { onset: 1800, notes: [{ pitch: 6500, dur: 100 }] },   // 500 ms of silence before it
    { onset: 600, notes: [{ pitch: 6700, dur: 100 }] },    // out of order, inside the first note
  ];
  assert.equal(core.chordEnd(chords[0]), 1000);
  assert.deepEqual(core.phrases(chords, 300).map((g) => g.map((c) => c.onset)), [[0, 600, 1200], [1800]]);
  assert.deepEqual(core.phrases(chords, 150).map((g) => g.length), [2, 1, 1]);
  const s = { voices: [{ chords }] };
  const copied = core.copy(s);
  core.eachNote(copied, (n) => { n.pitch += 1; });
  assert.equal(copied.voices[0].chords[0].notes[1].pitch, 6401);
  assert.equal(s.voices[0].chords[0].notes[1].pitch, 6400);
});

test("number parameters know what they are: pitch, interval, time or plain, each with its snap grid", () => {
  const specs = core.normalizeParams({
    target:   { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" },
    register: { type: "range", range: [3600, 9600], value: [4800, 8400], unit: "midicents" },
    step:     { type: "slider", range: [-1200, 1200], value: 400, unit: "mc" },
    width:    { type: "slider", range: [0, 1200], value: 700, unit: "cents" },
    gap:      { type: "slider", range: [50, 2000], value: 300, unit: "ms" },
    amount:   { type: "slider", range: [0, 1], value: 0.5 },
    times:    { type: "slider", range: [1, 64], value: 16 },
    quarter:  { type: "slider", range: [4800, 7200], value: 6050, step: 50, unit: "mc" },
  });
  const by = Object.fromEntries(specs.map((s) => [s.name, s]));
  assert.deepEqual(specs.map((s) => [s.name, s.kind, s.grid]), [
    ["target", "pitch", 100], ["register", "pitch", 100], ["step", "interval", 100], ["width", "interval", 100],
    ["gap", "time", 20], ["amount", "", 0.01], ["times", "", 1], ["quarter", "pitch", 50],
  ]);
  assert.deepEqual(by.target.range, [1200, 12700], "a pitch spans all a score takes, C0 to G9");
  assert.deepEqual(by.register.range, [1200, 12700]);
  assert.deepEqual(by.register.value, [4800, 8400], "the declared value is kept");
  assert.equal(by.register.unit, "mc");
  assert.deepEqual(by.step.range, [-1200, 1200], "an interval keeps its range");
});

test("a time is never negative, and a step larger than the range is dropped", () => {
  const [t, s] = core.normalizeParams({
    t: { type: "slider", range: [-100, 1000], value: 200, unit: "ms" },
    s: { type: "slider", range: [0, 10], value: 5, step: 50 },
  });
  assert.deepEqual(t.range, [0, 1000]);
  assert.equal(s.step, 0);
  assert.throws(() => core.normalizeParams({ t: { type: "slider", range: [-100, -10], value: -50, unit: "ms" } }),
    /a time cannot be negative/);
});

test("a pitch parameter takes names at the inlet too", () => {
  const [target, register, step] = core.normalizeParams({
    target: { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" },
    register: { type: "range", range: [3600, 9600], value: [4800, 8400], unit: "mc" },
    step: { type: "slider", range: [-1200, 1200], value: 400, unit: "mc" },
  });
  assert.equal(core.coerce(target, ["E4"]), 6400);
  assert.equal(core.coerce(target, [6450]), 6450, "exact numbers stay exact");
  assert.deepEqual(core.coerce(register, ["G6", "C2"]), [3600, 9100]);
  assert.throws(() => core.coerce(target, ["H4"]), /cannot use/);
  assert.throws(() => core.coerce(step, ["E4"]), /cannot use/, "an interval is a number");
});

test("pitches outside C0..G9 come back in by octaves; a MIDI number is still an error", () => {
  const code = (pitch) => `
const params = { base: { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" } };
function produce(p) { const s = score(); s.voice("Flute").note(0, ${pitch}, 500); return s; }`;
  const at = (pitch) => core.run(core.compile(code(pitch)), {}).canonical.voices[0].chords[0].notes[0].pitch;
  assert.equal(at("p.base - 4950"), 2250, "1050 folds up an octave");
  assert.equal(at("p.base + 7000"), 11800, "13000 folds down an octave");
  assert.equal(at("p.base"), 6000);
  assert.throws(() => at("60"), /looks like a MIDI note number/);
});
