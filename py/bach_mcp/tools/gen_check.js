#!/usr/bin/env node
/*
gen_check.js — read a GenExpr file (the code of a gen~ codebox) before it reaches Max.

    node gen_check.js <file.genexpr> --type synth|fx [--params <file.json>]

There is no gen~ compiler outside Max, so nothing is run here: the file is parsed and
checked against what gen~ accepts. The rules are gen~'s own or stricter, never looser:
a file that passes should compile; what gen~ would refuse is named with its line.

    syntax        statements, expressions, declarations, functions, if / for / while
    names         every operator exists in gen~ (OPERATORS, from Max's reference pages) and
                  gets a number of arguments and attributes it takes; every variable is set
                  before it is read; History, Delay, Data and Buffer are used as what they are
    the file      opens with a // comment (what it does); every inlet and outlet it uses is
                  described (// in1: ..., // out1: ...); outlets are numbered without gaps
    parameters    --params: the panel's declarations (the same spec as an algorithm's
                  const params, as JSON). Each one is a Param of the code and each Param is
                  one of them, with the same default (a toggle 0 or 1, a menu the index of
                  its option)

Prints one JSON line:
    {"ok": true, "type": "synth", "description": "...", "inlets": [{"index": 1, "about": "..."}],
     "outlets": [...], "params": [...specs], "describe": [...], "buffers": [{"name", "buffer"}],
     "data": [...], "warnings": [...]}
    {"ok": false, "error": "...", "line": n}
*/
"use strict";

const fs = require("fs");
const path = require("path");

const JS = path.join(__dirname, "..", "..", "..", "javascript");
const paramspec = require(path.join(JS, "runners", "bachmcp.runner.paramspec.js"));

class GenError extends Error {
  constructor(message, line) {
    super(message);
    this.line = line || 0;
  }
}

// ── What gen~ has ──────────────────────────────────────────────────────────── //

const INTERP = ["none", "step", "linear", "cosine", "cubic", "fastcubic", "spline", "spline6"];
const BOUND = ["ignore", "clamp", "clip", "wrap", "fold", "mirror"];
const INDEX = ["samples", "phase", "lookup", "signal", "wave"];
const READ_ATTRS = { index: INDEX, interp: INTERP, boundmode: BOUND, channelmode: BOUND, channels: "number" };
const WRITE_ATTRS = { index: ["samples", "phase", "lookup", "signal"], boundmode: BOUND, channelmode: BOUND,
                      overdubmode: ["accum", "mix"] };
const ACCUM_ATTRS = { init: "number", min: "number", max: "number", resetmode: ["pre", "post"] };
const INIT = { init: "number" };

// name: [fewest arguments, most arguments, attributes, "data" when the first argument is a Data or Buffer]
const OPERATORS = {};
function op(names, min, max, attrs, first) {
  for (const name of names.split(" ")) OPERATORS[name] = { min, max, attrs: attrs || {}, first: first || "" };
}
op("abs acos acosh asin asinh atan atanh bool ceil cos cosh degrees exp exp2 fastcos fastexp fastsin fasttan " +
   "floor fract ln log log10 log2 neg not radians sign sin sinh sqrt tan tanh trunc float int f i pass " +
   "atodb dbtoa mstosamps sampstoms t60 t60time fixdenorm fixnan isdenorm isnan dcblock phasewrap", 1, 1);
op("absdiff add sub mul div mod rsub rdiv rmod and or xor eq neq gt gte lt lte eqp neqp gtp gtep ltp ltep " +
   "max maximum min minimum pow fastpow atan2 hypot step", 2, 2);
op("cartopol poltocar", 2, 2);
op("clamp clip fold wrap", 1, 3);
op("scale", 1, 6);
op("mix smoothstep switch", 3, 3);
op("selector", 2, 64);
op("gate", 2, 2, { choices: "number" });
op("noise", 0, 0);
op("cycle", 1, 2, { index: ["freq", "phase"] });
op("phasor", 1, 2, { phase: "number" });
op("train", 1, 3, { phase: "number" });
op("triangle", 1, 2);
op("rate", 2, 2, { sync: ["off", "lock", "cycle"] });
op("delta change", 1, 1, INIT);
op("latch", 2, 2, INIT);
op("sah", 2, 3, INIT);
op("slide", 1, 3, INIT);
op("accum plusequals mulequals", 1, 2, ACCUM_ATTRS);
op("counter", 0, 3, INIT);
op("mtof ftom", 1, 2);
op("interp", 3, 7, { mode: INTERP });
op("round", 1, 2, { mode: ["nearest", "floor", "ceil", "trunc"] });
op("elapsed voice voicecount mc_channel mc_channelcount", 0, 0);
op("peek sample nearest lookup", 2, 3, READ_ATTRS, "data");
op("wave", 2, 5, READ_ATTRS, "data");
op("poke splat", 3, 5, WRITE_ATTRS, "data");
op("dim channels", 1, 1, {}, "data");

const CONSTANTS = ["pi", "twopi", "halfpi", "invpi", "degtorad", "radtodeg", "e", "ln2", "ln10", "log2e", "log10e",
                   "sqrt2", "sqrt1_2", "phi", "samplerate", "vectorsize", "fftsize", "ffthop", "fftoffset", "fftfullspect"];
const CONSTANT_NAMES = new Set([...CONSTANTS, ...CONSTANTS.map((c) => c.toUpperCase())]);
const GLOBALS = new Set(["elapsed", "voice", "voicecount", "mc_channel", "mc_channelcount"]);  // read with or without ()

const DECLARATIONS = { Param: "param", History: "history", Delay: "delay", Data: "data", Buffer: "buffer" };
const DECLARATION_ATTRS = {
  Param: { min: "number", max: "number", default: "number" },
  History: {},
  Delay: { interp: INTERP, feedback: "number" },
  Data: {},
  Buffer: {},
};
const KEYWORDS = new Set(["if", "else", "for", "while", "break", "continue", "return", "require"]);

