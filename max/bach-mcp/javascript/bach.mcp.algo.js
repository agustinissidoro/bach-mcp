/*
bach.mcp.algo.js — the runner (v8). Lives inside the bach.mcp.algo abstraction.

Loads an algorithm file (see bach.mcp.core.js), runs it, and sends:
  outlet 0  dictionary <name>         the JSON score, for bach.mcp.translate
  outlet 1  spec / set / status ...   the panel (bach.mcp.params)
  outlet 2  loaded / done / error     what happened, for the patch and the MCP server

Messages:
  load <path>          load and run a file (absolute path, or a name in the search path)
  reload               read the file again
  run, bang            run with the current values
  <param> <value...>   set a parameter, e.g. "times 32", "register 4800 8400"
  auto 0/1             run on every parameter change (default 1)
  watch 0/1            reload when the file changes on disk (default 1)
  input dictionary <n> the score arriving at the right inlet (`p`, `input`)
  remote <runner> <message...>  a message from the MCP server: acted on when <runner> is this name
*/
"use strict";

autowatch = 1;
inlets = 1;
outlets = 3;

const core = (function () {
  try {
    return require("bach.mcp.core.js");
  } catch (e) {
    return require("./bach.mcp.core.js");
  }
})();

let runner = "algo";
let source = "";
let text = "";
let compiled = null;
let values = {};
let inputScore = null;
let autorun = true;
let watching = true;
let freshLoad = false;

const scoreDict = new Dict();
const pending = new Task(runNow, this);
const watcher = new Task(checkFile, this);
watcher.interval = 1000;

try {
  setinletassist(0, "load <path>, run, <param> <value>, input dictionary <name>");
  setoutletassist(0, "dictionary: the JSON score (to bach.mcp.translate)");
  setoutletassist(1, "to bach.mcp.params");
  setoutletassist(2, "loaded / done / error");
} catch (e) {
  // assist strings are optional
}

// ── Reading the file ────────────────────────────────────────────────────── //

function utf8(bytes) {
  let out = "";
  for (let i = 0; i < bytes.length; i++) {
    const b = bytes[i] & 255;
    if (b < 0x80) {
      out += String.fromCharCode(b);
    } else if (b >= 0xc0 && b < 0xe0 && i + 1 < bytes.length) {
      out += String.fromCharCode(((b & 0x1f) << 6) | (bytes[++i] & 0x3f));
    } else if (b >= 0xe0 && b < 0xf0 && i + 2 < bytes.length) {
      out += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[++i] & 0x3f) << 6) | (bytes[++i] & 0x3f));
    } else if (b >= 0xf0 && i + 3 < bytes.length) {
      const cp = ((b & 0x07) << 18) | ((bytes[++i] & 0x3f) << 12) | ((bytes[++i] & 0x3f) << 6) | (bytes[++i] & 0x3f);
      out += String.fromCodePoint(cp);
    }
  }
  return out;
}

function readText(path) {
  const f = new File(path, "read");
  if (!f.isopen) return null;
  const bytes = [];
  while (f.position < f.eof) {
    const chunk = f.readbytes(Math.min(4096, f.eof - f.position));
    if (!chunk || !chunk.length) break;
    for (let i = 0; i < chunk.length; i++) bytes.push(chunk[i]);
  }
  f.close();
  return utf8(bytes);
}

function basename(path) {
  return String(path).split(/[\/:]/).pop();
}

// ── Reporting ───────────────────────────────────────────────────────────── //

function say(message) {
  post(`bach.mcp.algo ${runner}: ${message}\n`);
}

function fail(e) {
  const message = typeof e === "string" ? e : (e.message || String(e)) + (e.line ? ` (line ${e.line})` : "");
  say(`error: ${message}`);
  outlet(1, "status", "error", message);
  outlet(2, "error", runner, message);
}

// ── Messages ────────────────────────────────────────────────────────────── //

function setname(name, file) {
  runner = String(name);
  if (file !== undefined && !source) load(file);
}

