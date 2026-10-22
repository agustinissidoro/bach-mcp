/*
bach.mcp.algo.js — the runner (v8). Lives inside the bach.mcp.algo abstraction.

Loads an algorithm file (see bach.mcp.core.js), runs it, and sends:
  outlet 0  dictionary <name>         the JSON score, for bach.mcp.translate
  outlet 1  spec / set / status ...   the panel (bach.mcp.params)
  outlet 2  loaded / done / error     what happened, for the patch and the MCP server

A producer runs on its parameters alone. A transformer works on a source score,
which the runner keeps so that every run starts again from it, never from the
transformer's own output. The source is a bach text file next to the algorithm,
<name>.source.txt: it survives reopening the patch, and it is made by asking
bach.roll (through [r to_bach]) to write itself there: on the first load, and
whenever `capture` is sent. A score arriving at the right inlet is also a source
(bach.roll -> [bach.portal @out t] -> [bach.mcp.translate @in bach @out json]),
depending on the source mode:

  keep    (default) the source is kept: an input becomes the source only when
          there is none yet (and is saved to <name>.source.txt); after that,
          inputs are ignored until `capture`
  follow  every input becomes the source, so that the next change of a
          parameter transforms the latest score. An input does not run the
          transformer by itself (only the first one does), so a dump of the
          roll can never loop back into a run.

Messages:
  load <path>          load and run a file (absolute path, or a name in the search path)
  reload               read the file again
  run, bang            run with the current values
  <param> <value...>   set a parameter, e.g. "times 32", "register 4800 8400"
  capture              transformer: take the score now in the roll as the new source
  sourcemode keep|follow  what a score at the right inlet does (see above)
  auto 0/1             run on every parameter change (default 1)
  watch 0/1            reload when the file changes on disk (default 1)
  roll <name>          the [receive] that feeds bach.roll (default to_bach)
  input dictionary <n> a source score from another object (right inlet)
  remote <runner> <message...>  a message from the MCP server: acted on when <runner> is this name
*/
"use strict";

autowatch = 1;
inlets = 1;
outlets = 3;

function requireSibling(name) {
  try {
    return require(name);
  } catch (e) {
    return require("./" + name);
  }
}

const core = requireSibling("bach.mcp.core.js");
const S = requireSibling("bach.mcp.score.js");

const CAPTURE_POLL_MS = 50;
const CAPTURE_TIMEOUT_MS = 4000;

let runner = "algo";
let rollReceive = "to_bach";
let algoPath = "";
let text = "";
let compiled = null;
let values = {};
let sourceScore = null;
let sourceFrom = "";  // "file" (the .source.txt next to the algorithm) or "inlet"
let sourceMode = "keep";  // or "follow": see the header
const SOURCE_MODES = ["keep", "follow"];
let autorun = true;
let watching = true;
let freshLoad = false;
let capturing = null;  // {path, before, started}

const scoreDict = new Dict();
const pending = new Task(runNow, this);
const watcher = new Task(checkFile, this);
watcher.interval = 1000;
const capturer = new Task(checkCapture, this);
capturer.interval = CAPTURE_POLL_MS;

try {
  setinletassist(0, "load <path>, run, capture, <param> <value>, input dictionary <name>");
  setoutletassist(0, "dictionary: the JSON score (to bach.mcp.translate)");
  setoutletassist(1, "to bach.mcp.params");
  setoutletassist(2, "loaded / done / error");
} catch (e) {
  // assist strings are optional
}

// ── Reading files ───────────────────────────────────────────────────────── //

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

/** Write a text file (whole, replacing what was there); false if it cannot be opened. */
function writeText(path, content) {
  const f = new File(path, "write", "TEXT");
  if (!f.isopen) return false;
  f.position = 0;
  f.eof = 0;
  for (let i = 0; i < content.length; i += 4096) f.writestring(content.slice(i, i + 4096));
  f.eof = f.position;
  f.close();
  return true;
}

function basename(path) {
  return String(path).split(/[\/:]/).pop();
}

/** A whole score written by bach.roll: starts with roll and every bracket is closed. */
function isComplete(llll) {
  if (!llll || !/^\s*roll\b/.test(llll)) return false;
  let depth = 0;
  for (const token of llll.match(/"(?:[^"\\]|\\.)*"|[\[\]]|[^\s\[\]"]+/g) || []) {
    if (token === "[") depth += 1;
    else if (token === "]") depth -= 1;
    if (depth < 0) return false;
  }
  return depth === 0 && /\]\s*$/.test(llll);
}

