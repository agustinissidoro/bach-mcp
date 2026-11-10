/*
bachmcp.runner.js
-----------------
The runner: one [v8] that runs an algorithm file, and is a generator, a
transformer or a selector depending on its type.

    [v8 bachmcp.runner.js generator]     (or transformer, selector; or @type <t>)

  generator     a file with function produce(p) { ... }: music from nothing
  transformer   a file with function transform(source, p) { ... }: changes the score at the inlet
  selector      a file with function select(source, p) { ... }: picks notes of the score at the inlet

"type <t>" changes it: what the old type held (source, selection) goes, and a
loaded file must be of the new type (otherwise algo_error). A file of another
type is refused.

The parts: what every type does is bachmcp.runner.engine.js; what a type adds
is bachmcp.runner.type.<type>.js; the source a transformer and a selector share
is bachmcp.runner.source.js. This file is only what Max sees: the outlets and
the messages.

Outlets, the same for every type:
  0  only scores: dictionary <name> (bachjson-complete)
  1  to bach.roll: dump (asks for its score), clearselection, sel note [v c n] ...
  2  to bachmcp.gui.params: spec, set, status, type, and every setting's value back
  3  bang: a process is done, after its score (and a selector's commands)
  4  dumpout: <name> algo_loaded / algo_done / algo_error / error / processing / timeout / specs

A load is not a run: it says algo_loaded (outlet 4), and nothing goes out
until a bang (a patch that wants a score on load catches algo_loaded). bang outputs the score of the current settings: the last one again if nothing
changed since, otherwise a new run. A parameter change outputs a score only
with auto_dump 1 (the default).

Messages, every type:
  type generator|transformer|selector
  set_name <name> [file]    the instance's name (and a file to load)
  load <path>               load a file
  load_algo <path>          the same; a failure is "error: impossible to load ..."
  try_load_algo <path>      the same, silent: a file that cannot be loaded is ignored
  reload                    read the file again
  get_specs                 the loaded algorithm's spec again, out of outlet 2, with the current values
                            (for a panel that was not listening at load); always answers on dumpout:
                            <name> specs 1 (sent) or <name> specs 0 (no algorithm loaded)
  bang, dump                the score of the current settings (see above)
  run                       run the algorithm now, changed or not
  repeat                    the last score sent, again
  param <name> <value...>   set a parameter, e.g. "param times 32", "param register 4800 8400":
                            parameters come in only this way, so any name is free for them
  auto_dump 0/1             1 (default): a parameter change outputs a score; 0: only bang does
  snap 0/1/3                the output's pitches: 0 semitones, 1 quarter tones, 3 free (default)
  bypass 0/1                1: runs do nothing; a score at the inlet goes straight out of outlet 0
  sync <message...>         the panel's values after a load: param, snap, bypass, source_mode,
                            process_only_selection, dump_selection_only, applied without a run
  write_to_playground       write the last score sent to <playground>/scores/<name>.json
  verbose 0/1               say in the Max console what happens (default 0: only errors)
  watch 0/1                 reload when the file changes on disk (default 1)
Settings: every runner takes them, at any time (before its type, too), and keeps
them across a type change; a type that does not use one ignores it:
  source_mode 0/1           transformer, selector: 0 destructive, 1 non-destructive (default)
  process_only_selection 0/1  transformer, selector: 1 work only on the selected notes (flag 16)
  dump_selection_only 0/1   selector: the score out, the selected notes (1, default) or the whole source flagged
  involutive 0/1            selector: kept for later; ignored for now
  input_mode 0/1, selection_slot <n>   old names (process_only_selection; nothing), kept for old patches

Actions: only the types that have them take them.
  dictionary <name>         every type: a score in (a generator only passes it through while bypassed);
                            input dictionary <name> is its old form, kept for old patches
  input clear               transformer, selector: forget the source
  capture                   transformer, selector: "dump" to the roll; the next input becomes the source
  dump_selection            selector: the selected notes as a score, out of outlet 0
  clear_selection           selector: nothing selected any more

A message the type does not take, or no runner takes (a bare "times 32", say), is
refused: <name> error <message>, out of outlet 4.
*/
"use strict";

autowatch = 1;
inlets = 1;
outlets = 5;

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
const TYPES = {
  generator: need("bachmcp.runner.type.generator.js").create,
  transformer: need("bachmcp.runner.type.transformer.js").create,
  selector: need("bachmcp.runner.type.selector.js").create,
};

