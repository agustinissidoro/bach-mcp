/*
bachmcp.runner.loader.js
------------------
Loads and runs an algorithm file, with the algorithmic core library in scope
(algorithmic_core_library/bachmcp.lib.index.js). The same module runs in Max
(v8, in the runners: runners/bachmcp.runner.engine.js) and in Node (the check before a file reaches Max), so
an algorithm behaves identically in both.

An algorithm is one of two kinds:

    a producer makes a score from nothing       function produce(p) { ... return s; }
    a transformer changes a score it is given   function transform(source, p) { ... return out; }

and declares its parameters first (bachmcp.runner.paramspec.js):

    const params = {
      times:    { type: "slider", range: [1, 64], value: 16 },
      register: { type: "range",  range: [3600, 9600], value: [4800, 8400], unit: "mc" },
      seed:     { type: "seed",   value: 1 },
    };

`p` holds the current value of every parameter. `source` is the original score
(JSON) a transformer works on: the runner keeps it, so every run starts again
from it, never from the transformer's own output. Both return a JSON score.
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
  const generate = typeof parts.generate === "function" ? parts.generate : null;
  if (produce && transform) {
    throw new AlgoError("define produce or transform, not both: a producer makes a score, a transformer changes its source");
  }
  if (!produce && !transform && !generate) {
    throw new AlgoError("function produce(p) { ... } (a producer) or function transform(source, p) { ... } (a transformer) is missing");
  }
  const specs = normalizeParams(parts.params);
  const kind = transform ? "transformer" : "producer";
  return { specs, kind, fn: transform || produce || generate, legacy: !produce && !transform, state };
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
  const name = compiled.kind === "transformer" ? "transform" : (compiled.legacy ? "generate" : "produce");
  if (compiled.kind === "transformer" && !source) {
    throw new AlgoError("this transformer has no source score yet: send it one (input dictionary <name>)");
  }
  let result;
  try {
    const p = prepare(compiled.specs, values);
    if (compiled.kind === "transformer") result = compiled.fn(copy(source), p);
    else if (compiled.legacy) result = compiled.fn(p, source ? copy(source) : null);
    else result = compiled.fn(p);
  } catch (e) {
    if (e instanceof AlgoError) throw e;
    throw new AlgoError(`error in ${name}: ${e.message}`, lineOf(e));
  }
  if (result === undefined || result === null) {
    throw new AlgoError(`${name}() returned nothing: it must end by returning the score`);
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

module.exports = { AlgoError, LIBRARY, compile, run };
