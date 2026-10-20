/*
bach.mcp.core.js
----------------
The core library of bach.mcp.algo: what every algorithm file runs with, and the
loader that turns a file into parameters plus a generate function. The same
module runs in Max (v8) and in Node (the check that runs before a file reaches
Max), so an algorithm behaves identically in both.

An algorithm file has two parts:

    const params = {
      times:    { type: "slider", range: [1, 64], value: 16 },
      register: { type: "range",  range: [3600, 9600], value: [4800, 8400], unit: "mc" },
      seed:     { type: "seed",   value: 1 },
    };

    function generate(p, input) {
      const s = score();
      const v = s.voice("Flute");
      ...
      return s;
    }

`p` holds the current value of every parameter; `input` is the score arriving
at the runner's right inlet (or null). generate returns a JSON score.

Everything in LIBRARY below is in scope inside the file, without imports.
*/
"use strict";

function requireSibling(name) {
  try {
    return require(name); // Max: found through the search path
  } catch (e) {
    return require("./" + name); // Node: next to this file
  }
}

const S = requireSibling("bach.mcp.score.js");

class AlgoError extends Error {
  constructor(message, line) {
    super(message);
    this.name = "AlgoError";
    this.line = line || null;
  }
}

function isObject(x) {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

function isNumber(x) {
  return typeof x === "number" && Number.isFinite(x);
}

// ── Units ───────────────────────────────────────────────────────────────── //

const SEMITONE = 100;
const QUARTERTONE = 50;
const OCTAVE = 1200;
const MIDDLE_C = 6000;
const SECOND = 1000;

// ── Score building ──────────────────────────────────────────────────────── //

// Marks drawn once per chord; everything else in `opts` goes on each note.
const CHORD_OPTS = ["dyn", "art", "text", "lyric"];

class Voice {
  constructor(name, clef) {
    this.name = name;
    if (clef) this.clef = clef;
    this.chords = [];
  }

  /** A chord of one note. Returns the chord, so its marks can still be changed. */
  note(onset, pitch, dur, opts) {
    return this.chord(onset, [pitch], dur, opts);
  }

  /** A chord: pitches is a list of midicents, or of note objects {pitch, dur, vel, ...}. */
  chord(onset, pitches, dur, opts) {
    const chord = { onset };
    const notes = pitches.map((p) => (isObject(p) ? Object.assign({ dur }, p) : { pitch: p, dur }));
    for (const [key, value] of Object.entries(opts || {})) {
      if (value === undefined || value === null) continue;
      if (CHORD_OPTS.includes(key)) chord[key] = value;
      else for (const n of notes) n[key] = value;
    }
    chord.notes = notes;
    this.chords.push(chord);
    return chord;
  }

  /** When the last note of this voice stops sounding, in milliseconds. */
  get end() {
    let end = 0;
    for (const c of this.chords) for (const n of c.notes) end = Math.max(end, c.onset + n.dur);
    return end;
  }
}

class Score {
  constructor() {
    this.voices = [];
  }

  /** The voice with this name, created on first use. Voices appear top to bottom in creation order. */
  voice(name, clef) {
    let v = this.voices.find((x) => x.name === name);
    if (!v) {
      v = new Voice(name, clef);
      this.voices.push(v);
    }
    return v;
  }

  marker(onset, name) {
    if (!this.markers) this.markers = [];
    this.markers.push({ onset, name: String(name) });
    return this;
  }

  get end() {
    return Math.max(0, ...this.voices.map((v) => v.end));
  }
}

function score() {
  return new Score();
}

// ── Randomness: seeded, so the same parameters give the same score ──────── //

function hashString(text) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

/** A random generator (mulberry32) seeded by any number or text. r() is uniform in [0, 1). */
function makeRandom(seed) {
  let state = hashString(String(seed)) || 1;
  const next = () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const r = () => next();
  r.float = (lo = 0, hi = 1) => lo + (hi - lo) * next();
  r.int = (lo, hi) => {
    if (hi === undefined) [lo, hi] = [0, lo];
    lo = Math.ceil(lo);
    hi = Math.floor(hi);
    return lo + Math.floor(next() * (hi - lo + 1));
  };
  r.pick = (list) => list[Math.floor(next() * list.length)];
  r.weighted = (list, weights) => {
    const total = weights.reduce((a, b) => a + Math.max(0, b), 0);
    let x = next() * total;
    for (let i = 0; i < list.length; i++) {
      x -= Math.max(0, weights[i]);
      if (x < 0) return list[i];
    }
    return list[list.length - 1];
  };
  r.shuffle = (list) => {
    const out = list.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  };
  r.gauss = (mean = 0, sd = 1) => {
    const u = 1 - next();
    const v = next();
    return mean + sd * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  r.chance = (p) => next() < p;
  return r;
}

// ── Numbers and shapes ──────────────────────────────────────────────────── //

const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const rescale = (x, inLo, inHi, outLo, outHi) =>
  inHi === inLo ? outLo : outLo + ((x - inLo) * (outHi - outLo)) / (inHi - inLo);

function wrap(x, lo, hi) {
  const span = hi - lo;
  return span <= 0 ? lo : lo + ((((x - lo) % span) + span) % span);
}

/** Reflect x back into [lo, hi], like a ball between two walls. */
function fold(x, lo, hi) {
  const span = hi - lo;
  if (span <= 0) return lo;
  const t = wrap(x - lo, 0, 2 * span);
  return lo + (t > span ? 2 * span - t : t);
}

/** The nearest multiple of grid (plus offset). */
const snap = (x, grid, offset = 0) => (grid > 0 ? offset + Math.round((x - offset) / grid) * grid : x);

/** [start, start + step, ...], n values. */
function seq(n, start = 0, step = 1) {
  return Array.from({ length: Math.max(0, Math.floor(n)) }, (_, i) => start + i * step);
}

/** n values from a to b, both included. */
function linspace(a, b, n) {
  n = Math.max(0, Math.floor(n));
  if (n === 1) return [a];
  return Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1));
}