// What a model used to other languages writes, and what gen~ has instead.
const NOT_GENEXPR = {
  var: "variables are not declared: write `x = 1;`", let: "variables are not declared: write `x = 1;`",
  const: "variables are not declared: write `x = 1;`", float: "variables have no type: write `x = 1;` (float(x) is an operator)",
  double: "variables have no type: write `x = 1;`", function: "a function is written `name(a, b) { ... return x; }`, without a keyword",
  true: "there is no true: write 1", false: "there is no false: write 0",
  null: "there is no null: write 0", undefined: "there is no undefined: write 0",
  do: "there is no do: write while (...) { ... }",
  param: "a parameter is declared `Param name(default);`", history: "a memory is declared `History name(0);`",
  delay: "a delay line is declared `Delay name(samples);`", data: "a table is declared `Data name(length);`",
  buffer: "a buffer is declared `Buffer name(\"buffer_name\");`",
};
const NO_SUCH_OPERATOR = {
  saw: "a sawtooth is `phasor(freq) * 2 - 1`", sawtooth: "a sawtooth is `phasor(freq) * 2 - 1`",
  rect: "a square wave is `phasor(freq) < width ? 1 : -1`", square: "a square wave is `phasor(freq) < 0.5 ? 1 : -1`",
  pulse: "a pulse is `phasor(freq) < width`", tri: "a triangle is `triangle(phasor(freq)) * 2 - 1`",
  sine: "a sine is `cycle(freq)`", osc: "a sine is `cycle(freq)`", sinosc: "a sine is `cycle(freq)`",
  random: "`noise()` gives a new random value from -1 to 1 at every sample; hold one with `latch(noise(), trigger)`",
  rand: "`noise()` gives a new random value from -1 to 1 at every sample; hold one with `latch(noise(), trigger)`",
  pink: "there is no pink noise: filter `noise()`", white: "white noise is `noise()`",
  lowpass: "there are no ready filters: write one with History (y = mix(x, y, coeff))",
  highpass: "there are no ready filters: write one with History", bandpass: "there are no ready filters: write one with History",
  lpf: "there are no ready filters: write one with History", hpf: "there are no ready filters: write one with History",
  onepole: "there is no onepole: `History y(0); y = mix(x, y, coeff);`", biquad: "there is no biquad: write its difference equation with History",
  svf: "there is no svf: write it with History", filter: "there are no ready filters: write one with History",
  reson: "there is no reson: write it with History", allpass: "there is no allpass: write it with Delay",
  comb: "there is no comb: write it with Delay", tapin: "a delay line is `Delay d(samples); d.write(x); y = d.read(time);`",
  tapout: "a delay line is `Delay d(samples); d.write(x); y = d.read(time);`",
  adsr: "there is no adsr: write the envelope with History, or follow the gate with slide()",
  line: "there is no line: smooth with slide(x, up, down)", env: "there is no envelope operator: write it with History or slide()",
  sig: "every value is already a signal", snapshot: "there are no messages in gen~", print: "there is no printing in gen~",
  post: "there is no printing in gen~", lerp: "linear interpolation is `mix(a, b, t)`",
  map: "rescaling is `scale(x, inlo, inhi, outlo, outhi)`", rescale: "rescaling is `scale(x, inlo, inhi, outlo, outhi)`",
  saturate: "soft clipping is `tanh(x)`", sinc: "there is no sinc: write `x == 0 ? 1 : sin(x) / x`",
  sr: "the sample rate is `samplerate`", mstosamp: "it is `mstosamps`", samptoms: "it is `sampstoms`",
  midi2freq: "it is `mtof`", mtf: "it is `mtof`", db2a: "it is `dbtoa`", a2db: "it is `atodb`", dbtoamp: "it is `dbtoa`",
  ifelse: "a choice is `cond ? a : b`", select: "a choice among several is `selector(n, a, b, c)` (n from 1)",
  history: "a memory is declared `History name(0);` and then read and assigned by its name",
  delay: "a delay line is declared `Delay d(samples);` then `d.write(x); y = d.read(time);`",
  buffer: "a buffer is declared `Buffer name(\"buffer_name\");` and read with peek / sample / wave",
  data: "a table is declared `Data name(length);` and read with peek, written with poke",
  param: "a parameter is declared `Param name(default);` and read by its name",
  length: "the length of a Data or Buffer is `dim(name)`", size: "the length of a Data or Buffer is `dim(name)`",
  read: "read is a Delay's: `d.read(time)`. A Data or Buffer is read with peek / sample / wave",
  write: "write is a Delay's: `d.write(x)`. A Data or Buffer is written with poke",
};

// ── Tokens ─────────────────────────────────────────────────────────────────── //

const PUNCTUATION = ["==", "!=", "<=", ">=", "&&", "||", "^^", "+=", "-=", "*=", "/=", "%=", "++", "--", "<<", ">>",
                     "+", "-", "*", "/", "%", "<", ">", "=", "!", "?", ":", ",", ";", "(", ")", "{", "}", ".",
                     "[", "]", "&", "|", "^", "~", "@", "#", "'"];

