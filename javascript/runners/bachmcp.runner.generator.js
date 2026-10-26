/*
bachmcp.runner.generator.js
---------------------------
The generator runner ([v8], inside bachmcp.algo.gen). It runs an algorithm that
makes music from nothing: a file that defines `function produce(p) { ... }`. A
file of another kind is refused. Everything else is the engine's
(bachmcp.runner.engine.js), which also lists the outlets.

Messages:
  setname <name> [file]  the instance's name (and a file to load)
  load <path>            load and run a file
  reload                 read the file again
  run, bang              run with the current values
  <param> <value...>     set a parameter, e.g. "times 32", "register 4800 8400"
  auto 0/1               run on every parameter change (default 1)
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
  setinletassist(0, "load <path>, run, <param> <value>");
  setoutletassist(0, "dictionary <name>: the score (bachjson-complete)");
  setoutletassist(1, "to the parameter panel (bachmcp.gui.params.jsui.js)");
  setoutletassist(2, "<name> algo_loaded / algo_done / algo_error");
} catch (e) {
  // assist strings are optional
}

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
