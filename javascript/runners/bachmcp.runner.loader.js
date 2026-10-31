/*
bachmcp.runner.loader.js
------------------
Loads and runs an algorithm file, with the algorithmic core library in scope
(algorithmic_core_library/bachmcp.lib.index.js). The same module runs in Max
(v8, in the runners: runners/bachmcp.runner.engine.js) and in Node (the check before a file reaches Max), so
an algorithm behaves identically in both.

An algorithm is one of three kinds:

    a producer makes a score from nothing       function produce(p) { ... return s; }
    a transformer changes a score it is given   function transform(source, p) { ... return out; }
    a selector picks notes of a score           function select(source, p) { ... return notes; }

A selector returns a list of notes: the note objects of `source` themselves (as
eachNote gives them), or their addresses [voice, chord, note], 1-based as in
bach. run() turns either into addresses.

and declares its parameters first (bachmcp.runner.paramspec.js):

    const params = {
      times:    { type: "slider", range: [1, 64], value: 16 },
      register: { type: "range",  range: [3600, 9600], value: [4800, 8400], unit: "mc" },
      seed:     { type: "seed",   value: 1 },
    };

`p` holds the current value of every parameter. `source` is the original score
(JSON) a transformer works on: the runner keeps it, so every run starts again
from it, never from the transformer's own output. A producer and a transformer return a JSON score.
(An older file with `function generate(p, input)` is a producer.)

    compile(code)                  the file -> {specs, kind, fn, state}; throws AlgoError
    run(compiled, values, source)  one run -> {score, notes, ms}

Scores are bachjson-complete, as every object passes them: the loader does not
check their syntax. It only makes sure a result is a score (it has voices) of at
most MAX_NOTES notes (more would flood Max), and
brings pitches that a parameter pushed out of C0..G9 back in by octaves.
*/
"use strict";

// Max finds a file by its name, on the search path; Node by where it is.
function need(name) {
  const places = ["", "./", "../", "../algorithmic_core_library/", "../runners/"];
  for (const place of places) {
    try {
      return require(place + name);
    } catch (e) {
      if (place === places[places.length - 1]) throw e;
    }
  }
}

const { AlgoError, isObject, isNumber } = need("bachmcp.lib.base.js");
const { makeLibrary, LIBRARY, OCTAVE, copy } = need("bachmcp.lib.index.js");
const { normalizeParams, prepare, MIDI_RANGE } = need("bachmcp.runner.paramspec.js");
const { MAX_NOTES } = need("bachmcp.lib.units.js");

function wrapSource(code) {
  return '"use strict";\nreturn (function () {\n' + code +
    '\n;return { params: typeof params === "undefined" ? undefined : params,' +
    ' produce: typeof produce === "undefined" ? undefined : produce,' +
    ' transform: typeof transform === "undefined" ? undefined : transform,' +
    ' select: typeof select === "undefined" ? undefined : select,' +
    ' generate: typeof generate === "undefined" ? undefined : generate };\n})();';
}

// Where line 1 of the file lands in a stack trace of code built by `new Function`.
const LINE_OFFSET = (() => {
  try {
    new Function(wrapSource('throw new Error("probe");'))();
  } catch (e) {
    const m = /<anonymous>:(\d+):\d+/.exec(String(e.stack));
    if (m) return Number(m[1]) - 1;
  }
  return null;
})();

function lineOf(error) {
  const m = /<anonymous>:(\d+):\d+/.exec(String(error && error.stack));
  return m && LINE_OFFSET !== null ? Number(m[1]) - LINE_OFFSET : null;
}

/** Algorithm source text -> {specs, kind, fn, state}. Throws AlgoError. */
function compile(code) {
  const state = { seed: 0, streams: new Map() };
  const lib = makeLibrary(state);
  let factory;
  try {
    factory = new Function(...LIBRARY, wrapSource(code));
  } catch (e) {
    throw new AlgoError(`syntax error: ${e.message}`);
  }
  let parts;
  try {
    parts = factory(...LIBRARY.map((k) => lib[k]));
  } catch (e) {
    throw new AlgoError(`error while loading: ${e.message}`, lineOf(e));
  }
  const produce = typeof parts.produce === "function" ? parts.produce : null;
  const transform = typeof parts.transform === "function" ? parts.transform : null;
  const select = typeof parts.select === "function" ? parts.select : null;
  const generate = typeof parts.generate === "function" ? parts.generate : null;
  if ([produce, transform, select].filter(Boolean).length > 1) {
    throw new AlgoError("define one of produce, transform or select: a producer makes a score, a transformer changes its source, a selector picks notes of it");
  }
  if (!produce && !transform && !select && !generate) {
    throw new AlgoError("function produce(p) { ... } (a producer), function transform(source, p) { ... } (a transformer) or function select(source, p) { ... } (a selector) is missing");
  }
  const specs = normalizeParams(parts.params);
  const kind = transform ? "transformer" : (select ? "selector" : "producer");
  return { specs, kind, fn: transform || select || produce || generate, legacy: !produce && !transform && !select, state };
}