function sourcePath() {
  return algoPath ? algoPath.replace(/\.js$/, "") + ".source.txt" : "";
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

function sourceInfo() {
  if (!compiled || compiled.kind !== "transformer") return null;
  return sourceScore ? { notes: S.countNotes(sourceScore), from: sourceFrom } : { notes: 0, from: "" };
}

function tellPanelSource() {
  const info = sourceInfo();
  if (info) outlet(1, "source", info.notes, info.from || "none");
}

// ── Messages ────────────────────────────────────────────────────────────── //

function setname(name, file) {
  runner = String(name);
  if (file !== undefined && !algoPath) load(file);
}

function roll(name) {
  rollReceive = String(name);
}

function remote(target, cmd, ...args) {
  if (String(target) !== runner && String(target) !== "*") return;
  const command = String(cmd);
  const handlers = { load, reload, run, bang, auto, watch, capture, sourcemode };
  if (handlers[command]) handlers[command](...args);
  else setParam(command, args);
}

function load(path) {
  if (path === undefined) return fail("load needs a file path");
  const t = readText(String(path));
  if (t === null) return fail(`cannot read ${path}`);
  if (String(path) !== algoPath) {
    sourceScore = null;  // another algorithm: its own source
    sourceFrom = "";
  }
  algoPath = String(path);
  text = t;
  freshLoad = true;
  compileText();
  if (watching) watcher.repeat();
}

function reload() {
  if (!algoPath) return fail("nothing loaded");
  load(algoPath);
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
  if (watching && algoPath) watcher.repeat();
  else watcher.cancel();
}

function input(kind, name) {
  if (kind === "clear") {
    sourceScore = null;
    sourceFrom = "";
    tellPanelSource();
    return;
  }
  if (kind !== "dictionary") {
    return fail("input expects a dictionary (connect bach.mcp.translate @in bach @out json, or another bach.mcp.algo)");
  }
  let score;
  try {
    score = JSON.parse(new Dict(String(name)).stringify());
  } catch (e) {
    return fail(`cannot read the input dictionary ${name}`);
  }
  const transformer = compiled && compiled.kind === "transformer";
  const first = !sourceScore;
  if (transformer && sourceMode === "keep" && !first) return;  // the original stays until capture
  sourceScore = score;
  sourceFrom = "inlet";
  if (transformer && sourceMode === "keep") saveSource(score);
  tellPanelSource();
  if (autorun && (first || !transformer || sourceMode === "keep")) schedule();
}

/** The source mode: keep the original, or follow every score that arrives. */
function sourcemode(mode) {
  const m = String(mode);
  if (!SOURCE_MODES.includes(m)) return fail(`sourcemode is ${SOURCE_MODES.join(" or ")}, got ${m}`);
  sourceMode = m;
  outlet(1, "sourcemode", m);
}

/** Keep a source from the inlet next to the algorithm, so that it survives reopening the patch. */
function saveSource(score) {
  const path = sourcePath();
  if (!path) return;
  try {
    if (!writeText(path, S.scoreToLlll(S.normalizeScore(score)))) say(`could not save the source to ${path}`);
  } catch (e) {
    say(`could not save the source: ${e.message}`);
  }
}

/** Take the score now in bach.roll as the transformer's source. */
function capture() {
  if (!algoPath) return fail("load a transformer before capturing a source");
  const path = sourcePath();
  capturing = { path, before: readText(path), started: Date.now() };
  outlet(1, "status", "ok", "capturing the score from the roll...");
  messnamed(rollReceive, "writetxt", path);
  capturer.repeat();
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
  capturer.cancel();
}

// ── Sources ─────────────────────────────────────────────────────────────── //

function readSourceFile(path) {
  const llll = readText(path);
  if (!isComplete(llll)) return null;
  try {
    return S.llllToScore(llll);
  } catch (e) {
    return null;
  }
}

function checkCapture() {
  if (!capturing) return capturer.cancel();
  const now = readText(capturing.path);
  const waited = Date.now() - capturing.started;
  const fresh = isComplete(now) && (now !== capturing.before || waited > 1000);
  if (!fresh) {
    if (waited < CAPTURE_TIMEOUT_MS) return;
    capturer.cancel();
    capturing = null;
    return fail(`bach.roll did not write the score (is it fed by [r ${rollReceive}]?)`);
  }
  capturer.cancel();
  capturing = null;
  const score = readSourceFile(sourcePath());
  if (!score) return fail("could not read the captured score");
  sourceScore = score;
  sourceFrom = "file";
  say(`source: ${S.countNotes(score)} notes from the roll (${basename(sourcePath())})`);
  tellPanelSource();
  runNow();
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
  // A transformer keeps the source it has; else the one saved next to it; else it captures the roll.
  if (compiled.kind === "transformer" && !sourceScore) {
    const saved = readSourceFile(sourcePath());
    if (saved) {
      sourceScore = saved;
      sourceFrom = "file";
    }
  }
  const params = compiled.specs.map((s) => Object.assign({}, s, { value: values[s.name] }));
  outlet(1, "spec", JSON.stringify({
    title: basename(algoPath).replace(/\.js$/, ""), path: algoPath, kind: compiled.kind, source: sourceInfo(), params,
  }));
  say(`loaded ${basename(algoPath)} (${compiled.kind}): ${core.describe(compiled.specs, values).join("; ")}`);
  if (compiled.kind === "transformer" && !sourceScore) capture();
  else runNow();
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
    result = core.run(compiled, values, sourceScore);
  } catch (e) {
    freshLoad = false;
    return fail(e);
  }
  scoreDict.clear();
  scoreDict.parse(JSON.stringify(result.score));
  outlet(1, "status", "ok", `${result.notes} notes, ${result.ms} ms`);
  if (freshLoad) outlet(2, "loaded", runner, basename(algoPath), result.notes, result.ms);
  else outlet(2, "done", runner, result.notes, result.ms);
  freshLoad = false;
  outlet(0, "dictionary", scoreDict.name);
}

function checkFile() {
  if (!algoPath || !watching) return;
  const t = readText(algoPath);
  if (t !== null && t !== text) {
    text = t;
    say(`${basename(algoPath)} changed on disk`);
    compileText();
  }
}