function tokenize(text) {
  const tokens = [];
  const comments = [];  // {line, text}
  let i = 0;
  let line = 1;
  const n = text.length;
  while (i < n) {
    const c = text[i];
    if (c === "\n") { line++; i++; continue; }
    if (c === " " || c === "\t" || c === "\r") { i++; continue; }
    if (c === "/" && text[i + 1] === "/") {
      let j = i;
      while (j < n && text[j] !== "\n") j++;
      comments.push({ line, text: text.slice(i + 2, j).trim() });
      i = j;
      continue;
    }
    if (c === "/" && text[i + 1] === "*") {
      const end = text.indexOf("*/", i + 2);
      if (end < 0) throw new GenError("a /* comment is never closed with */", line);
      const body = text.slice(i + 2, end);
      body.split("\n").forEach((part, k) => comments.push({ line: line + k, text: part.replace(/^\s*\*?\s*/, "").trim() }));
      line += body.split("\n").length - 1;
      i = end + 2;
      continue;
    }
    if (c === '"') {
      let j = i + 1;
      while (j < n && text[j] !== '"' && text[j] !== "\n") j++;
      if (text[j] !== '"') throw new GenError('a " string is never closed', line);
      tokens.push({ type: "string", value: text.slice(i + 1, j), line });
      i = j + 1;
      continue;
    }
    const number = /^(?:\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)/.exec(text.slice(i, i + 40));
    if (number) {
      const after = text[i + number[0].length] || "";
      if (/[A-Za-z_]/.test(after)) {
        throw new GenError(`"${number[0]}${after}..." is not a number: write it without a suffix (1.5, not 1.5f), ` +
                           "and start names with a letter", line);
      }
      tokens.push({ type: "number", value: Number(number[0]), text: number[0], line });
      i += number[0].length;
      continue;
    }
    const word = /^[A-Za-z_][A-Za-z0-9_]*/.exec(text.slice(i, i + 80));
    if (word) {
      tokens.push({ type: "name", value: word[0], line });
      i += word[0].length;
      continue;
    }
    const mark = PUNCTUATION.find((p) => text.startsWith(p, i));
    if (!mark) throw new GenError(`the character ${JSON.stringify(c)} is not GenExpr`, line);
    tokens.push({ type: "mark", value: mark, line });
    i += mark.length;
  }
  tokens.push({ type: "end", value: "end of the file", line });
  return { tokens, comments };
}

// ── The parser, which checks as it reads ───────────────────────────────────── //

function io(name) {
  const m = /^(in|out)(\d*)$/.exec(name);
  if (!m) return null;
  if (m[2] !== "" && (Number(m[2]) < 1 || m[2].startsWith("0"))) return null;
  return { way: m[1], index: m[2] === "" ? 1 : Number(m[2]) };
}

class Scope {
  constructor(parent, isFunction) {
    this.parent = parent;
    this.names = new Map();  // name -> kind
    this.isFunction = Boolean(isFunction);
  }
  find(name) {
    for (let s = this; s; s = s.parent) {
      if (s.names.has(name)) return s.names.get(name);
      if (s.isFunction) break;  // a function sees only what is its own
    }
    return null;
  }
  set(name, kind) { this.names.set(name, kind); }
}

class Parser {
  constructor(text) {
    const { tokens, comments } = tokenize(text);
    this.tokens = tokens;
    this.comments = comments;
    this.pos = 0;
    this.functions = new Map();  // name -> {args, attrs}
    this.inlets = new Set();
    this.outlets = new Set();
    this.params = [];    // {name, default, min, max, line}
    this.buffers = [];   // {name, buffer}
    this.data = [];
    this.called = new Map();   // operator names called -> line
    this.variables = new Map();  // variable names set in the main body -> line
    this.loops = 0;
    this.inFunction = false;
    this.constantOf = "";  // while a value that must be known at compile time is read: whose
  }

  get tok() { return this.tokens[this.pos]; }
  peek(k = 1) { return this.tokens[Math.min(this.pos + k, this.tokens.length - 1)]; }
  is(value, type = "mark") { return this.tok.type === type && this.tok.value === value; }
  take(value) {
    if (this.is(value)) { this.pos++; return true; }
    return false;
  }
  shown(tok) {
    if (tok.type === "end") return "the end of the file";
    return tok.type === "string" ? `"${tok.value}"` : `\`${tok.type === "number" ? tok.text : tok.value}\``;
  }
  expect(value, why) {
    if (this.take(value)) return;
    const before = this.tokens[Math.max(this.pos - 1, 0)];
    if (value === ";") {
      throw new GenError(`a ; is missing ${why || "at the end of the statement"} (before ${this.shown(this.tok)}). ` +
                         "Every statement ends with ;", before.line);
    }
    throw new GenError(`expected \`${value}\` ${why || ""} but found ${this.shown(this.tok)}`.replace("  ", " "), this.tok.line);
  }
  fail(message, tok) { throw new GenError(message, (tok || this.tok).line); }

  // program: functions, then declarations, then statements
  program() {
    const scope = new Scope(null, false);
    while (this.tok.type === "name" && this.tok.value === "require") {
      this.fail("there are no libraries to require: write the functions you need in this file");
    }
    while (this.atFunction()) this.functionDefinition();
    this.body(scope, false);
    if (this.tok.type !== "end") {
      if (this.is("}")) this.fail("a } closes nothing here");
      this.fail(`unexpected ${this.shown(this.tok)}`);
    }
    return scope;
  }

  atFunction() {
    if (this.tok.type !== "name" || !(this.peek().type === "mark" && this.peek().value === "(")) return false;
    let depth = 0;
    for (let k = this.pos + 1; k < this.tokens.length; k++) {
      const t = this.tokens[k];
      if (t.type !== "mark") continue;
      if (t.value === "(") depth++;
      else if (t.value === ")" && --depth === 0) {
        const next = this.tokens[k + 1];
        return next.type === "mark" && next.value === "{" && !KEYWORDS.has(this.tok.value);
      } else if (t.value === ";" || t.value === "{" || t.value === "}") return false;
    }
    return false;
  }

  functionDefinition() {
    const name = this.tok;
    this.pos++;
    if (OPERATORS[name.value] || DECLARATIONS[name.value]) {
      this.fail(`a function cannot be named ${name.value}: gen~ already has it. Choose another name`, name);
    }
    if (this.functions.has(name.value)) this.fail(`the function ${name.value} is defined twice`, name);
    if (io(name.value) || CONSTANT_NAMES.has(name.value)) this.fail(`a function cannot be named ${name.value}`, name);
    this.expect("(");
    const scope = new Scope(null, true);
    const args = [];
    const attrs = [];
    while (!this.is(")")) {
      if (this.tok.type !== "name") this.fail(`the arguments of ${name.value} are names: ${name.value}(a, b) { ... }`);
      const arg = this.tok;
      this.pos++;
      if (io(arg.value)) this.fail(`an argument cannot be named ${arg.value}: that is an inlet or outlet of the codebox`, arg);
      if (this.take("=")) {  // an attribute with its default
        this.constant(`the default of ${arg.value}`);
        attrs.push(arg.value);
      } else {
        args.push(arg.value);
      }
      scope.set(arg.value, "arg");
      if (!this.take(",")) break;
    }
    this.expect(")", `after the arguments of ${name.value}`);
    this.expect("{");
    const def = { args: args.length, attrs, line: name.line };
    const previous = this.inFunction;
    this.inFunction = name.value;
    this.body(scope, true, def);
    this.inFunction = previous;
    this.expect("}", `to close the function ${name.value}`);
    this.functions.set(name.value, def);  // after its body: a function cannot call itself
  }

