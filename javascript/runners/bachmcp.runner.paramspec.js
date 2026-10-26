/*
bachmcp.runner.paramspec.js
---------------------
The parameters of an algorithm file: the declarations it makes (const params = {...})
completed and checked, the values that arrive from Max coerced to them, and the
lines that describe them to the model and to the panel, and the values an
algorithm receives (prepare). Used by the loader
(bachmcp.runner.loader.js), the runners (runners/) and the check before Max.
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

const { MIN_CENTS, MAX_CENTS, fmt, nameToCents } = need("bachmcp.lib.units.js");
const { AlgoError, isObject, isNumber } = need("bachmcp.lib.base.js");
const { clamp, env } = need("bachmcp.lib.numbers.js");
const { copy } = need("bachmcp.lib.build.js");

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
// Messages the runners answer themselves; a parameter cannot take these names.
const RESERVED = [
  "load", "reload", "run", "bang", "auto", "watch", "setname", "remote", "input", "values",
  "getstate", "open", "edit", "dictionary", "list", "int", "float", "anything", "loadbang",
  "save", "notifydeleted", "compile", "autowatch", "wclose", "setprop", "getprop", "delprop",
  "msg_int", "msg_float", "set", "spec", "status", "clear", "done", "capture", "sourcemode", "roll", "source",
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

// What a number parameter is, read from its unit and range, so that the panel can show
// and snap it well without the algorithm saying more: a pitch (midicents, always the
// whole MIDI range), an interval (midicents with a sign, or a small span), a time, or a
// plain number. `grid` is where a drag snaps to; `step` stays the finest resolution.
const PITCH_UNITS = ["mc", "midicent", "midicents", "cent", "cents", "pitch"];
const TIME_UNITS = { ms: "ms", msec: "ms", millisecond: "ms", milliseconds: "ms", s: "s", sec: "s", seconds: "s" };
const MIDI_RANGE = [MIN_CENTS, MAX_CENTS];  // C0 to G9: all a score takes (below C0 it reads as a mistake)
const NUMBER_TYPES = ["slider", "range", "list", "curve"];

function kindOf(type, unit, range) {
  if (!NUMBER_TYPES.includes(type)) return "";
  const u = String(unit || "").toLowerCase();
  if (PITCH_UNITS.includes(u)) {
    const [lo, hi] = range;
    if (lo < 0 || (lo < 1200 && hi <= 4800)) return "interval";
    return "pitch";
  }
  return TIME_UNITS[u] ? "time" : "";
}

/** 1, 2 or 5 times a power of ten, near a hundredth of the span. */
function niceGrid(span) {
  const raw = span / 100;
  const ten = Math.pow(10, Math.floor(Math.log10(raw)));
  const m = raw / ten;
  return decimals((m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * ten);
}

function gridOf(spec, declaredStep) {
  if (!spec.range) return 0;
  if (declaredStep > 0) return declaredStep;
  if (spec.kind === "pitch" || spec.kind === "interval") return 100;
  const grid = niceGrid(spec.range[1] - spec.range[0]);
  return spec.step > 0 ? Math.max(spec.step, Math.round(grid / spec.step) * spec.step) : grid;
}

/** Ranges that make sense for their kind: a pitch spans all of MIDI, a time is never negative. */
function capRange(type, kind, range, name) {
  if (kind === "pitch") return MIDI_RANGE.slice();
  if (kind === "time" && range[0] < 0) {
    if (range[1] <= 0) throw new AlgoError(`params.${name}: a time cannot be negative; "range" must end above 0`);
    return [0, range[1]];
  }
  return range;
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
  if (NUMBER_TYPES.includes(type) && s.range !== undefined) {
    const declared = rangeOf(s.range, name);
    spec.kind = kindOf(type, spec.unit, declared);
    if (PITCH_UNITS.includes(String(spec.unit || "").toLowerCase())) spec.unit = "mc";
    s.range = capRange(type, spec.kind, declared, name);
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
  if (spec.range && spec.step > spec.range[1] - spec.range[0]) spec.step = 0;
  if (spec.kind !== undefined) spec.grid = gridOf(spec, s.step);
  spec.default = copy(spec.value);
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

/** The default value of every parameter, by name. */
function defaults(specs) {
  const out = {};
  for (const s of specs) out[s.name] = copy(s.default);
  return out;
}

/** The values an algorithm receives as `p`: a copy of each value; a curve becomes a function of 0..1. */
function prepare(specs, values) {
  const p = {};
  for (const s of specs) {
    const v = copy(values[s.name] === undefined ? s.default : values[s.name]);
    p[s.name] = s.type === "curve" ? env(v) : v;
  }
  return p;
}

/** A value arriving as Max atoms (from the panel or a message box) -> the parameter's value. */
function coerce(spec, atoms) {
  // a pitch parameter also takes names: "target E4", "register C2 G6"
  const nums = atoms.map((a) => (spec.kind === "pitch" && typeof a === "string" && isNaN(Number(a))
    ? (nameToCents(a) === null ? NaN : nameToCents(a)) : Number(a)));
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
    const span = s.range ? ` ${fmt(s.range[0])}..${fmt(s.range[1])}` : "";
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

module.exports = {
  TYPES, RESERVED, MIDI_RANGE,
  normalizeParams, defaults, prepare, coerce, valueAtoms, describe,
};