const engine = createEngine({
  outlet: (...a) => outlet(...a), post: (...a) => post(...a), Dict, Task, File,
});

try {
  setinletassist(0, "type, load_algo <path>, bang, param <param> <value>, dictionary <name>, capture ...");
  setoutletassist(0, "dictionary <name>: the score (bachjson-complete)");
  setoutletassist(1, "to bach.roll: dump, clearselection, sel note ...");
  setoutletassist(2, "to the parameter panel (bachmcp.gui.params)");
  setoutletassist(3, "bang: a process is done (after its score)");
  setoutletassist(4, "dumpout: <name> algo_loaded / algo_done / algo_error / error / processing / timeout");
} catch (e) {
  // assist strings are optional
}

// ── The type ────────────────────────────────────────────────────────────── //

/** type generator|transformer|selector: what the runner is (and loads) from now on. */
function type(name) { becomeType(name, false); }

/** quiet: nothing to the panel (the box's argument, while the patch is still loading). */
function becomeType(name, quiet) {
  const t = String(name);
  if (!TYPES[t]) return engine.refuse(`type is generator, transformer or selector, got ${name}`);
  if (engine.type && engine.type.name === t) return;
  engine.setType(TYPES[t](engine), quiet);
}
becomeType.local = 1;  // not a message

/** A message only some types take: the current type's, or refused. */
function forType(name, args) {
  const t = engine.type;
  if (!t) return engine.refuse(`${name}: no type yet (type generator, transformer or selector)`);
  const fn = t.messages && t.messages[name];
  if (!fn) return engine.refuse(`${name}: a ${t.name} does not take it`);
  fn(...args);
}

// The box's arguments: [v8 bachmcp.runner.js transformer] or [v8 bachmcp.runner.js @type transformer].
(function fromArguments(args) {
  const at = args.indexOf("@type");
  const given = at >= 0 ? args[at + 1] : args[1];
  if (given !== undefined && !String(given).startsWith("@")) becomeType(given, true);
})(Array.from(jsarguments || []));

// ── Every type ──────────────────────────────────────────────────────────── //

function set_name(name, file) { engine.setname(name, file); }
function load(path) { engine.load(path); }
function load_algo(path) { engine.loadAlgo(path); }
function try_load_algo(path) { engine.tryLoadAlgo(path); }
function reload() { engine.reload(); }
function get_specs() { engine.getSpecs(); }
function bang() { engine.bang(); }
function dump() { engine.bang(); }
function run() { engine.runNow(); }
function repeat() { engine.repeat(); }
function auto_dump(on) { engine.autoDump(on); }
function snap(n) { engine.setSnap(n); }
function bypass(on) { engine.setBypass(on); }
function write_to_playground() { engine.writeScore(); }
function verbose(on) { engine.verbose(on); }
function watch(on) { engine.watch(on); }
function param(name, ...args) {
  if (name === undefined) return engine.refuse("param needs a name: param <name> <value...>");
  engine.setParam(String(name), args);
}
function anything() {
  engine.refuse(`${messagename}: not a message of the runner (a parameter is set with param ${messagename} <value...>)`);
}
function notifydeleted() { engine.deleted(); }

/** The panel's values after a load (it sends what it holds that differs): applied, never run. */
function sync(name, ...args) {
  const fn = SYNCED[String(name)];
  if (!fn) return engine.refuse(`sync: ${name} cannot be synced`);
  engine.quietly(() => fn(...args));
}
const SYNCED = { param, snap, bypass, source_mode, process_only_selection, dump_selection_only };
function done() {} // end of patcherargs' attribute list

// ── Settings: every type takes them ─────────────────────────────────────── //

function source_mode(value) { engine.setSourceMode(value); }
function process_only_selection(value) { engine.setProcessOnlySelection(value); }
function input_mode(value) { engine.setProcessOnlySelection(value); }  // its old name, kept for old patches
function selection_slot() {}  // ignored: the selection is bach's flag 16 now (old patches send it)
function dump_selection_only(value) { engine.setDumpSelectionOnly(value); }
function involutive(value) { engine.setInvolutive(value); }

// ── Actions: some types ─────────────────────────────────────────────────── //

function dictionary(...args) { forType("dictionary", args); }
function input(...args) { forType("input", args); }
function capture(...args) { forType("capture", args); }
function dump_selection(...args) { forType("dump_selection", args); }
function clear_selection(...args) { forType("clear_selection", args); }