  // declarations first, then statements
  body(scope, inFunction, def) {
    let statements = false;
    while (this.tok.type !== "end" && !this.is("}")) {
      if (this.tok.type === "name" && DECLARATIONS[this.tok.value] && this.peek().type === "name") {
        if (statements) {
          this.fail(`${this.tok.value} ${this.peek().value} comes after the first statement: ` +
                    "declare every Param, History, Delay, Data and Buffer before the code that uses them");
        }
        this.declaration(scope, inFunction, def);
        continue;
      }
      if (!inFunction && this.atFunction()) {
        this.fail(`the function ${this.tok.value} comes after other code: define every function at the top of the file`);
      }
      statements = true;
      this.statement(scope);
    }
  }

  declaration(scope, inFunction, def) {
    const type = this.tok.value;
    const kind = DECLARATIONS[type];
    this.pos++;
    do {
      const name = this.tok;
      if (name.type !== "name") this.fail(`${type} needs a name: ${type} name(...);`);
      this.pos++;
      if (io(name.value)) this.fail(`${type} cannot be named ${name.value}: that is an inlet or outlet`, name);
      if (CONSTANT_NAMES.has(name.value)) this.fail(`${type} cannot be named ${name.value}: that is a constant of gen~`, name);
      if (KEYWORDS.has(name.value) || DECLARATIONS[name.value]) this.fail(`${type} cannot be named ${name.value}`, name);
      if (scope.names.has(name.value)) this.fail(`${name.value} is declared twice`, name);
      const args = [];
      const attrs = {};
      if (this.take("(")) {
        while (!this.is(")")) {
          if (this.tok.type === "name" && this.peek().type === "mark" && this.peek().value === "=") {
            const key = this.tok.value;
            this.pos += 2;
            const allowed = DECLARATION_ATTRS[type];
            if (!(key in allowed)) {
              this.fail(`${type} ${name.value}: no attribute ${key}` +
                        (Object.keys(allowed).length ? ` (it has: ${Object.keys(allowed).join(", ")})` : ""));
            }
            attrs[key] = this.attributeValue(`${type} ${name.value}`, key, allowed[key]);
          } else if (this.tok.type === "string") {
            args.push(this.tok.value);
            this.pos++;
          } else {
            args.push(this.constant(`${type} ${name.value}`));
          }
          if (!this.take(",")) break;
        }
        this.expect(")", `to close ${type} ${name.value}(`);
      }
      this.declared(type, name, args, attrs, inFunction, def);
      scope.set(name.value, kind);
    } while (this.take(","));
    this.expect(";", `after ${type}`);
  }

  declared(type, name, args, attrs, inFunction, def) {
    const numbers = args.every((a) => typeof a !== "string");
    if (type === "Param") {
      if (args.length > 1 || !numbers) this.fail(`Param ${name.value}: write Param ${name.value}(default);`, name);
      if (inFunction) {
        def.attrs.push(name.value);  // inside a function a Param is an attribute of the function
        return;
      }
      const value = args.length ? args[0] : attrs.default;
      this.params.push({ name: name.value, default: typeof value === "number" ? value : null,
                         min: attrs.min, max: attrs.max, line: name.line });
    } else if (type === "History") {
      if (args.length > 1 || !numbers) this.fail(`History ${name.value}: write History ${name.value}(0); with its first value`, name);
    } else if (type === "Delay") {
      if (args.length > 2 || !numbers) {
        this.fail(`Delay ${name.value}: write Delay ${name.value}(samples); with its longest time in samples, e.g. Delay ${name.value}(samplerate);`, name);
      }
    } else if (type === "Data") {
      if (args.length > 2 || !numbers) {
        this.fail(`Data ${name.value}: write Data ${name.value}(length); or Data ${name.value}(length, channels);`, name);
      }
      this.data.push(name.value);
    } else if (type === "Buffer") {
      if (args.length > 1 || (args.length === 1 && typeof args[0] !== "string")) {
        this.fail(`Buffer ${name.value}: write Buffer ${name.value}("${name.value}"); with the name of the buffer~ in Max, in quotes`, name);
      }
      const buffer = args.length ? args[0] : name.value;
      if (!/^[A-Za-z_][A-Za-z0-9_.\-]*$/.test(buffer)) {
        this.fail(`Buffer ${name.value}: "${buffer}" cannot name a buffer~. Use letters, digits and _`, name);
      }
      this.buffers.push({ name: name.value, buffer });
    }
  }

  // A value known when the code is compiled: numbers, constants, + - * / ( ) and operators on them.
  constant(where) {
    const start = this.pos;
    const scope = new Scope(null, true);
    let value = null;
    const outer = this.constantOf;
    this.constantOf = where;
    this.expression(scope);
    this.constantOf = outer;
    const tokens = this.tokens.slice(start, this.pos);
    if (tokens.length === 1 && tokens[0].type === "number") value = tokens[0].value;
    if (tokens.length === 2 && tokens[0].value === "-" && tokens[1].type === "number") value = -tokens[1].value;
    return value;  // a number when it is plain, else null (a formula)
  }

  attributeValue(where, key, allowed) {
    const tok = this.tok;
    if (Array.isArray(allowed)) {
      if (tok.type !== "string" && tok.type !== "name") {
        this.fail(`${where}: ${key} is one of ${allowed.map((a) => `"${a}"`).join(", ")}`);
      }
      this.pos++;
      if (!allowed.includes(tok.value)) {
        this.fail(`${where}: ${key}="${tok.value}" does not exist. It is one of ${allowed.map((a) => `"${a}"`).join(", ")}`, tok);
      }
      return tok.value;
    }
    if (tok.type === "string") this.fail(`${where}: ${key} is a number, not a string`);
    const value = this.constant(`${where}: ${key}`);
    return value;
  }

