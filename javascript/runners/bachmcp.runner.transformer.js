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
lives only in memory: nothing is written to disk. write_to_playground writes
the last score sent (the result), not the source. The result leaves outlet 0 as `dictionary <name>`, and the runner
never tells a roll to read it, so a transformer fits any flow. The runner never
feeds its own result back: what it transforms is always a score that came in at
the inlet, so that anything (another algorithm, a hand edit in a roll) can act
on the music between two transformations.

Every run goes: parameter change (or dump), "dump" out of outlet 1 to ask the
roll for its score, the score comes in, it is processed, the result goes out.
While the runner waits for the score it is "processing" (outlet 2: <name>
processing 1, then 0); changes meanwhile are kept, and the score that comes in
runs with the latest values. If nothing comes in within 3 seconds: <name>
timeout 1, then processing 0. What happens depends on the source mode:

  source_mode 1   non-destructive (default). Only the first run asks for the
                  score: it becomes the source, held, and every later run
                  starts again from it, without a dump. capture_source asks
                  for a new one. An input that arrives unasked becomes the
                  source only when there is none yet.
  source_mode 0   destructive. Every run asks for the score, so it works on
                  what the roll holds now. An input that arrives unasked is
                  kept as the source but never transformed by itself (no loop
                  through a roll).

process_only_selection 1 transforms only the selected notes: those flagged 1
in slot `selection_slot` (default 11; bachmcp.runner.selection.js, a selector
writes it). The algorithm gets a score of those notes only; the others are put
back unchanged around its result. process_only_selection 0 (default): the
whole score.

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
  input_mode 0/1          0 the whole score (default), 1 only the notes flagged in the slot named "selected"
  process_only_selection 0/1  0 the whole score (default), 1 only the selected notes (see above)
  selection_slot <n>      the slot that flags the selected notes (default 11)
  snap 0/1/3              the output's pitches: 0 semitones, 1 quarter tones, 3 free (default)
  bypass 0/1              1: runs do nothing; a score at the inlet goes straight out of outlet 0
  repeat                  the last score sent, out of outlet 0 again
  write_to_playground     write the last score sent to <playground>/scores/<name>.json
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
const sel = need("bachmcp.runner.selection.js");

const PROCESSING_TIMEOUT_MS = 3000;

const source = {
  score: null,
  from: "",                 // "inlet"
  destructive: false,       // source_mode 0: see the top
  open: false,              // capture_source: the next input becomes the source
  processing: false,        // a dump went out, the score has not come in yet
  selectedOnly: false,      // process_only_selection 1
  byName: false,            // input_mode 1: the slot is the one named "selected"
  slot: 11,                 // selection_slot
  rest: null,               // process_only_selection 1: the notes left out of the run, put back after it
};

const engine = createEngine(
  { outlet: (...a) => outlet(...a), post: (...a) => post(...a), messnamed: (...a) => messnamed(...a), Dict, Task, File },
  { name: "transformer", accepts: "transformer", needs: "function transform(source, p) { ... }" },
  {
    source: () => {
      source.rest = null;
      if (!source.selectedOnly || !source.score) return source.score;
      let slot = source.slot;
      if (source.byName) {
        slot = sel.selectionSlot(source.score);
        if (slot === null) throw new Error(`input_mode 1: the source has no slot named "${sel.SLOT_NAME}" (a selector writes it)`);
      }
      const parts = sel.split(source.score, slot);
      source.rest = parts.rest;
      return parts.picked;
    },
    output: (score) => (source.rest ? sel.merge(source.rest, score) : score),
    spec: () => ({ source: sourceInfo() }),
    loaded: () => true,  // a load runs nothing: the first change (or dump) asks for the score
    // Every run starts with a dump: the roll's score comes in, is processed, goes out.
    request: () => {
      if (source.score && !source.destructive) return false;  // non-destructive: the held source
      askForScore();
      return true;
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
function snap(n) { engine.setSnap(n); }
function repeat() { engine.repeat(); }
function bypass(on) {
  engine.setBypass(on);
  if (engine.state.bypass) setProcessing(false);
}
function done() {} // end of patcherargs' attribute list

/** 0 destructive (every input is the source), 1 non-destructive (the source is held). */
function source_mode(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`source_mode is 0 (destructive) or 1 (non-destructive), got ${flag}`);
  source.destructive = m === 0;
  setProcessing(false);
  outlet(1, "source_mode", m);
}

/** 0 the whole score, 1 only its selected notes. */
/** As before: 1 transforms only the notes flagged in the slot named "selected". */
function input_mode(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`input_mode is 0 (the whole score) or 1 (only the selected notes), got ${flag}`);
  source.selectedOnly = m === 1;
  source.byName = m === 1;
  outlet(1, "input_mode", m);
}

function process_only_selection(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`process_only_selection is 0 (the whole score) or 1 (only the selected notes), got ${flag}`);
  source.selectedOnly = m === 1;
  source.byName = false;
  outlet(1, "process_only_selection", m);
  if (engine.state.autorun && engine.state.compiled) engine.schedule();
}

function selection_slot(n) {
  const slot = Number(n);
  if (!Number.isInteger(slot) || slot < 1 || slot > 30) return engine.fail(`selection_slot is a slot number 1..30, got ${n}`);
  source.slot = slot;
}

function setProcessing(on) {
  if (on) timeout.schedule(PROCESSING_TIMEOUT_MS);
  else timeout.cancel();
  if (source.processing === on) return;
  source.processing = on;
  outlet(2, engine.state.name, "processing", on ? 1 : 0);
}

/** No score answered the dump: stop waiting, so that the next change asks again. */
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

/** A run waits for the score: "dump" out of outlet 1, the input that answers it becomes the source and runs. */
function askForScore() {
  if (source.processing) return;  // already asked: the score runs with the latest values
  setProcessing(true);
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
  if (engine.state.bypass) return engine.passThrough(name);
  const asked = source.processing;
  const first = !source.score || source.open;
  if (!source.destructive && !first && !asked) return;  // the source stays until capture_source
  if (source.destructive || first) {
    source.score = score;
    source.from = "inlet";
    tellPanelSource();
  }
  source.open = false;
  setProcessing(false);
  if (asked) return engine.process();                       // the answer to a dump: process it
  if (!source.destructive && engine.state.autorun) engine.schedule();  // a first source, unasked
  // destructive and unasked: kept, processed by the next change or dump (no loop through a roll)
}

/** Write the last score sent to the playground: scores/<name>.json. */
function write_to_playground() { engine.writeScore(); }

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