const sum = (list) => list.reduce((a, b) => a + b, 0);

/** Running starts from a list of durations: [start, start + d0, start + d0 + d1, ...]. */
function accumulate(durations, start = 0) {
  const out = [];
  let t = start;
  for (const d of durations) {
    out.push(t);
    t += d;
  }
  return out;
}

/** A breakpoint function: env([[x, y], ...])(x), linear between points, flat outside. */
function env(points) {
  const pts = points.map((p) => [Number(p[0]), Number(p[1])]).sort((a, b) => a[0] - b[0]);
  const f = (x) => {
    if (!pts.length) return 0;
    if (x <= pts[0][0]) return pts[0][1];
    for (let i = 1; i < pts.length; i++) {
      if (x <= pts[i][0]) {
        const [x0, y0] = pts[i - 1];
        const [x1, y1] = pts[i];
        return x1 === x0 ? y1 : y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
      }
    }
    return pts[pts.length - 1][1];
  };
  f.points = pts;
  return f;
}

/** Bend t in 0..1: k = 0 straight, k > 0 starts slow (exponential), k < 0 starts fast. */
function warp(t, k) {
  if (!k) return t;
  return (Math.exp(k * t) - 1) / (Math.exp(k) - 1);
}

// ── Procedures ──────────────────────────────────────────────────────────── //

/** [x0, f(x0, 1), f(f(x0, 1), 2), ...], n values: a state that evolves step by step. */
function iterate(n, x0, f) {
  const out = [];
  let x = x0;
  for (let i = 0; i < n; i++) {
    out.push(x);
    x = f(x, i + 1);
  }
  return out;
}

/** A random walk of n values: each step moves by up to ±step, reflected inside [min, max]. */
function walk({ n, start, step, min, max, rng }) {
  const r = rng || makeRandom("walk");
  return iterate(n, clamp(start, min, max), (x) => fold(x + r.float(-step, step), min, max));
}

/**
 * A Markov chain of n states from `start`. table: {state: {next: weight, ...}} or
 * {state: [next, ...]} (equal weights). Stops early at a state with no way out.
 */