  block(scope) {
    const inner = new Scope(scope, false);
    if (this.take("{")) {
      while (!this.is("}")) {
        if (this.tok.type === "end") this.fail("a { is never closed with }");
        if (this.tok.type === "name" && DECLARATIONS[this.tok.value] && this.peek().type === "name") {
          this.fail(`${this.tok.value} ${this.peek().value} is declared inside a block: declare it at the top, before the first statement`);
        }
        this.statement(inner);
      }
      this.pos++;
    } else {
      this.statement(inner);
    }
  }

  statement(scope) {
    const tok = this.tok;
    if (tok.type === "mark" && tok.value === ";") { this.pos++; return; }
    if (tok.type === "mark" && tok.value === "{") { this.block(scope); return; }
    if (tok.type === "name") {
      if (NOT_GENEXPR[tok.value] && this.peek().type === "name") {
        this.fail(`\`${tok.value} ${this.peek().value}\` is not GenExpr: ${NOT_GENEXPR[tok.value]}`);
      }
      if (tok.value === "int" && this.peek().type === "name") {
        this.fail("`int` is not a declaration: variables have no type, write `x = 1;`");
      }
      if (tok.value === "if") return this.ifStatement(scope);
      if (tok.value === "else") this.fail("this else has no if before it");
      if (tok.value === "while") {
        this.pos++;
        this.expect("(", "after while");
        this.expression(scope);
        this.expect(")", "to close the condition of while");
        this.loops++;
        this.block(scope);
        this.loops--;
        return;
      }
      if (tok.value === "for") return this.forStatement(scope);
      if (tok.value === "break" || tok.value === "continue") {
        if (!this.loops) this.fail(`${tok.value} is outside a loop`);
        this.pos++;
        this.expect(";", `after ${tok.value}`);
        return;
      }
      if (tok.value === "return") {
        if (!this.inFunction) this.fail("return is for functions. The codebox answers by assigning its outlets: out1 = ...;");
        this.pos++;
        if (!this.is(";")) this.expressionList(scope);
        this.expect(";", "after return");
        return;
      }
      if (tok.value === "require") this.fail("there are no libraries to require: write the functions you need in this file");
    }
    this.simple(scope);
    this.expect(";");
  }

  ifStatement(scope) {
    this.pos++;
    this.expect("(", "after if");
    this.expression(scope);
    this.expect(")", "to close the condition of if");
    this.block(scope);
    if (this.tok.type === "name" && this.tok.value === "else") {
      this.pos++;
      if (this.tok.type === "name" && this.tok.value === "if") this.ifStatement(scope);
      else this.block(scope);
    }
  }

  forStatement(scope) {
    this.pos++;
    this.expect("(", "after for");
    const inner = new Scope(scope, false);
    if (!this.is(";")) this.simple(inner);
    this.expect(";", "after the start of the for");
    if (!this.is(";")) this.expression(inner);
    this.expect(";", "after the condition of the for");
    if (!this.is(")")) this.simple(inner);
    this.expect(")", "to close the for");
    this.loops++;
    this.block(inner);
    this.loops--;
  }

  // an assignment, or a call made for what it does (poke, splat, d.write)
  simple(scope) {
    const targets = this.targets();
    if (targets) {
      const { names, operator } = targets;
      if (operator !== "=") {
        if (names.length > 1) this.fail(`${operator} takes one name on its left`, names[0]);
        this.read(scope, names[0]);
      }
      this.expressionList(scope);
      for (const name of names) this.assign(scope, name);
      return;
    }
    const start = this.tok;
    if (start.type === "name" && this.peek().type === "mark" && (this.peek().value === "++" || this.peek().value === "--")) {
      this.fail(`there is no ${this.peek().value} in GenExpr: write ${start.value} ${this.peek().value[0]}= 1`);
    }
    if (start.type === "mark" && (start.value === "++" || start.value === "--")) {
      this.fail(`there is no ${start.value} in GenExpr: write x ${start.value[0]}= 1`);
    }
    const before = this.pos;
    this.expression(scope);
    const first = this.tokens[before];
    const call = first.type === "name" && this.tokens[before + 1].type === "mark" &&
                 ["(", "."].includes(this.tokens[before + 1].value) && this.tokens[this.pos - 1].value === ")";
    if (!call) {
      this.fail("this line computes a value and does nothing with it: assign it (x = ...; or out1 = ...;)", first);
    }
  }

  // name (, name)* followed by an assignment operator, else null
  targets() {
    const names = [];
    let k = this.pos;
    for (;;) {
      const t = this.tokens[k];
      if (t.type !== "name") return null;
      names.push(t);
      const next = this.tokens[k + 1];
      if (next.type !== "mark") return null;
      if (next.value === ",") { k += 2; continue; }
      if (["=", "+=", "-=", "*=", "/=", "%="].includes(next.value)) {
        this.pos = k + 2;
        return { names, operator: next.value };
      }
      if (next.value === "[") {
        throw new GenError("there are no arrays in GenExpr: a table is `Data name(length);`, read with peek(name, index) " +
                           "and written with poke(name, value, index)", next.line);
      }
      return null;
    }
  }

  assign(scope, tok) {
    const name = tok.value;
    const port = io(name);
    if (port) {
      if (port.way === "in") this.fail(`${name} is an inlet: it can only be read`, tok);
      if (this.inFunction) this.fail(`${name} is set inside the function ${this.inFunction}: outlets belong to the main code. Return the value instead`, tok);
      if (port.index > 32) this.fail(`${name}: at most 32 outlets`, tok);
      this.outlets.add(port.index);
      return;
    }
    if (CONSTANT_NAMES.has(name)) this.fail(`${name} is a constant of gen~: choose another name for this variable`, tok);
    if (KEYWORDS.has(name) || DECLARATIONS[name]) this.fail(`${name} cannot be a variable name`, tok);
    if (NOT_GENEXPR[name] && ["true", "false", "null", "undefined"].includes(name)) this.fail(`${name} cannot be a variable name`, tok);
    const kind = scope.find(name);
    if (kind === "param") this.fail(`${name} is a Param: it is set from the panel and only read here. Use another variable (x = ${name} * ...;)`, tok);
    if (kind === "delay") this.fail(`${name} is a Delay: write into it with ${name}.write(x);`, tok);
    if (kind === "data" || kind === "buffer") this.fail(`${name} is a ${kind === "data" ? "Data" : "Buffer"}: write into it with poke(${name}, value, index);`, tok);
    if (!kind) scope.set(name, "var");
    if (!this.inFunction && !this.variables.has(name)) this.variables.set(name, tok.line);
  }

