/*
bachmcp.runner.generator.js
---------------------------
The generator runner ([v8], inside bachmcp.algo.gen). It runs an algorithm that
makes music from nothing: a file that defines `function produce(p) { ... }`. A
file of another kind is refused. Everything else is the engine's
(bachmcp.runner.engine.js), which also lists the outlets.

Messages:
  set_name <name> [file] the instance's name (and a file to load)
  load <path>            load and run a file
  load_algo <path>       the same; a failure is "error: impossible to load ..." (outlet 2)
  try_load_algo <path>   the same, silent: a file that cannot be loaded is ignored
  reload                 read the file again
  dump, bang, run        run with the current values: the score out of outlet 0
  <param> <value...>     set a parameter, e.g. "times 32", "register 4800 8400"
  param <param> <value...>  the same, as bachmcp.gui.params sends it
  snap 0/1/3             the output's pitches: 0 semitones, 1 quarter tones, 3 free (default)
  bypass 0/1             1: runs do nothing; a score at the inlet goes straight out of outlet 0
  repeat                 the last score sent, out of outlet 0 again
  input dictionary <n>   passed through while bypassed, otherwise ignored (a generator takes no input)
  write_to_playground    write the last score sent to <playground>/scores/<name>.json
  auto_dump 0/1          output on every parameter change (default 1); 0: only on dump
  verbose 0/1            say in the Max console what happens (default 0: only errors)
  watch 0/1              reload when the file changes on disk (default 1)
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

const engine = createEngine(
  { outlet: (...a) => outlet(...a), post: (...a) => post(...a), messnamed: (...a) => messnamed(...a), Dict, Task, File },
  { name: "generator", accepts: "producer", needs: "function produce(p) { ... }" },
);

try {
  setinletassist(0, "load <path>, run, [param] <param> <value>");
  setoutletassist(0, "dictionary <name>: the score (bachjson-complete)");
  setoutletassist(1, "to the parameter panel (bachmcp.gui.params.v8ui.js)");
  setoutletassist(2, "<name> algo_loaded / algo_done / algo_error");
} catch (e) {
  // assist strings are optional
}

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
function bypass(on) { engine.setBypass(on); }
function repeat() { engine.repeat(); }
function input(what, name) {
  if (engine.state.bypass && what === "dictionary") engine.passThrough(name);
}
function write_to_playground() { engine.writeScore(); }
function notifydeleted() { engine.deleted(); }
function done() {} // end of patcherargs' attribute list