function markov(table, { n, start, rng }) {
  const r = rng || makeRandom("markov");
  const asValue = (key) => (key !== "" && !Number.isNaN(Number(key)) ? Number(key) : key);
  const out = [];
  let state = start;
  for (let i = 0; i < n; i++) {
    out.push(state);
    const options = table[state];
    if (!options) break;
    if (Array.isArray(options)) {
      if (!options.length) break;
      state = r.pick(options);
    } else {
      const keys = Object.keys(options);
      if (!keys.length) break;
      state = asValue(r.weighted(keys, keys.map((k) => options[k])));
    }
  }
  return out;
}

/** An L-system: rewrite every symbol of the axiom by its rule, `generations` times. Returns text. */
function rewrite(axiom, rules, generations) {
  let text = String(axiom);
  for (let g = 0; g < generations; g++) {
    let next = "";
    for (const ch of text) next += Object.prototype.hasOwnProperty.call(rules, ch) ? rules[ch] : ch;
    text = next;
    if (text.length > 100000) throw new AlgoError("rewrite() grew past 100000 symbols: use fewer generations");
  }
  return text;
}

/**
 * An elementary cellular automaton (rule 0-255). cells: the first row as 0/1 values,
 * or a width (one live cell in the middle). Returns `steps` rows, the first included.
 */
function automaton(rule, cells, steps) {
  let row = Array.isArray(cells) ? cells.map((c) => (c ? 1 : 0)) : seq(cells).map((i) => (i === Math.floor(cells / 2) ? 1 : 0));
  const rows = [];
  for (let s = 0; s < steps; s++) {
    rows.push(row);
    const w = row.length;
    row = row.map((_, i) => (rule >> ((row[(i - 1 + w) % w] << 2) | (row[i] << 1) | row[(i + 1) % w])) & 1);
  }
  return rows;
}

/** A Euclidean rhythm: `hits` onsets spread as evenly as possible over `steps`, as 1/0. */
function euclid(hits, steps, rotate = 0) {
  return seq(steps).map((i) => ((((i + rotate) * hits) % steps + steps) % steps < hits ? 1 : 0));
}

// ── Parameters ──────────────────────────────────────────────────────────── //

const TYPES = ["slider", "range", "toggle", "menu", "seed", "curve", "list"];
const TYPE_ALIASES = {
  number: "slider", knob: "slider", dial: "slider", float: "slider", int: "slider",
  bool: "toggle", boolean: "toggle", checkbox: "toggle", switch: "toggle",
  choice: "menu", options: "menu", dropdown: "menu", enum: "menu",
  envelope: "curve", breakpoints: "curve", function: "curve", shape: "curve",
  multislider: "list", array: "list", values: "list",
  minmax: "range", span: "range",
};
const SPEC_KEYS = ["type", "range", "value", "step", "unit", "options"];
const SPEC_ALIASES = { default: "value", values: "options", choices: "options", units: "unit" };
const SPEC_IGNORED = ["label", "doc", "info", "description", "help"];
// Messages bach.mcp.algo answers itself; a parameter cannot take these names.
const RESERVED = [
  "load", "reload", "run", "bang", "auto", "watch", "setname", "remote", "input", "values",
  "getstate", "open", "edit", "dictionary", "list", "int", "float", "anything", "loadbang",
  "save", "notifydeleted", "compile", "autowatch", "wclose", "setprop", "getprop", "delprop",
  "msg_int", "msg_float", "set", "spec", "status", "clear", "done",
  "post", "cpost", "error", "outlet", "messnamed", "arrayfromargs", "embedmessage", "assist",
];
const MAX_LIST = 256;

function decimals(x) {
  return Number(Number(x).toFixed(6));
}

function snapTo(spec, x) {
  const [lo, hi] = spec.range;
  x = clamp(x, lo, hi);
  if (spec.step > 0) x = clamp(lo + Math.round((x - lo) / spec.step) * spec.step, lo, hi);
  return decimals(x);
}

function rangeOf(raw, name, fallback) {
  const r = raw === undefined ? fallback : raw;
  if (!(Array.isArray(r) && r.length === 2 && isNumber(r[0]) && isNumber(r[1]) && r[0] < r[1])) {
    throw new AlgoError(`params.${name}: "range" must be [low, high] with low < high, e.g. [0, 100]`);
  }
  return [r[0], r[1]];
}