  read(scope, tok) {
    const name = tok.value;
    const port = io(name);
    if (this.constantOf && !CONSTANT_NAMES.has(name)) {
      this.fail(`${this.constantOf}: its value must be known when the code is compiled: a number, or a formula of ` +
                `numbers and constants (samplerate, pi ...), not ${name}`, tok);
    }
    if (port) {
      if (port.way === "out") this.fail(`${name} is an outlet: it can only be assigned. Keep the value in a variable to use it again`, tok);
      if (this.inFunction) this.fail(`${name} is read inside the function ${this.inFunction}: inlets belong to the main code. Pass the value as an argument`, tok);
      if (port.index > 32) this.fail(`${name}: at most 32 inlets`, tok);
      this.inlets.add(port.index);
      return;
    }
    if (CONSTANT_NAMES.has(name) || GLOBALS.has(name)) return;
    const kind = scope.find(name);
    if (!kind) {
      if (NOT_GENEXPR[name]) this.fail(`\`${name}\` is not GenExpr: ${NOT_GENEXPR[name]}`, tok);
      if (this.variables.has(name) && this.inFunction) {
        this.fail(`${name} belongs to the main code: the function ${this.inFunction} sees only its own arguments. Pass it as an argument`, tok);
      }
      const later = this.variables.has(name) || scope.names.has(name);
      this.fail(`${name} is not set before it is read here` +
                (later ? " (it is first set inside an if or a loop: give it a value before, e.g. " + name + " = 0;)" :
                 ". Assign it first, or declare it (Param, History)"), tok);
    }
    if (kind === "delay") this.fail(`${name} is a Delay: read it with ${name}.read(time_in_samples)`, tok);
    if (kind === "data" || kind === "buffer") {
      this.fail(`${name} is a ${kind === "data" ? "Data" : "Buffer"}, not a value: read it with peek(${name}, index), sample(${name}, phase) or dim(${name})`, tok);
    }
  }

  expressionList(scope) {
    let count = 0;
    do {
      this.expression(scope);
      count++;
    } while (this.take(","));
    return count;
  }

  expression(scope) {
    this.binary(scope, 0);
    if (this.take("?")) {
      this.expression(scope);
      this.expect(":", "in a ? : choice (cond ? a : b)");
      this.expression(scope);
    }
  }

  binary(scope, level) {
    const LEVELS = [["||"], ["&&", "^^"], ["==", "!="], ["<", "<=", ">", ">="], ["+", "-"], ["*", "/", "%"]];
    if (level === LEVELS.length) return this.unary(scope);
    this.binary(scope, level + 1);
    while (this.tok.type === "mark" && LEVELS[level].includes(this.tok.value)) {
      this.pos++;
      this.binary(scope, level + 1);
    }
    if (level === 0 && this.tok.type === "mark") {
      const v = this.tok.value;
      if (["&", "|", "^", "~", "<<", ">>"].includes(v)) {
        this.fail(`there is no ${v} in GenExpr` + (v === "&" ? ": and is &&" : v === "|" ? ": or is ||" : v === "^" ? ": a power is pow(a, b)" : ""));
      }
      if (v === "[") {
        this.fail("there are no arrays in GenExpr: a table is `Data name(length);`, read with peek(name, index) and written with poke(name, value, index)");
      }
      if (v === "++" || v === "--") this.fail(`there is no ${v} in GenExpr: write x ${v[0]}= 1`);
    }
  }

  unary(scope) {
    if (this.tok.type === "mark" && (this.tok.value === "-" || this.tok.value === "!" || this.tok.value === "+")) {
      this.pos++;
      return this.unary(scope);
    }
    return this.primary(scope);
  }

  primary(scope) {
    const tok = this.tok;
    if (tok.type === "number") { this.pos++; return; }
    if (tok.type === "string") {
      this.fail(`the string "${tok.value}" cannot be a value: strings only name a buffer~ (Buffer b("name");) or set an attribute (interp="linear")`);
    }
    if (tok.type === "mark" && tok.value === "(") {
      this.pos++;
      this.expression(scope);
      this.expect(")", "to close (");
      return;
    }
    if (tok.type !== "name") {
      this.fail(tok.type === "end" ? "the code stops in the middle of an expression" : `unexpected ${this.shown(tok)}`);
    }
    if (KEYWORDS.has(tok.value)) this.fail(`unexpected \`${tok.value}\` inside an expression`);
    this.pos++;
    if (this.is("(")) return this.call(scope, tok);
    if (this.is(".")) return this.method(scope, tok);
    this.read(scope, tok);
  }

  // positional arguments, then attributes (key="value")
  arguments(scope, where, allowed, first) {
    this.expect("(");
    let count = 0;
    const attrs = [];
    while (!this.is(")")) {
      if (this.tok.type === "name" && this.peek().type === "mark" && this.peek().value === "=" ) {
        const key = this.tok;
        this.pos += 2;
        if (allowed === null) {
          this.expression(scope);  // an attribute of a function of this file: any value
        } else if (!(key.value in allowed)) {
          const has = Object.keys(allowed);
          this.fail(`${where} has no attribute ${key.value}` + (has.length ? ` (it has: ${has.join(", ")})` : ""), key);
        } else {
          this.attributeValue(where, key.value, allowed[key.value]);
        }
        attrs.push(key.value);
      } else {
        if (attrs.length) this.fail(`${where}: attributes (${attrs[0]}=...) come after the other arguments`);
        if (count === 0 && first === "data") {
          const name = this.tok;
          const kind = name.type === "name" ? scope.find(name.value) : null;
          if (kind !== "data" && kind !== "buffer") {
            this.fail(`${where}: its first argument is the name of a Data or a Buffer declared at the top ` +
                      `(Data table(512); or Buffer source("source");)` +
                      (name.type === "name" ? `, and ${name.value} is not one` : ""), name);
          }
          this.pos++;
        } else {
          this.expression(scope);
        }
        count++;
      }
      if (!this.take(",")) break;
    }
    this.expect(")", `to close ${where}(`);
    return { count, attrs };
  }

