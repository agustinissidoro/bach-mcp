/*
bachmcp.runner.transformer.js
-----------------------------
The transformer runner ([v8], inside bachmcp.algo.trans). It runs an algorithm
that changes music already there: a file that defines
`function transform(source, p) { ... }`. A file of another kind is refused. The
engine (bachmcp.runner.engine.js) does the rest and lists the outlets; this
file adds the source.

The source is the score a transformer works on, in bachjson-complete like every
score between objects. It arrives at the inlet as `input dictionary <name>`
(from another runner, or from a roll through bachmcp.translate @out json). The
runner keeps it, so every run starts again from it, never from the
transformer's own output, and saves it next to the algorithm as
<name>.source.json, so that it survives reopening the patch. What a new input
does depends on the source mode:

  keep    (default) the source is kept: an input becomes the source only when
          there is none yet; after that, inputs are ignored until `capture`
  follow  every input becomes the source, so that the next change of a
          parameter transforms the latest score. An input does not run the
          transformer by itself (only the first one does), so a score coming
          back from the roll can never loop into a run.

Messages:
  setname <name> [file]   the instance's name (and a file to load)
  load <path>             load and run a file
  reload                  read the file again
  run, bang               run with the current values
  <param> <value...>      set a parameter, e.g. "shift 700"
  input dictionary <n>    a source score; input clear forgets it
  capture                 the next input becomes the source, even in keep mode
  sourcemode keep|follow  what a score at the inlet does (see above)
  auto 0/1                run on every parameter change (default 1)
  watch 0/1               reload when the file changes on disk (default 1)
*/
"use strict";

autowatch = 1;
inlets = 1;
outlets = 3;

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

const { createEngine } = need("bachmcp.runner.engine.js");

const SOURCE_MODES = ["keep", "follow"];

const source = {
  score: null,
  from: "",          // "file" (the .source.json next to the algorithm) or "inlet"
  mode: "keep",      // or "follow": see the top
  open: false,       // capture: the next input becomes the source
};

const engine = createEngine(
  { outlet: (...a) => outlet(...a), post: (...a) => post(...a), messnamed: (...a) => messnamed(...a), Dict, Task, File },
  { name: "transformer", accepts: "transformer", needs: "function transform(source, p) { ... }" },
  {
    source: () => source.score,
    spec: () => ({ source: sourceInfo() }),
    loaded() {
      // It keeps the source it has, else the one saved next to it; without one it waits for an input.
      if (!source.score) {
        const saved = readSource();
        if (saved) {
          source.score = saved;
          source.from = "file";
        }
      }
      if (source.score) return false;
      engine.say("waiting for a source: input dictionary <name>");
      return true;
    },
    forget() {
      source.score = null;  // another algorithm: its own source
      source.from = "";
    },
  },
);

try {
  setinletassist(0, "load <path>, run, <param> <value>, input dictionary <name>");
  setoutletassist(0, "dictionary <name>: the score (bachjson-complete)");
  setoutletassist(1, "to the parameter panel (bachmcp.gui.params.jsui.js)");
  setoutletassist(2, "<name> algo_loaded / algo_done / algo_error");
} catch (e) {
  // assist strings are optional
}

// ── Messages ────────────────────────────────────────────────────────────── //

function setname(name, file) { engine.setname(name, file); }
function load(path) { engine.load(path); }
function reload() { engine.reload(); }
function run() { engine.runNow(); }
function bang() { engine.runNow(); }
function auto(on) { engine.auto(on); }
function watch(on) { engine.watch(on); }
function anything(...args) { engine.setParam(messagename, args); }
function notifydeleted() { engine.deleted(); }
function done() {} // end of patcherargs' attribute list

/** The source mode: keep the original, or follow every score that arrives. */
function sourcemode(mode) {
  const m = String(mode);
  if (!SOURCE_MODES.includes(m)) return engine.fail(`sourcemode is ${SOURCE_MODES.join(" or ")}, got ${m}`);
  source.mode = m;
  outlet(1, "sourcemode", m);
}

/** The next input becomes the source, even in keep mode. */
function capture() {
  source.open = true;
  outlet(1, "status", "ok", "the next score at the inlet becomes the source");
}

function input(what, name) {
  if (what === "clear") {
    source.score = null;
    source.from = "";
    tellPanelSource();
    return;
  }
  if (what !== "dictionary") return engine.fail("input expects a dictionary: input dictionary <name>");
  let score;
  try {
    score = JSON.parse(new Dict(String(name)).stringify());
  } catch (e) {
    return engine.fail(`cannot read the input dictionary ${name}`);
  }
  const first = !source.score || source.open;
  if (source.mode === "keep" && !first) return;  // the original stays until capture
  source.score = score;
  source.from = "inlet";
  source.open = false;
  saveSource(score);
  tellPanelSource();
  if (engine.state.autorun && (first || source.mode === "keep")) engine.schedule();
}

// ── The source ──────────────────────────────────────────────────────────── //

function sourcePath() {
  return engine.state.path ? engine.state.path.replace(/\.js$/, "") + ".source.json" : "";
}

function countNotes(score) {
  let n = 0;
  for (const v of (score && score.voices) || []) for (const c of (v && v.chords) || []) n += ((c && c.notes) || []).length;
  return n;
}

function sourceInfo() {
  return source.score ? { notes: countNotes(source.score), from: source.from } : { notes: 0, from: "" };
}

function tellPanelSource() {
  const info = sourceInfo();
  outlet(1, "source", info.notes, info.from || "none");
}

function readSource() {
  const path = sourcePath();
  const text = path ? engine.files.read(path) : null;
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (e) {
    engine.say(`${path} is not a score (JSON): ignored`);
    return null;
  }
}

/** Keep the source next to the algorithm, so that it survives reopening the patch. */
function saveSource(score) {
  const path = sourcePath();
  if (path && !engine.files.write(path, JSON.stringify(score))) engine.say(`could not save the source to ${path}`);
}