function autoStep(numbers, range) {
  return numbers.every(Number.isInteger) && range[1] - range[0] > 1 ? 1 : 0;
}

function normalizeSpec(name, raw) {
  if (!/^[A-Za-z_][A-Za-z0-9_]{0,31}$/.test(name)) {
    throw new AlgoError(`params: "${name}" is not a usable name. Use letters, digits and _ (e.g. "times", "max_dur")`);
  }
  if (RESERVED.includes(name)) {
    throw new AlgoError(`params: "${name}" is a name Max uses for its own messages; rename the parameter ` +
      `(e.g. "${name}_amount"). Not usable: open, load, run, set, input, values, auto, watch, clear, done`);
  }
  if (!isObject(raw)) {
    throw new AlgoError(`params.${name}: must be an object like { type: "slider", range: [0, 100], value: 50 }`);
  }
  const s = {};
  for (const [key, value] of Object.entries(raw)) {
    if (SPEC_IGNORED.includes(key)) continue;
    const k = SPEC_ALIASES[key] || key;
    if (k === "min" || k === "max") continue;
    if (!SPEC_KEYS.includes(k)) {
      throw new AlgoError(`params.${name}: unknown key "${key}". A parameter has: ${SPEC_KEYS.join(", ")}`);
    }
    s[k] = value;
  }
  if (s.range === undefined && isNumber(raw.min) && isNumber(raw.max)) s.range = [raw.min, raw.max];
  const type = TYPE_ALIASES[String(s.type).toLowerCase()] || String(s.type).toLowerCase();
  if (!TYPES.includes(type)) {
    throw new AlgoError(`params.${name}: unknown type ${JSON.stringify(s.type)}. Types: ${TYPES.join(", ")}`);
  }
  const spec = { name, type };
  if (s.unit !== undefined) spec.unit = String(s.unit).slice(0, 12);
  if (s.step !== undefined && !(isNumber(s.step) && s.step >= 0)) {
    throw new AlgoError(`params.${name}: "step" must be a number >= 0`);
  }

  if (type === "slider") {
    spec.range = rangeOf(s.range, name);
    const v = s.value === undefined ? spec.range[0] : s.value;
    if (!isNumber(v)) throw new AlgoError(`params.${name}: "value" must be a number`);
    spec.step = s.step !== undefined ? s.step : autoStep([spec.range[0], spec.range[1], v], spec.range);
    spec.value = snapTo(spec, v);
  } else if (type === "range") {
    spec.range = rangeOf(s.range, name);
    const v = s.value === undefined ? spec.range.slice() : s.value;
    if (!(Array.isArray(v) && v.length === 2 && v.every(isNumber))) {
      throw new AlgoError(`params.${name}: "value" must be [low, high], e.g. [${spec.range[0]}, ${spec.range[1]}]`);
    }
    spec.step = s.step !== undefined ? s.step : autoStep(spec.range.concat(v), spec.range);
    spec.value = v.map((x) => snapTo(spec, x)).sort((a, b) => a - b);
  } else if (type === "toggle") {
    spec.value = Boolean(s.value);
  } else if (type === "menu") {
    if (!(Array.isArray(s.options) && s.options.length && s.options.every((o) => typeof o === "string" || isNumber(o)))) {
      throw new AlgoError(`params.${name}: a menu needs "options": a list of names or numbers, e.g. ["up", "down"]`);
    }
    spec.options = s.options.slice();
    const v = s.value === undefined ? spec.options[0] : s.value;
    if (!spec.options.some((o) => String(o) === String(v))) {
      throw new AlgoError(`params.${name}: "value" ${JSON.stringify(v)} is not one of the options`);
    }
    spec.value = spec.options.find((o) => String(o) === String(v));
  } else if (type === "seed") {
    spec.range = rangeOf(s.range, name, [0, 9999]);
    spec.step = 1;
    spec.value = snapTo(spec, isNumber(s.value) ? s.value : 1);
  } else if (type === "curve") {
    spec.range = rangeOf(s.range, name, [0, 1]);
    spec.step = s.step || 0;
    const v = s.value === undefined ? [[0, spec.range[0]], [1, spec.range[1]]] : s.value;
    spec.value = curvePoints(spec, v, name);
  } else if (type === "list") {
    spec.range = rangeOf(s.range, name);
    const v = s.value;
    if (!(Array.isArray(v) && v.length && v.length <= MAX_LIST && v.every(isNumber))) {
      throw new AlgoError(`params.${name}: a list needs "value": 1 to ${MAX_LIST} numbers, e.g. [250, 250, 500]`);
    }
    spec.step = s.step !== undefined ? s.step : autoStep(spec.range.concat(v), spec.range);
    spec.value = v.map((x) => snapTo(spec, x));
  }
  spec.default = clone(spec.value);
  return spec;
}