  call(scope, tok) {
    const name = tok.value;
    const port = io(name);
    if (port) this.fail(`${name} is an ${port.way}let, not a function: write ${name} without ( )`, tok);
    if (GLOBALS.has(name) || CONSTANT_NAMES.has(name)) {
      this.expect("(");
      this.expect(")", `: ${name} takes no arguments`);
      return;
    }
    const mine = this.functions.get(name);
    if (mine) {
      const { count, attrs } = this.arguments(scope, name, null, "");
      if (count !== mine.args) {
        this.fail(`${name} is defined with ${mine.args} argument${mine.args === 1 ? "" : "s"} (line ${mine.line}) and called with ${count}`, tok);
      }
      for (const a of attrs) {
        if (!mine.attrs.includes(a)) this.fail(`${name} has no attribute ${a}`, tok);
      }
      return;
    }
    if (name === this.inFunction) this.fail(`the function ${name} calls itself: gen~ has no recursion. Use a loop`, tok);
    const known = OPERATORS[name];
    if (!known) {
      const kind = scope.find(name);
      if (kind === "delay") this.fail(`${name} is a Delay: read it with ${name}.read(time_in_samples)`, tok);
      if (kind === "history" || kind === "param" || kind === "var" || kind === "arg") {
        this.fail(`${name} is a ${kind === "var" ? "variable" : kind === "arg" ? "argument" : kind === "param" ? "Param" : "History"}, not a function: write ${name} without ( )`, tok);
      }
      if (DECLARATIONS[name]) this.fail(`${name} is a declaration: write it at the top, \`${name} name(...);\``, tok);
      const hint = NO_SUCH_OPERATOR[name] || NO_SUCH_OPERATOR[name.toLowerCase()];
      const near = !hint && nearest(name, [...Object.keys(OPERATORS), ...this.functions.keys()]);
      this.fail(`gen~ has no operator ${name}` + (hint ? `: ${hint}` : near ? `. Did you mean ${near}?` : "") +
                (hint || near ? "" : ". Use the operators listed in the skill, or define the function at the top of this file"), tok);
    }
    if (scope.find(name)) {
      this.fail(`${name} is a name of yours here and also the operator ${name}( ): rename yours (e.g. ${name}_amount)`, tok);
    }
    if (!this.called.has(name)) this.called.set(name, tok.line);
    const { count } = this.arguments(scope, name, known.attrs, known.first);
    if (count < known.min || count > known.max) {
      const takes = known.min === known.max ? `${known.min}` : `${known.min} to ${known.max}`;
      this.fail(`${name} takes ${takes} argument${known.max === 1 ? "" : "s"}, and here it gets ${count}`, tok);
    }
  }

  method(scope, tok) {
    this.pos++;  // .
    const method = this.tok;
    if (method.type !== "name") this.fail(`unexpected ${this.shown(method)} after ${tok.value}.`);
    this.pos++;
    const kind = scope.find(tok.value);
    if (kind !== "delay") {
      if (io(tok.value) || kind) {
        this.fail(`${tok.value}.${method.value}: only a Delay has .read( ) and .write( )` +
                  (kind === "data" || kind === "buffer" ? `. Read a ${kind === "data" ? "Data" : "Buffer"} with peek(${tok.value}, index) and write it with poke(${tok.value}, value, index)` : ""), tok);
      }
      this.fail(`${tok.value}.${method.value}: there are no objects in GenExpr (no Math., no this.). ` +
                "Operators are plain functions: sin(x), floor(x), min(a, b)", tok);
    }
    if (method.value === "read") {
      const { count } = this.arguments(scope, `${tok.value}.read`, { interp: INTERP }, "");
      if (count < 1) this.fail(`${tok.value}.read needs the delay time in samples: ${tok.value}.read(mstosamps(250))`, tok);
    } else if (method.value === "write") {
      const { count } = this.arguments(scope, `${tok.value}.write`, {}, "");
      if (count !== 1) this.fail(`${tok.value}.write takes the one value to delay: ${tok.value}.write(x)`, tok);
    } else {
      this.fail(`a Delay has .read(time) and .write(value), not .${method.value}`, method);
    }
  }
}

function distance(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
  }
  return d[a.length][b.length];
}

function nearest(name, names) {
  const lower = name.toLowerCase();
  let best = null;
  let score = lower.length > 4 ? 3 : 2;
  for (const candidate of names) {
    const d = candidate === lower ? 0 : distance(lower, candidate.toLowerCase());
    if (d < score) { best = candidate; score = d; }
  }
  return best;
}

// ── The file as a whole ────────────────────────────────────────────────────── //

function documented(comments, way) {
  const out = new Map();
  const pattern = new RegExp(`^${way}(\\d*)\\s*[:=\\-–—]\\s*(.+)$`);
  for (const c of comments) {
    const m = pattern.exec(c.text);
    if (m && !out.has(m[1] === "" ? 1 : Number(m[1]))) out.set(m[1] === "" ? 1 : Number(m[1]), m[2].trim());
  }
  return out;
}