/**
 * Run a compiled algorithm. A transformer works on `source` (a JSON score), which
 * stays untouched. Returns {score, notes, ms}: the score as the algorithm returned
 * it (pitches folded into C0..G9), its number of notes, and the time it took.
 */
function run(compiled, values, source) {
  const start = Date.now();
  const seedSpec = compiled.specs.find((s) => s.type === "seed");
  compiled.state.seed = seedSpec ? (values[seedSpec.name] !== undefined ? values[seedSpec.name] : seedSpec.default) : 0;
  compiled.state.streams = new Map();
  const name = { transformer: "transform", selector: "select" }[compiled.kind] || (compiled.legacy ? "generate" : "produce");
  const given = compiled.kind === "transformer" || compiled.kind === "selector";
  if (given && !source) {
    throw new AlgoError(`this ${compiled.kind} has no source score yet: send it one (input dictionary <name>)`);
  }
  let result;
  let input = null;
  try {
    const p = prepare(compiled.specs, values);
    if (given) result = compiled.fn(input = copy(source), p);
    else if (compiled.legacy) result = compiled.fn(p, source ? copy(source) : null);
    else result = compiled.fn(p);
  } catch (e) {
    if (e instanceof AlgoError) throw e;
    throw new AlgoError(`error in ${name}: ${e.message}`, lineOf(e));
  }
  if (result === undefined || result === null) {
    throw new AlgoError(`${name}() returned nothing: it must end by returning ${compiled.kind === "selector" ? "the notes it picks" : "the score"}`);
  }
  if (compiled.kind === "selector") {
    const selection = addresses(input, result, name);
    return { selection, notes: selection.length, ms: Date.now() - start };
  }
  if (!isObject(result) || !Array.isArray(result.voices)) {
    throw new AlgoError(`${name}() must return a score: an object with "voices"`);
  }
  const notes = countNotes(result);
  if (notes > MAX_NOTES) throw new AlgoError(`${name}() made more than ${MAX_NOTES} notes (${notes})`);
  foldPitches(result);
  return { score: copy(result), notes, ms: Date.now() - start };
}

/**
 * Every pitch of a result brought into C0..G9 by whole octaves, so that a parameter at
 * its extreme (a base at the bottom, a step at the top) still makes a playable score.
 * 0..127 is left alone: that is a MIDI number written by mistake, and the check says so.
 */
function foldPitch(p) {
  if (!isNumber(p) || (p >= 0 && p <= 127)) return p;
  while (p < MIDI_RANGE[0]) p += OCTAVE;
  while (p > MIDI_RANGE[1]) p -= OCTAVE;
  return p;
}

/** A selector's result -> sorted, distinct [voice, chord, note] addresses (1-based) of notes in `score`. */
function addresses(score, result, name) {
  if (!Array.isArray(result)) throw new AlgoError(`${name}() must return a list of notes (note objects or [voice, chord, note])`);
  const where = new Map();
  const voices = score.voices || [];
  voices.forEach((v, vi) => ((v && v.chords) || []).forEach((c, ci) =>
    ((c && c.notes) || []).forEach((n, ni) => where.set(n, [vi + 1, ci + 1, ni + 1]))));
  const seen = new Set();
  const out = [];
  for (const item of result) {
    let a = where.get(item);
    if (!a && Array.isArray(item) && item.length === 3 && item.every(Number.isInteger)) {
      const [v, c, n] = item;
      const chord = voices[v - 1] && voices[v - 1].chords && voices[v - 1].chords[c - 1];
      if (chord && chord.notes && chord.notes[n - 1]) a = item.slice();
    }
    if (!a) throw new AlgoError(`${name}() returned something that is not a note of the source: ${JSON.stringify(item)}`);
    const key = a.join(" ");
    if (!seen.has(key)) {
      seen.add(key);
      out.push(a);
    }
  }
  return out.sort((x, y) => x[0] - y[0] || x[1] - y[1] || x[2] - y[2]);
}

function countNotes(score) {
  let n = 0;
  for (const v of score.voices) for (const c of (v && v.chords) || []) n += ((c && c.notes) || []).length;
  return n;
}

function foldPitches(result) {
  for (const v of (result && Array.isArray(result.voices) ? result.voices : [])) {
    for (const c of (v && Array.isArray(v.chords) ? v.chords : [])) {
      if (isObject(c) && Array.isArray(c.notes)) {
        for (const n of c.notes) {
          if (isObject(n)) n.pitch = foldPitch(n.pitch);
          else if (Array.isArray(n)) n[0] = foldPitch(n[0]);
        }
      } else if (Array.isArray(c)) {
        for (let i = 1; i < c.length; i++) if (Array.isArray(c[i])) c[i][0] = foldPitch(c[i][0]);
      }
    }
  }
}

module.exports = { AlgoError, LIBRARY, compile, run, countNotes };
