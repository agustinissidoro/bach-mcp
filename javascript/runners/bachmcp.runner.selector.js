/*
bachmcp.runner.selector.js
--------------------------
The selector runner ([v8], inside bachmcp.algo.select). It runs an algorithm
that picks notes of a score: a file that defines
`function select(source, p) { ... }` and returns the notes it picks (the note
objects of `source`, or their addresses [voice, chord, note], 1-based). A file
of another kind is refused. The engine (bachmcp.runner.engine.js) does the rest.

The source is the score the selector picks in, in bachjson-complete, as
`input dictionary <name>` (from a roll through bachmcp.translate @out json).
Every run goes: parameter change (or dump), "dump" out of outlet 1 to ask the
roll for its score, the score comes in, the algorithm selects in it. While the
runner waits it is "processing" (outlet 3: <name> processing 1, then 0);
changes meanwhile are kept, and the score that comes in runs with the latest
values. If nothing comes in within 3 seconds: <name> timeout 1, then
processing 0. The source modes are the transformer's:
  source_mode 1   non-destructive (default). Only the first run asks for the
                  score: it becomes the source, held, and every later run
                  selects in it again, without a dump. capture_source asks
                  for a new one. An input that arrives unasked becomes the
                  source only when there is none yet.
  source_mode 0   destructive. Every run asks for the score, so it selects in
                  what the roll holds now. An input that arrives unasked is
                  kept as the source but never selected in by itself (no loop
                  through a roll). Selections are not
cumulative: each run replaces the previous one (involutive is ignored for now).
A run sends:

  outlet 0   the score, its slot `selection_slot` (default 11) declared in the
             slotinfo as "selected" (an int, 0..1), every note flagged in it, so
             that a runner with process_only_selection 1 works on it:
               dump_selection_only 1  (default) only the selected notes, each flagged 1
               dump_selection_only 0  the whole source, flagged 1 or 0
             selection_slot 0: no score.
  outlet 1   then, to bach: clearselection, sel note [v c n] ...
             ("sel note", singular: bach's "sel notes" selects every note, whatever follows)

dump_selection outputs only the tracked notes of the source, as a score (each
flagged 1 in the slot), out of outlet 0.

Messages:
  set_name <name> [file]  the instance's name (and a file to load)
  load <path>             load and run a file
  load_algo <path>        the same; a failure is "error: impossible to load ..." (outlet 3)
  try_load_algo <path>    the same, silent: a file that cannot be loaded is ignored
  reload                  read the file again
  dump, bang, run         ask the roll for its score and select in it: commands out of outlet 1
  <param> <value...>      set a parameter
  param <param> <value...>  the same, as bachmcp.gui.params sends it
  input dictionary <n>    the source; input clear forgets it
  capture_source          "dump" out of outlet 1; the next input becomes the source
  source_mode 0/1         0 destructive, 1 non-destructive (see above)
  involutive 0/1          kept for later; ignored for now (every run is clearselection, sel)
  dump_selection_only 0/1 the score out of outlet 0: the selected notes only (1, default) or the whole source
  selection_slot <n>      the slot marking the selection, read and written (default 11; 0: none)
  process_only_selection 0/1  1: select only among the notes flagged in that slot (default 0)
  dump_selection          the selected notes as a score, out of outlet 0
  clear_selection         nothing selected any more: the score (empty, or the source all 0), then clearselection
  snap 0/1/3              the output score's pitches: 0 semitones, 1 quarter tones, 3 free (default)
  bypass 0/1              1: runs do nothing; a score at the inlet goes straight out of outlet 0
  repeat                  the last output again: the score out of outlet 0, then the commands out of outlet 1
  write_to_playground     write the last score sent to <playground>/scores/<name>.json
  auto_dump 0/1           select on every parameter change (default 1); 0: only on dump
  verbose 0/1             say in the Max console what happens (default 0: only errors)
  watch 0/1               reload when the file changes on disk (default 1)

Outlets: 0 the score (marked source, dump_selection), 1 to bach (selection commands, dump),
2 the parameter panel, 3 <name> algo_loaded / algo_done / algo_error / processing 0|1 / timeout 1.
*/
"use strict";

autowatch = 1;
inlets = 1;
outlets = 4;

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
const { countNotes } = need("bachmcp.runner.loader.js");
const sel = need("bachmcp.runner.selection.js");

const BACH = 1;
const PANEL = 2;
const STATUS = 3;
const PROCESSING_TIMEOUT_MS = 3000;

const source = { score: null, from: "", processing: false, destructive: false, open: false };
const selection = {
  involutive: false,
  slot: 11,
  only: true,  // dump_selection_only
  within: false,  // process_only_selection
  map: null,      // process_only_selection: address in what the algorithm got -> in the source
  tracked: new Set(), // "v c n" of what this runner selected
  commands: [],       // the last run's messages to bach, for repeat
};

const engine = createEngine(
  { outlet: (...a) => outlet(...a), post: (...a) => post(...a), messnamed: (...a) => messnamed(...a), Dict, Task, File },
  { name: "selector", accepts: "selector", needs: "function select(source, p) { ... }", panel: PANEL, status: 3 },
  {
    source: () => {
      selection.map = null;
      if (!selection.within || !source.score || !selection.slot) return source.score;
      const parts = sel.split(source.score, selection.slot);
      selection.map = parts.map;
      return parts.picked;
    },
    spec: () => ({ source: sourceInfo() }),
    loaded: () => true,  // a load runs nothing: the first change (or dump) asks for the score
    // Every run starts with a dump: the roll's score comes in, the algorithm selects in it.
    request: () => {
      if (source.score && !source.destructive) return false;  // non-destructive: the held source
      askForScore();
      return true;
    },
    ran(result) {
      const map = selection.map;
      apply(map ? result.selection.map((a) => map[a.join(" ")]) : result.selection);
    },
  },
);