function curvePoints(spec, v, name) {
  if (!(Array.isArray(v) && v.length >= 2 && v.length <= 64 &&
        v.every((p) => Array.isArray(p) && p.length === 2 && p.every(isNumber)))) {
    throw new AlgoError(`params.${name}: a curve "value" is a list of [x, y] points, x from 0 to 1, e.g. [[0, 0], [1, 1]]`);
  }
  const pts = v.map(([x, y]) => [decimals(clamp(x, 0, 1)), snapTo(spec, y)]).sort((a, b) => a[0] - b[0]);
  pts[0][0] = 0;
  pts[pts.length - 1][0] = 1;
  return pts;
}

/** The `params` object of a file -> a list of complete parameter specs, in file order. */
function normalizeParams(params) {
  if (!isObject(params)) {
    throw new AlgoError('const params = { ... } is missing. Example: const params = { times: { type: "slider", range: [1, 64], value: 16 } };');
  }
  return Object.entries(params).map(([name, raw]) => normalizeSpec(name, raw));
}

function clone(x) {
  return x === undefined ? undefined : JSON.parse(JSON.stringify(x));
}

/** The default value of every parameter, by name. */
function defaults(specs) {
  const out = {};
  for (const s of specs) out[s.name] = clone(s.default);
  return out;
}

/** A value arriving as Max atoms (from the panel or a message box) -> the parameter's value. */
function coerce(spec, atoms) {
  const nums = atoms.map(Number);
  const bad = () => new AlgoError(`${spec.name}: cannot use ${JSON.stringify(atoms)} as a ${spec.type} value`);
  switch (spec.type) {
    case "slider":
    case "seed":
      if (!isNumber(nums[0])) throw bad();
      return snapTo(spec, nums[0]);
    case "range":
      if (!(nums.length >= 2 && isNumber(nums[0]) && isNumber(nums[1]))) throw bad();
      return [snapTo(spec, nums[0]), snapTo(spec, nums[1])].sort((a, b) => a - b);
    case "toggle":
      if (atoms[0] === "true" || atoms[0] === "on") return true;
      if (atoms[0] === "false" || atoms[0] === "off") return false;
      if (!isNumber(nums[0])) throw bad();
      return nums[0] !== 0;
    case "menu": {
      const hit = spec.options.find((o) => String(o) === String(atoms[0]));
      if (hit !== undefined) return hit;
      if (Number.isInteger(nums[0]) && nums[0] >= 0 && nums[0] < spec.options.length) return spec.options[nums[0]];
      throw bad();
    }
    case "list":
      if (!(nums.length && nums.length <= MAX_LIST && nums.every(isNumber))) throw bad();
      return nums.map((x) => snapTo(spec, x));
    case "curve": {
      if (!(nums.length >= 4 && nums.length % 2 === 0 && nums.every(isNumber))) throw bad();
      const pts = [];
      for (let i = 0; i < nums.length; i += 2) pts.push([nums[i], nums[i + 1]]);
      return curvePoints(spec, pts, spec.name);
    }
    default:
      throw bad();
  }
}

/** A value -> Max atoms (the inverse of coerce). */
function valueAtoms(spec, value) {
  if (spec.type === "toggle") return [value ? 1 : 0];
  if (spec.type === "curve") return [].concat(...value);
  return Array.isArray(value) ? value.slice() : [value];
}