function ports(used, comments, way, type) {
  const about = documented(comments, way);
  const word = way === "in" ? "inlet" : "outlet";
  const indices = [...used].sort((a, b) => a - b);
  const top = indices.length ? indices[indices.length - 1] : 0;
  for (let k = 1; k <= top; k++) {
    if (!used.has(k)) {
      throw new GenError(way === "in"
        ? `the code reads in${top} but never in${k}: number the inlets without gaps, from in1`
        : `the code sets out${top} but never out${k}: number the outlets without gaps, from out1`, 0);
    }
    if (!about.has(k)) {
      throw new GenError(`${way}${k} is not described: add a comment line "// ${way}${k}: what this ${word} ${way === "in" ? "takes" : "gives"}" ` +
                         "at the top of the file", 0);
    }
  }
  for (const k of about.keys()) {
    if (k > top) throw new GenError(`the comments describe ${way}${k}, but the code never ${way === "in" ? "reads" : "sets"} it`, 0);
  }
  if (way === "out" && !top) throw new GenError("the code sets no outlet: the sound leaves through out1 = ...; (and out2 for stereo)", 0);
  if (way === "in" && !top && type === "fx") {
    throw new GenError("an fx processes the sound that comes in: read it from in1 (and in2 for stereo), and describe it (// in1: ...)", 0);
  }
  return indices.map((index) => ({ index, about: about.get(index) }));
}

const PANEL_TYPES = ["slider", "toggle", "menu"];

function panel(declared, raw) {
  let specs;
  try {
    // a unit is a label here: "cents" must not make the panel treat the number as a pitch of the score
    for (const spec of Object.values(raw && typeof raw === "object" ? raw : {})) {
      if (spec && typeof spec === "object" && /^(mc|midicents?|cents?|pitch)$/i.test(String(spec.unit || spec.units || ""))) {
        delete spec.units;
        spec.unit = "ct";
      }
    }
    specs = paramspec.normalizeParams(raw);
  } catch (e) {
    throw new GenError(String(e.message || e).replace("const params = { ... } is missing", "params is not an object"), 0);
  }
  const byName = new Map(declared.map((p) => [p.name, p]));
  for (const spec of specs) {
    if (!PANEL_TYPES.includes(spec.type)) {
      throw new GenError(`params.${spec.name}: a gen~ parameter is one number, so its type is slider, toggle or menu, not ${spec.type}` +
                         (spec.type === "range" ? `. Declare two sliders (${spec.name}_low, ${spec.name}_high)` : ""), 0);
    }
    if (spec.type === "menu") spec.send = spec.options.findIndex((o) => String(o) === String(spec.value));
    else if (spec.type === "toggle") spec.send = spec.value ? 1 : 0;
    else spec.send = spec.value;
    const p = byName.get(spec.name);
    if (!p) {
      throw new GenError(`params.${spec.name} has no Param in the code: declare \`Param ${spec.name}(${spec.send});\` and use it, ` +
                         "or take it out of params", 0);
    }
    const same = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));
    if (p.default === null || !same(p.default, spec.send)) {
      const why = spec.type === "menu" ? ` (a menu sends the index of its option, from 0: "${spec.value}" is ${spec.send})`
                : spec.type === "toggle" ? " (a toggle sends 0 or 1)" : "";
      throw new GenError(`Param ${spec.name} starts at ${p.default === null ? "nothing" : p.default} in the code and at ${spec.send} in params${why}: ` +
                         `write \`Param ${spec.name}(${spec.send});\``, p.line);
    }
    const [lo, hi] = spec.type === "slider" ? spec.range : spec.type === "toggle" ? [0, 1] : [0, spec.options.length - 1];
    if ((typeof p.min === "number" && !same(p.min, lo)) || (typeof p.max === "number" && !same(p.max, hi))) {
      throw new GenError(`Param ${spec.name}: min and max in the code differ from params (${lo} to ${hi}). ` +
                         `Leave them out of the code: \`Param ${spec.name}(${spec.send});\``, p.line);
    }
  }
  const names = new Set(specs.map((s) => s.name));
  for (const p of declared) {
    if (!names.has(p.name)) {
      throw new GenError(`Param ${p.name} is not in params: add it there ({ type: "slider", range: [low, high], value: ${p.default === null ? 0 : p.default} }), ` +
                         "or make it a plain number in the code", p.line);
    }
  }
  return specs;
}

function check(text, type, rawParams) {
  if (!text.trim()) throw new GenError("the code is empty", 0);
  const parser = new Parser(text);
  parser.program();
  for (const [name, line] of parser.called) {
    if (parser.variables.has(name) || parser.params.some((p) => p.name === name)) {
      throw new GenError(`${name} is used both as a name of yours and as the operator ${name}( ): rename your ` +
                         `${parser.variables.has(name) ? "variable" : "Param"} (e.g. ${name}_amount)`, parser.variables.get(name) || line);
    }
  }
  const first = text.trimStart();
  const opens = first.startsWith("//") || first.startsWith("/*");
  const description = opens && parser.comments.length ? parser.comments[0].text : "";
  if (!description || /^(in|out)\d*\s*[:=\-–—]/.test(description)) {
    throw new GenError("the file must open with a // comment: what it does, in one line of plain words (shown above its panel)", 1);
  }
  const inlets = ports(parser.inlets, parser.comments, "in", type);
  const outlets = ports(parser.outlets, parser.comments, "out", type);
  const specs = panel(parser.params, rawParams);
  const warnings = [];
  if (outlets.length === 1) warnings.push("one outlet: the sound is mono");
  return {
    ok: true, type, description, inlets, outlets,
    params: specs, describe: paramspec.describe(specs),
    buffers: parser.buffers, data: parser.data, warnings,
  };
}

function main() {
  const args = process.argv.slice(2);
  const file = args[0];
  const option = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : "");
  const type = option("--type") || "synth";
  let result;
  try {
    const text = fs.readFileSync(file, "utf8");
    const paramsFile = option("--params");
    const raw = paramsFile ? JSON.parse(fs.readFileSync(paramsFile, "utf8")) : {};
    result = check(text, type, raw);
  } catch (e) {
    if (!(e instanceof GenError)) throw e;
    result = { ok: false, error: e.message, line: e.line };
  }
  process.stdout.write(JSON.stringify(result) + "\n");
}

if (require.main === module) main();

module.exports = { check, tokenize, OPERATORS, GenError };