function remote(target, cmd, ...args) {
  if (String(target) !== runner && String(target) !== "*") return;
  const command = String(cmd);
  const handlers = { load, reload, run, bang, auto, watch };
  if (handlers[command]) handlers[command](...args);
  else setParam(command, args);
}

function load(path) {
  if (path === undefined) return fail("load needs a file path");
  const t = readText(String(path));
  if (t === null) return fail(`cannot read ${path}`);
  source = String(path);
  text = t;
  freshLoad = true;
  compileText();
  if (watching) watcher.repeat();
}

function reload() {
  if (!source) return fail("nothing loaded");
  load(source);
}

function run() {
  runNow();
}

function bang() {
  runNow();
}

function auto(on) {
  autorun = Boolean(Number(on));
}

function watch(on) {
  watching = Boolean(Number(on));
  if (watching && source) watcher.repeat();
  else watcher.cancel();
}

function input(kind, name) {
  if (kind === "dictionary") {
    try {
      inputScore = JSON.parse(new Dict(String(name)).stringify());
    } catch (e) {
      return fail(`cannot read the input dictionary ${name}`);
    }
  } else if (kind === "clear") {
    inputScore = null;
  } else {
    return fail("input expects a dictionary (connect bach.mcp.translate @out json or another bach.mcp.algo)");
  }
  if (autorun) schedule();
}

function done() {
  // end of patcherargs' attribute list
}

function anything(...args) {
  setParam(messagename, args);
}

function setParam(name, args) {
  if (!compiled) return fail(`no algorithm loaded (received "${name}")`);
  const spec = compiled.specs.find((s) => s.name === name);
  if (!spec) {
    return fail(`"${name}" is not a parameter. Parameters: ${compiled.specs.map((s) => s.name).join(", ")}`);
  }
  try {
    values[name] = core.coerce(spec, args);
  } catch (e) {
    return fail(e);
  }
  outlet(1, "set", name, ...core.valueAtoms(spec, values[name]));
  if (autorun) schedule();
}

function notifydeleted() {
  pending.cancel();
  watcher.cancel();
}

// ── Compiling and running ───────────────────────────────────────────────── //

function compileText() {
  let next;
  try {
    next = core.compile(text);
  } catch (e) {
    freshLoad = false;
    return fail(e);
  }
  // A parameter that keeps its name and type keeps its current value.
  const kept = {};
  for (const spec of next.specs) {
    const old = compiled && compiled.specs.find((s) => s.name === spec.name && s.type === spec.type);
    kept[spec.name] = core.clone(spec.default);
    if (old && values[spec.name] !== undefined) {
      try {
        kept[spec.name] = core.coerce(spec, core.valueAtoms(old, values[spec.name]));
      } catch (e) {
        // out of the new options: back to the default
      }
    }
  }
  compiled = next;
  values = kept;
  const params = compiled.specs.map((s) => Object.assign({}, s, { value: values[s.name] }));
  outlet(1, "spec", JSON.stringify({ title: basename(source).replace(/\.js$/, ""), path: source, params }));
  say(`loaded ${basename(source)}: ${core.describe(compiled.specs, values).join("; ")}`);
  runNow();
}

function schedule() {
  pending.cancel();
  pending.schedule(20);
}

function runNow() {
  pending.cancel();
  if (!compiled) return;
  let result;
  try {
    result = core.run(compiled, values, inputScore);
  } catch (e) {
    freshLoad = false;
    return fail(e);
  }
  scoreDict.clear();
  scoreDict.parse(JSON.stringify(result.score));
  outlet(1, "status", "ok", `${result.notes} notes, ${result.ms} ms`);
  if (freshLoad) outlet(2, "loaded", runner, basename(source), result.notes, result.ms);
  else outlet(2, "done", runner, result.notes, result.ms);
  freshLoad = false;
  outlet(0, "dictionary", scoreDict.name);
}

function checkFile() {
  if (!source || !watching) return;
  const t = readText(source);
  if (t !== null && t !== text) {
    text = t;
    say(`${basename(source)} changed on disk`);
    compileText();
  }
}
