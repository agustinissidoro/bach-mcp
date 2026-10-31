// bachmcp.runner.loader.js and bachmcp.runner.paramspec.js: loading, checking and running an algorithm file. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { JS_DIR } = require("./maxmock.js");

const loader = require(path.join(JS_DIR, "runners", "bachmcp.runner.loader.js"));
const paramspec = require(path.join(JS_DIR, "runners", "bachmcp.runner.paramspec.js"));

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
  const c = loader.compile(SPIRAL);
  const r = loader.run(c, paramspec.defaults(c.specs));
  assert.deepEqual(pitches(r), [6200, 6500, 6900, 6700, 7100, 6400, 7300, 6600, 6900]);
  assert.equal(r.notes, 9);
});

test("the same values give the same score; the seed changes it", () => {
  const c = loader.compile(SPIRAL);
  const values = Object.assign(paramspec.defaults(c.specs), { drift: 80 });
  const a = loader.run(c, values), b = loader.run(c, values);
  assert.deepEqual(a.score, b.score);
  assert.notDeepEqual(loader.run(c, Object.assign({}, values, { seed: 2 })).score, a.score);
});

test("random streams are independent: more passes do not reshuffle the first ones", () => {
  const code = `const params = { n: { type: "slider", range: [1, 50], value: 5 }, seed: { type: "seed", value: 7 } };
    function generate(p) { const s = score(); const v = s.voice("A"); const r = rng("pitch");
      for (let i = 0; i < p.n; i++) v.note(i * 100, 6000 + r.int(0, 1200), 100); return s; }`;
  const c = loader.compile(code);
  const five = pitches(loader.run(c, { n: 5, seed: 7 }));
  const nine = pitches(loader.run(c, { n: 9, seed: 7 }));
  assert.deepEqual(nine.slice(0, 5), five);
});

test("Math.random is seeded too", () => {
  const code = `const params = { seed: { type: "seed", value: 3 } };
    function generate() { const s = score(); s.voice("A").note(0, 6000 + Math.floor(Math.random() * 1000), 100); return s; }`;
  const c = loader.compile(code);
  assert.deepEqual(loader.run(c, { seed: 3 }).score, loader.run(c, { seed: 3 }).score);
});