/** One line per parameter: what the model and the Max console are told. */
function describe(specs, values) {
  return specs.map((s) => {
    const v = values ? values[s.name] : s.value;
    const unit = s.unit ? ` ${s.unit}` : "";
    const span = s.range ? ` ${S.fmt(s.range[0])}..${S.fmt(s.range[1])}` : "";
    switch (s.type) {
      case "menu":
        return `${s.name}: menu [${s.options.join(", ")}] = ${v}`;
      case "toggle":
        return `${s.name}: toggle = ${v}`;
      case "curve":
        return `${s.name}: curve${span}${unit} = ${JSON.stringify(v)}`;
      default:
        return `${s.name}: ${s.type}${span}${unit} = ${JSON.stringify(v)}`;
    }
  });
}

// ── Loading and running ─────────────────────────────────────────────────── //

/** The names in scope inside an algorithm file. */
function makeLibrary(state) {
  const rng = (name = "main") => {
    const key = String(name);
    if (!state.streams.has(key)) state.streams.set(key, makeRandom(`${state.seed}:${key}`));
    return state.streams.get(key);
  };
  const seededMath = Object.create(Math);
  seededMath.random = () => rng("Math.random")();
  return {
    SEMITONE, QUARTERTONE, OCTAVE, MIDDLE_C, SECOND,
    score, rng, Math: seededMath,
    lerp, clamp, rescale, wrap, fold, snap, seq, linspace, sum, accumulate, env, warp,
    iterate, walk, markov, rewrite, automaton, euclid,
  };
}

const LIBRARY = Object.keys(makeLibrary({ seed: 0, streams: new Map() }));

function wrapSource(code) {
  return '"use strict";\nreturn (function () {\n' + code +
    '\n;return { params: typeof params === "undefined" ? undefined : params,' +
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

/** Algorithm source text -> {specs, generate, state}. Throws AlgoError. */
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
  if (typeof parts.generate !== "function") {
    throw new AlgoError("function generate(p, input) { ... return s; } is missing");
  }
  const specs = normalizeParams(parts.params);
  return { specs, generate: parts.generate, state };
}

/** The values generate() sees: a copy of each value; a curve becomes a function of 0..1. */
function prepare(specs, values) {
  const p = {};
  for (const s of specs) {
    const v = clone(values[s.name] === undefined ? s.default : values[s.name]);
    p[s.name] = s.type === "curve" ? env(v) : v;
  }
  return p;
}

/**
 * Run a compiled algorithm. Returns {score, canonical, notes, ms}: the JSON score as
 * generate returned it, its canonical form (validated) and the note count.
 */
function run(compiled, values, input) {
  const start = Date.now();
  const seedSpec = compiled.specs.find((s) => s.type === "seed");
  compiled.state.seed = seedSpec ? (values[seedSpec.name] !== undefined ? values[seedSpec.name] : seedSpec.default) : 0;
  compiled.state.streams = new Map();
  let result;
  try {
    result = compiled.generate(prepare(compiled.specs, values), input ? clone(input) : null);
  } catch (e) {
    if (e instanceof AlgoError || e instanceof S.ScoreError) throw e;
    throw new AlgoError(`error in generate: ${e.message}`, lineOf(e));
  }
  if (result === undefined || result === null) {
    throw new AlgoError("generate() returned nothing: it must end with return s; (the score)");
  }
  let canonical;
  try {
    canonical = S.normalizeScore(result);
  } catch (e) {
    if (e instanceof S.ScoreError) throw new AlgoError(`the score is not valid: ${e.message}`);
    throw e;
  }
  return { score: clone(result), canonical, notes: S.countNotes(canonical), ms: Date.now() - start };
}

module.exports = {
  AlgoError, LIBRARY, TYPES, RESERVED,
  // the library, also usable directly from Node
  SEMITONE, QUARTERTONE, OCTAVE, MIDDLE_C, SECOND,
  score, Score, Voice, makeRandom,
  lerp, clamp, rescale, wrap, fold, snap, seq, linspace, sum, accumulate, env, warp,
  iterate, walk, markov, rewrite, automaton, euclid,
  // the loader
  compile, run, prepare, normalizeParams, defaults, coerce, valueAtoms, describe, clone,
};