try {
  setinletassist(0, "load_algo <path>, run, [param] <param> <value>, input dictionary <name>, dump_selection");
  setoutletassist(0, "dictionary <name>: the source with the selection slot (a run), the selected notes (dump_selection)");
  setoutletassist(1, "to bach: sel / select notes ..., clearselection, dump");
  setoutletassist(2, "to the parameter panel (bachmcp.gui.params.v8ui.js)");
  setoutletassist(3, "<name> algo_loaded / algo_done / algo_error");
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
function notifydeleted() {
  timeout.cancel();
  engine.deleted();
}
function snap(n) { engine.setSnap(n); }
function bypass(on) {
  engine.setBypass(on);
  if (engine.state.bypass) setProcessing(false);
}
function repeat() {
  engine.repeat();
  for (const c of selection.commands) outlet(BACH, ...c);
}
function done() {} // end of patcherargs' attribute list

/** 0: sel (adds to the selection), 1: select (toggles). */
function involutive(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`involutive is 0 (sel) or 1 (select), got ${flag}`);
  selection.involutive = m === 1;
  outlet(PANEL, "involutive", m);
}

/** The score out of outlet 0: only the selected notes (1) or the whole source flagged (0). */
function dump_selection_only(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`dump_selection_only is 0 or 1, got ${flag}`);
  selection.only = m === 1;
  outlet(PANEL, "dump_selection_only", m);
}

/** 1: select only among the notes already flagged in selection_slot. */
function process_only_selection(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`process_only_selection is 0 or 1, got ${flag}`);
  selection.within = m === 1;
  outlet(PANEL, "process_only_selection", m);
  if (engine.state.autorun && engine.state.compiled) engine.schedule();
}

function selection_slot(n) {
  const slot = Number(n);
  if (!Number.isInteger(slot) || slot < 0 || slot > 30) return engine.fail(`selection_slot is a slot number 1..30, or 0 for none, got ${n}`);
  selection.slot = slot;
}

/** 0 destructive (every run asks for the roll's score), 1 non-destructive (the source is held). */
function source_mode(flag) {
  const m = Number(flag);
  if (m !== 0 && m !== 1) return engine.fail(`source_mode is 0 (destructive) or 1 (non-destructive), got ${flag}`);
  source.destructive = m === 0;
  setProcessing(false);
  outlet(PANEL, "source_mode", m);
}

function capture_source() {
  source.open = true;
  outlet(PANEL, "status", "ok", "the next score at the inlet becomes the source");
  outlet(BACH, "dump");
}

/** A run waits for the score: "dump" out of outlet 1, the input that answers it becomes the source and runs. */
function askForScore() {
  if (source.processing) return;  // already asked: the score runs with the latest values
  setProcessing(true);
  outlet(BACH, "dump");
}

function setProcessing(on) {
  if (on) timeout.schedule(PROCESSING_TIMEOUT_MS);
  else timeout.cancel();
  if (source.processing === on) return;
  source.processing = on;
  outlet(STATUS, engine.state.name, "processing", on ? 1 : 0);
}

/** No score answered the dump: stop waiting, so that the next change asks again. */
const timeout = new Task(() => {
  if (!source.processing) return;
  outlet(STATUS, engine.state.name, "timeout", 1);
  setProcessing(false);
});

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
    const present = new Set(sel.allAddresses(score).map((a) => a.join(" ")));
    for (const key of [...selection.tracked]) if (!present.has(key)) selection.tracked.delete(key);
    tellPanelSource();
  }
  source.open = false;
  setProcessing(false);
  if (asked) return engine.process();                       // the answer to a dump: select in it
  if (!source.destructive && engine.state.autorun) engine.schedule();  // a first source, unasked
  // destructive and unasked: kept, selected in by the next change or dump (no loop through a roll)
}

function dump_selection() {
  if (!source.score) return engine.fail("dump_selection: there is no source yet");
  engine.sendScore(sel.only(source.score, trackedAddresses(), selection.slot));
}

function clear_selection() {
  selection.tracked.clear();
  sendMarked();
  outlet(BACH, "clearselection");
}

/** Write the last score sent to the playground: scores/<name>.json. */
function write_to_playground() { engine.writeScore(); }

// ── The selection ───────────────────────────────────────────────────────── //

/** The run's notes replace the selection: the score out, then clearselection and sel. */
function apply(addresses) {
  selection.tracked = new Set(addresses.map((a) => a.join(" ")));
  selection.commands = [["clearselection"]];
  if (addresses.length) selection.commands.push(["sel", "note", ...sel.bracket(addresses)]);
  sendMarked();
  for (const c of selection.commands) outlet(BACH, ...c);
}

function trackedAddresses() {
  return [...selection.tracked].map((k) => k.split(" ").map(Number));
}

/** The score with the slot declared and every note flagged, out of outlet 0 (see dump_selection_only). */
function sendMarked() {
  if (!selection.slot || !source.score) return;
  const make = selection.only ? sel.only : sel.mark;
  engine.sendScore(make(source.score, trackedAddresses(), selection.slot));
}

function sourceInfo() {
  return source.score ? { notes: countNotes(source.score), from: source.from } : { notes: 0, from: "" };
}

function tellPanelSource() {
  const info = sourceInfo();
  outlet(PANEL, "source", info.notes, info.from || "none");
}