test("parameter declarations are completed and checked", () => {
  const specs = paramspec.normalizeParams({
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
  for (const [params, message] of bad) assert.throws(() => paramspec.normalizeParams(params), message);
  assert.throws(() => loader.compile("function generate() {}"), /const params = \{ \.\.\. \} is missing/);
  assert.throws(() => loader.compile("const params = {};"), /produce\(p\).*transform\(source, p\).*is missing/);
});

test("values from Max are clamped, snapped and typed", () => {
  const specs = paramspec.normalizeParams({
    times: { type: "slider", range: [1, 64], value: 16 },
    register: { type: "range", range: [3600, 9600] },
    legato: { type: "toggle" },
    mode: { type: "menu", options: ["up", "down", 3] },
    shape: { type: "curve", range: [0, 10] },
    durs: { type: "list", range: [50, 2000], value: [250] },
  });
  const [times, register, legato, mode, shape, durs] = specs;
  assert.equal(paramspec.coerce(times, [33.7]), 34);
  assert.equal(paramspec.coerce(times, ["900"]), 64);
  assert.deepEqual(paramspec.coerce(register, [9000, 4000]), [4000, 9000]);
  assert.equal(paramspec.coerce(legato, [0]), false);
  assert.equal(paramspec.coerce(legato, ["on"]), true);
  assert.equal(paramspec.coerce(mode, ["down"]), "down");
  assert.equal(paramspec.coerce(mode, [1]), "down");
  assert.equal(paramspec.coerce(mode, ["3"]), 3);
  assert.deepEqual(paramspec.coerce(shape, [0.1, 2, 0.5, 20, 0.9, 5]), [[0, 2], [0.5, 10], [1, 5]]);
  assert.deepEqual(paramspec.coerce(durs, [10, 300, 5000]), [50, 300, 2000]);
  assert.throws(() => paramspec.coerce(times, ["many"]), /cannot use/);
  assert.deepEqual(paramspec.valueAtoms(shape, [[0, 1], [1, 2]]), [0, 1, 1, 2]);
  assert.deepEqual(paramspec.valueAtoms(legato, true), [1]);
});

test("a curve parameter arrives as a function of 0..1", () => {
  const code = `const params = { shape: { type: "curve", range: [0, 100], value: [[0, 0], [0.5, 100], [1, 0]] } };
    function generate(p) { const s = score(); s.voice("A").note(0, 6000 + p.shape(0.25), 100); return s; }`;
  const c = loader.compile(code);
  assert.equal(loader.run(c, paramspec.defaults(c.specs)).score.voices[0].chords[0].notes[0].pitch, 6050);
});

test("errors name the line of the file", () => {
  const code = 'const params = {};\nfunction generate(p) {\n  const x = 1;\n  return missing.value;\n}';
  const c = loader.compile(code);
  assert.throws(() => loader.run(c, {}), (e) => e.line === 4 && /missing is not defined/.test(e.message));
  assert.throws(() => loader.compile("const params = {;"), /syntax error/);
  assert.throws(() => loader.run(loader.compile("const params = {}; function generate() {}"), {}), /returned nothing/);
  assert.throws(() => loader.run(loader.compile("const params = {}; function generate() { return [1, 2]; }"), {}),
    /must return a score: an object with "voices"/);
});

test("names in the file can shadow the library", () => {
  const code = `const params = {};
    const lerp = (a, b) => a + b;
    function clamp() { return 1; }
    function generate() { const s = score(); s.voice("A").note(0, lerp(6000, clamp()), 100); return s; }`;
  assert.equal(loader.run(loader.compile(code), {}).score.voices[0].chords[0].notes[0].pitch, 6001);
});

test("producers and transformers", () => {
  const producer = loader.compile(`const params = {};
    function produce(p) { const s = score(); s.voice("A").note(0, 6000, 100); return s; }`);
  assert.equal(producer.kind, "producer");
  assert.equal(loader.run(producer, {}).notes, 1);
  const legacy = loader.compile(`const params = {};
    function generate(p, input) { const s = score(); s.voice("A").note(0, input ? 7000 : 6000, 100); return s; }`);
  assert.equal(legacy.kind, "producer");
  assert.equal(loader.run(legacy, {}, { voices: [] }).score.voices[0].chords[0].notes[0].pitch, 7000);
  assert.throws(() => loader.compile("const params = {}; function produce(p) {} function transform(s, p) {}"), /define one of produce, transform or select/);
});

test("a transformer always starts again from the original source", () => {
  const t = loader.compile(`const params = { shift: { type: "slider", range: [-1200, 1200], value: 100 } };
    function transform(source, p) { eachNote(source, (n) => { n.pitch += p.shift; }); return source; }`);
  assert.equal(t.kind, "transformer");
  const source = { voices: [{ chords: [{ onset: 0, notes: [{ pitch: 6000, dur: 100 }] }] }] };
  const pitch = (r) => r.score.voices[0].chords[0].notes[0].pitch;
  assert.equal(pitch(loader.run(t, { shift: 100 }, source)), 6100);
  assert.equal(pitch(loader.run(t, { shift: 300 }, source)), 6300, "from the original, not from 6100");
  assert.equal(source.voices[0].chords[0].notes[0].pitch, 6000, "the source itself is untouched");
  assert.throws(() => loader.run(t, { shift: 1 }, null), /no source score yet/);
  assert.throws(() => loader.run(loader.compile("const params = {}; function transform(s, p) { return null; }"), {}, source),
    /transform\(\) returned nothing/);
});

test("number parameters know what they are: pitch, interval, time or plain, each with its snap grid", () => {
  const specs = paramspec.normalizeParams({
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
  const [t, s] = paramspec.normalizeParams({
    t: { type: "slider", range: [-100, 1000], value: 200, unit: "ms" },
    s: { type: "slider", range: [0, 10], value: 5, step: 50 },
  });
  assert.deepEqual(t.range, [0, 1000]);
  assert.equal(s.step, 0);
  assert.throws(() => paramspec.normalizeParams({ t: { type: "slider", range: [-100, -10], value: -50, unit: "ms" } }),
    /a time cannot be negative/);
});

test("a pitch parameter takes names at the inlet too", () => {
  const [target, register, step] = paramspec.normalizeParams({
    target: { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" },
    register: { type: "range", range: [3600, 9600], value: [4800, 8400], unit: "mc" },
    step: { type: "slider", range: [-1200, 1200], value: 400, unit: "mc" },
  });
  assert.equal(paramspec.coerce(target, ["E4"]), 6400);
  assert.equal(paramspec.coerce(target, [6450]), 6450, "exact numbers stay exact");
  assert.deepEqual(paramspec.coerce(register, ["G6", "C2"]), [3600, 9100]);
  assert.throws(() => paramspec.coerce(target, ["H4"]), /cannot use/);
  assert.throws(() => paramspec.coerce(step, ["E4"]), /cannot use/, "an interval is a number");
});

test("pitches outside C0..G9 come back in by octaves", () => {
  const code = (pitch) => `
const params = { base: { type: "slider", range: [3600, 9600], value: 6000, unit: "mc" } };
function produce(p) { const s = score(); s.voice("Flute").note(0, ${pitch}, 500); return s; }`;
  const at = (pitch) => loader.run(loader.compile(code(pitch)), {}).score.voices[0].chords[0].notes[0].pitch;
  assert.equal(at("p.base - 4950"), 2250, "1050 folds up an octave");
  assert.equal(at("p.base + 7000"), 11800, "13000 folds down an octave");
  assert.equal(at("p.base"), 6000);
  assert.equal(at("60"), 60, "a MIDI number is left as it is");
});
