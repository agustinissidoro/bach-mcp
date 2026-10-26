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
(from another runner, or from a roll through bachmcp.translate @out json) and
lives only in memory: nothing is written to disk unless write_to_playground
asks for it. The result leaves outlet 0 as `dictionary <name>`, and the runner
never tells a roll to read it, so a transformer fits any flow. The runner never
feeds its own result back: what it transforms is always a score that came in at
the inlet, so that anything (another algorithm, a hand edit in a roll) can act
on the music between two transformations. What happens depends on the source
mode:

  source_mode 1   non-destructive (default). The source is held: every output
                  starts again from it. An input becomes the source only when
                  there is none yet; after that, inputs are ignored until
                  capture_source.
  source_mode 0   destructive. Every input becomes the source, and is never
                  transformed by itself (no loop through a roll): the next dump
                  or parameter change transforms it. After an output the runner
                  is "processing" until the next input arrives (outlet 2:
                  <name> processing 1, then 0): while it is, parameter changes are
                  kept but output nothing, so that each output works on the score
                  that came back. If nothing comes back within 3 seconds, the
                  runner stops waiting: <name> timeout 1, then processing 0.
                  dump always outputs.

auto_dump 1 (default) outputs a score on every parameter change; auto_dump 0
outputs only on dump (or bang).

Messages:
  set_name <name> [file]  the instance's name (and a file to load)
  load <path>             load and run a file
  load_algo <path>        the same; a failure is "error: impossible to load ..." (outlet 2)
  try_load_algo <path>    the same, silent: a file that cannot be loaded is ignored
  reload                  read the file again
  dump, bang, run         transform the source with the current values: the score out of outlet 0
  <param> <value...>      set a parameter, e.g. "shift 700"
  param <param> <value...>  the same, as bachmcp.gui.params sends it
  input dictionary <n>    a source score; input clear forgets it
  capture_source          "dump" out of outlet 1; the next input becomes the source
  source_mode 0/1         0 destructive, 1 non-destructive (see above)
  write_to_playground     write the source next to the algorithm, as <name>.source.json
  auto_dump 0/1           output on every parameter change (default 1); 0: only on dump
  verbose 0/1             say in the Max console what happens (default 0: only errors)
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

const PROCESSING_TIMEOUT_MS = 3000;

const source = {
  score: null,
  from: "",                 // "inlet"
  destructive: false,       // source_mode 0: see the top
  open: false,              // capture_source: the next input becomes the source
  processing: false,        // destructive: an output went out, its score has not come back yet
};

const engine = createEngine(
  { outlet: (...a) => outlet(...a), post: (...a) => post(...a), messnamed: (...a) => messnamed(...a), Dict, Task, File },
  { name: "transformer", accepts: "transformer", needs: "function transform(source, p) { ... }" },
  {
    source: () => source.score,
    spec: () => ({ source: sourceInfo() }),
    loaded() {
      // The source belongs to the instance, not to the file: a new algorithm keeps it.
      if (source.score) return false;
      engine.say("waiting for a source: input dictionary <name>");
      return true;
    },
    automatic: () => !(source.destructive && source.processing),
    ran() {
      if (source.destructive) setProcessing(true);
    },
  },
);

try {
  setinletassist(0, "load_algo <path>, run, [param] <param> <value>, input dictionary <name>, capture_source");
  setoutletassist(0, "dictionary <name>: the score (bachjson-complete)");
  setoutletassist(1, "to the parameter panel (bachmcp.gui.params.v8ui.js); dump (capture_source)");
  setoutletassist(2, "<name> algo_loaded / algo_done / algo_error / processing 0|1 / timeout 1");
} catch (e) {
  // assist strings are optional
}

// ── Messages ────────────────────────────────────────────────────────────── //

function set_name(name, file) { engine.setname(name, file); }
function load(path) { engine.load(path); }
function load_algo(path) { engine.loadAlgo(path); }
function try_load_algo(path) { engine.tryLoadAlgo(path); }
function reload() { engine.reload(); }
function run() { engine.runNow(); }
function bang() { engine.runNow(); }
function dump() { engine.runNow(); }
function auto_dump(on) { engine.autoDump(on); }
function watch(on) { engine.watch(on); }
function verbose(on) { engine.verbose(on); }
function param(name, ...args) { engine.setParam(String(name), args); }
function anything(...args) { engine.setParam(messagename, args); }
function done() {} // end of patcherargs' attribute list

/** 0 destructive (every input is the source), 1 non-destructive (the source is held). */
function source_mode(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`source_mode is 0 (destructive) or 1 (non-destructive), got ${flag}`);
  source.destructive = m === 0;
  setProcessing(false);
  outlet(1, "source_mode", m);
}

function setProcessing(on) {
  if (on) timeout.schedule(PROCESSING_TIMEOUT_MS);
  else timeout.cancel();
  if (source.processing === on) return;
  source.processing = on;
  outlet(2, engine.state.name, "processing", on ? 1 : 0);
}

/** Nothing came back after an output: stop waiting, so that parameter changes output again. */
const timeout = new Task(() => {
  if (!source.processing) return;
  outlet(2, engine.state.name, "timeout", 1);
  setProcessing(false);
});

function notifydeleted() {
  timeout.cancel();
  engine.deleted();
}

/** Ask for the score (a roll answers "dump"); the next input becomes the source, in either mode. */
function capture_source() {
  source.open = true;
  outlet(1, "status", "ok", "the next score at the inlet becomes the source");
  outlet(1, "dump");
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
  if (!source.destructive && !first) return;  // the source stays until capture_source
  source.score = score;
  source.from = "inlet";
  source.open = false;
  tellPanelSource();
  if (source.destructive) return setProcessing(false);  // kept, transformed by the next dump or change
  if (engine.state.autorun) engine.schedule();
}

/** Write the source next to the algorithm (<name>.source.json), where the server checks a transformer. */
function write_to_playground() {
  if (!source.score) return engine.fail("write_to_playground: there is no source yet");
  if (!engine.state.path) return engine.fail("write_to_playground: no algorithm loaded, so no folder to write to");
  const path = engine.state.path.replace(/[^\/:]*$/, "") + engine.state.name + ".source.json";
  if (!engine.files.write(path, JSON.stringify(source.score))) return engine.fail(`could not write ${path}`);
  outlet(1, "status", "ok", `source written to ${path}`);
}

// ── The source ──────────────────────────────────────────────────────────── //

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
