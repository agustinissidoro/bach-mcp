/*
bachmcp.runner.engine.js
------------------------
What the runner does, whatever its type: load an algorithm file (with the
loader and the algorithmic core library), check that it is of the runner's
type, hand its parameters to the panel, run it again when asked, and say what
happened. The runner ([v8] bachmcp.runner.js) creates one engine and gives it a
type (bachmcp.runner.type.*.js), which adds only what that type needs. Text
files are read and written by bachmcp.runner.files.js.

    const engine = createEngine(max)
    engine.setType(type)

max: what the runner's [v8] has and a module does not (outlet, post, messnamed,
Dict, Task, File), passed in by the runner.

type: what the runner is now:
    name        "generator" | "transformer" | "selector"   shown in the Max console and in errors
    needs       how such a file starts, for the error, e.g. "function produce(p) { ... }"
    messages    {name: fn}: the messages only this type takes (see bachmcp.runner.js)
  and the hooks, all optional:
    source()            the score a run works on (a transformer's or a selector's source)
    output(score)       a run's score -> the score sent (process_only_selection 1 puts back the rest)
    spec()              more to tell the panel with the algorithm's spec
    request()           before a run; true if the type asked the roll for the score and calls process() when it comes
    stale()             true: the last output cannot be trusted (the roll may have changed), so bang runs again
    ran(result)         after a run, with the loader's result ({score} or a selector's {selection});
                        a selector sends what the run made itself, the engine sends only scores
    repeated()          after the last score is sent again: what else the type sends (a selector's commands)
    bypassed(on)        bypass changed
    setting(name)       a setting of the types with a source changed (source_mode ...)
    deleted()           the type is replaced, or the object deleted: stop what it started

The outlets, the same for every type:
    0  SCORE    dictionary <name>                           only scores (bachjson-complete)
    1  BACH     dump, clearselection, sel note [v c n] ...  to bach.roll
    2  PANEL    spec, set, status, source, the settings,    to bachmcp.gui.params
                clear (the type changed with a file loaded)
    3  DONE     bang                                        a process is done: after its score (and a selector's commands)
    4  STATUS   <name> algo_loaded <file>                   dumpout: what happened, debugging, errors
                <name> algo_done <notes> <ms>
                <name> algo_error <message>                 the algorithm could not load or run
                <name> error <message>                      a message the runner cannot take
                <name> processing 0|1, <name> timeout 1     waiting for the roll's score

Running. A load is not a run: it compiles the file and says algo_loaded (outlet
4); a patch that wants a score then sends bang. bang outputs the score the
algorithm gives with the current settings: the last one again if nothing
changed since (no run), otherwise a new run. A parameter change outputs a
score only with auto_dump 1 (the default); with auto_dump 0 it only marks the
settings as changed, for the next bang. run always runs. repeat always sends
the last score again.

The done bang (outlet 3) closes every process, after everything it sent: a
run, and a bang that sent the last score again. It does not come after a run
that failed (algo_error), nor after repeat, a score passed through while
bypassed, or a selector's dump_selection and clear_selection.

Every type also takes bypass 0/1 (runs do nothing; a score at the inlet goes
straight out of outlet 0, see passThrough) and snap 0/1/3: the pitches of every
score sent rounded to semitones (0), quarter tones (1) or left free (3, default).

The last score sent is also kept in a dict of its own (lastScore), for bang,
repeat and write_to_playground: writeScore() writes it to the playground's
scores folder, <playground>/scores/<name>.json (the algorithm is in
<playground>/algorithms/).
*/
"use strict";

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

const loader = need("bachmcp.runner.loader.js");
const paramspec = need("bachmcp.runner.paramspec.js");
const { makeFiles, basename } = need("bachmcp.runner.files.js");
const { copy } = need("bachmcp.lib.build.js");

const OUT = { SCORE: 0, BACH: 1, PANEL: 2, DONE: 3, STATUS: 4 };
const DEBOUNCE_MS = 20;
const WATCH_MS = 1000;
const SNAP_STEPS = { 0: 100, 1: 50, 3: 0 };  // snap -> midicents (0: free)

/** Every note's pitch rounded to a step of midicents, in place. */
function snapPitches(score, step) {
  if (!step) return;
  const round = (x) => (typeof x === "number" ? Math.round(x / step) * step : x);
  for (const v of (score && score.voices) || []) {
    for (const c of (v && v.chords) || []) {
      for (const n of (c && c.notes) || []) {
        if (n) n.pitch = round(n.pitch);
      }
    }
  }
}

/** A 0/1 flag from a message, or null. */
function flag(x) {
  const m = Number(x);
  return m === 0 || m === 1 ? m : null;
}

function createEngine(max) {
  const files = makeFiles(max.File);
  let type = null;
  const state = {
    name: "algo",        // the instance's name, from set_name
    path: "",            // the algorithm file
    text: "",
    compiled: null,
    values: {},
    autorun: true,       // auto_dump 1: a change outputs a score
    syncing: false,      // inside sync: changes are applied, never run (see quietly)
    changed: true,       // something changed since the last run: bang runs instead of sending the last score
    watching: true,
    loading: false,      // inside load_algo: a file that does not compile is "impossible to load"
    bypass: false,       // bypass 1: runs do nothing, inputs pass through
    snap: 3,             // the output's pitches: 0 semitones, 1 quarter tones, 3 free
    // Settings of the types with a source (transformer, selector), kept here so that every
    // runner takes them, at any time (before its type, too) and keeps them across a type change:
    destructive: false,  // source_mode 0: every run asks the roll for its score
    selectedOnly: false, // process_only_selection 1: a run sees only the selected notes
    selectionOnly: true, // dump_selection_only 1: a selector sends only the selected notes
    involutive: false,   // involutive 1: kept for later, ignored for now
    verbose: false,      // verbose 1: say in the Max console what happens (errors are always said)
  };
  const scoreDict = new max.Dict();
  const lastScore = new max.Dict();
  const pending = new max.Task(autoRun);
  const watcher = new max.Task(checkFile);
  watcher.interval = WATCH_MS;

  // ── Saying what happened ─────────────────────────────────────────────── //

  function post(message) {
    max.post(`${type ? type.name : "runner"} ${state.name}: ${message}\n`);
  }

  function say(message) {
    if (state.verbose) post(message);
  }

  function status(...atoms) {
    max.outlet(OUT.STATUS, state.name, ...atoms);
  }

  function report(what, e) {
    const message = typeof e === "string" ? e : (e.message || String(e)) + (e.line ? ` (line ${e.line})` : "");
    post(`error: ${message}`);
    max.outlet(OUT.PANEL, "status", "error", message);
    status(what, message);
  }

  /** The algorithm could not be loaded or run: algo_error. */
  function fail(e) {
    report("algo_error", e);
  }

  /** A message the runner cannot take (a bad value, a message of another type): error. */
  function refuse(e) {
    report("error", e);
  }

  /** A setting the panel shows: its value back to the panel. */
  function tellPanel(name, ...atoms) {
    max.outlet(OUT.PANEL, name, ...atoms);
  }

  // ── The type ─────────────────────────────────────────────────────────── //

  /**
   * The runner becomes another type: what the old one held goes, a loaded file must be of the new one.
   * quiet: nothing to the panel (the box's argument, while the patch is still loading).
   */
  function setType(next, quiet = false) {
    if (type && type.deleted) type.deleted();
    type = next;
    pending.cancel();
    state.changed = true;
    if (!quiet) tellPanel("type", type.name);
    if (!state.text) return;
    const before = state.compiled;
    state.compiled = null;
    tellPanel("clear");  // the old type's panel: a file of the new type rebuilds it
    compile(before);
  }

  function hook(name, ...args) {
    return type && typeof type[name] === "function" ? type[name](...args) : undefined;
  }

  // ── Messages ──────────────────────────────────────────────────────────── //

  function setname(name, file) {
    state.name = String(name);
    if (file !== undefined && !state.path) load(file);
  }

  function load(path) {
    if (path === undefined) return fail("load needs a file path");
    const text = files.read(String(path));
    if (text === null) return fail(`cannot read ${path}`);
    take(path, text);
  }

  /** load, but a file that cannot be read or compiled is reported as "impossible to load". */
  function loadAlgo(path) {
    if (path === undefined) return fail("error: impossible to load: load_algo needs a file path");
    const text = files.read(String(path));
    if (text === null) return fail(`error: impossible to load ${path}: cannot read it`);
    state.loading = true;
    try {
      take(path, text);
    } finally {
      state.loading = false;
    }
  }

  /** load, silently: a file that cannot be read, or is not a working file of this type, is ignored. */
  function tryLoadAlgo(path) {
    if (path === undefined || !type) return;
    const text = files.read(String(path));
    if (text === null) return;
    try {
      if (loader.compile(text).type !== type.name) return;
    } catch (e) {
      return;
    }
    take(path, text);
  }

  function take(path, text) {
    state.path = String(path);
    state.text = text;
    compile();
    if (state.watching) watcher.repeat();
  }

  function reload() {
    if (!state.path) return fail("nothing loaded");
    load(state.path);
  }

  function verbose(on) {
    state.verbose = Boolean(Number(on));
  }

  /** auto_dump 1 (default): a parameter change outputs a score; 0: only bang does. */
  function autoDump(on) {
    const m = flag(on);
    if (m === null) return refuse(`auto_dump is 0 or 1, got ${on}`);
    state.autorun = m === 1;
    tellPanel("auto_dump", m);
  }

  function watch(on) {
    state.watching = Boolean(Number(on));
    if (state.watching && state.path) watcher.repeat();
    else watcher.cancel();
  }

  function setParam(name, args) {
    const compiled = state.compiled;
    if (!compiled) return refuse(`no algorithm loaded (received "param ${name}")`);
    const spec = compiled.specs.find((s) => s.name === name);
    if (!spec) {
      return refuse(`"${name}" is not a parameter. Parameters: ${compiled.specs.map((s) => s.name).join(", ")}`);
    }
    try {
      state.values[name] = paramspec.coerce(spec, args);
    } catch (e) {
      return refuse(e);
    }
    tellPanel("set", name, ...paramspec.valueAtoms(spec, state.values[name]));
    changed();
  }

  /** Something the output depends on changed: the next bang runs, and with auto_dump 1 a run is scheduled. */
  function changed() {
    state.changed = true;
    if (state.autorun && state.compiled && !state.syncing) schedule();
  }

  /**
   * fn's changes are applied but run nothing, whatever auto_dump says: for sync, the panel
   * telling the runner the values it holds after a load (a load is not a run).
   */
  function quietly(fn) {
    state.syncing = true;
    try {
      fn();
    } finally {
      state.syncing = false;
    }
  }

  /** bypass 1: no runs; what comes in passes straight through (passThrough). */
  function setBypass(on) {
    const m = flag(on);
    if (m === null) return refuse(`bypass is 0 or 1, got ${on}`);
    state.bypass = m === 1;
    if (state.bypass) pending.cancel();
    hook("bypassed", state.bypass);
    tellPanel("bypass", m);
  }

  /** snap 0 semitones, 1 quarter tones, 3 free: the output's pitches. */
  function setSnap(n) {
    const m = Number(n);
    if (!(m in SNAP_STEPS)) return refuse(`snap is 0 (semitones), 1 (quarter tones) or 3 (free), got ${n}`);
    state.snap = m;
    tellPanel("snap", m);
    changed();
  }

  // ── Settings of the types with a source ──────────────────────────────── //
  // Every runner takes them: a generator keeps them unused, a type uses what it needs.

  /** source_mode 0 destructive (every run asks the roll), 1 non-destructive (the source is held). */
  function setSourceMode(value) {
    const m = flag(value);
    if (m === null) return refuse(`source_mode is 0 (destructive) or 1 (non-destructive), got ${value}`);
    state.destructive = m === 0;
    hook("setting", "source_mode");
    tellPanel("source_mode", m);
  }

  /** process_only_selection 0 the whole score (default), 1 only its selected notes. */
  function setProcessOnlySelection(value) {
    const m = flag(value);
    if (m === null) return refuse(`process_only_selection is 0 (the whole score) or 1 (only the selected notes), got ${value}`);
    state.selectedOnly = m === 1;
    tellPanel("process_only_selection", m);
    changed();
  }

  /** dump_selection_only: a selector's score out, the selected notes (1, default) or the whole source flagged (0). */
  function setDumpSelectionOnly(value) {
    const m = flag(value);
    if (m === null) return refuse(`dump_selection_only is 0 or 1, got ${value}`);
    state.selectionOnly = m === 1;
    tellPanel("dump_selection_only", m);
    changed();
  }

  /** involutive 0: sel (adds to the selection), 1: select (toggles). Kept for later: ignored for now. */
  function setInvolutive(value) {
    const m = flag(value);
    if (m === null) return refuse(`involutive is 0 (sel) or 1 (select), got ${value}`);
    state.involutive = m === 1;
    tellPanel("involutive", m);
  }

  /** A score at the inlet while bypassed: out of outlet 0 as it came. */
  function passThrough(name) {
    max.outlet(OUT.SCORE, "dictionary", String(name));
  }

  function hasLastScore() {
    const text = lastScore.stringify();
    return Boolean(text && text !== "{}" && JSON.parse(text).voices);
  }

  /** bang: the score of the current settings. The last one again if nothing changed, else a run. */
  function bang() {
    if (!state.compiled || state.bypass) return runNow();
    if (!state.changed && hasLastScore() && !hook("stale")) {
      repeat();
      return done();
    }
    runNow();
  }

  /** A process is done: the bang, after its score. */
  function done() {
    max.outlet(OUT.DONE, "bang");
  }

  /** repeat: the last score sent, out of outlet 0 again (and what the type sends with it). */
  function repeat() {
    if (!hasLastScore()) return refuse("repeat: no score sent yet");
    sendScore(JSON.parse(lastScore.stringify()));
    hook("repeated");
  }

  function deleted() {
    pending.cancel();
    watcher.cancel();
    hook("deleted");
  }

  // ── Compiling and running ─────────────────────────────────────────────── //

  function compile(before = state.compiled) {
    if (!type) return fail("no type: send type generator, transformer or selector");
    let next;
    try {
      next = loader.compile(state.text);
      if (next.type !== type.name) {
        throw new Error(`this is a ${type.name}: the file must define ${type.needs}`);
      }
    } catch (e) {
      return fail(state.loading ? `error: impossible to load ${basename(state.path)}: ${e.message || e}` : e);
    }
    state.values = keptValues(next, before);
    state.compiled = next;
    state.changed = true;
    const params = next.specs.map((s) => Object.assign({}, s, { value: state.values[s.name] }));
    tellPanel("spec", JSON.stringify(Object.assign({
      title: basename(state.path).replace(/\.js$/, ""), description: next.description || "", path: state.path,
      type: next.type, params,
    }, hook("spec") || {})));
    say(`loaded ${basename(state.path)}: ${paramspec.describe(next.specs, state.values).join("; ")}`);
    status("algo_loaded", basename(state.path));  // a load is not a run: bang for a score
  }

  /**
   * The values for a new version of the file (saved while watched, or reloaded).
   * A value the user set (it differs from the old default) carries over when the
   * parameter still means the same: same name, type, kind and unit; clamped to the
   * new range, a menu's only if its option is still there (by name, never by
   * position). Everything else takes the file's (possibly new) default, so a
   * default edited in the file shows at once.
   */
  function keptValues(next, before) {
    const kept = {};
    for (const spec of next.specs) {
      kept[spec.name] = copy(spec.default);
      const old = before && before.specs.find((s) => paramspec.sameMeaning(s, spec));
      const value = state.values[spec.name];
      if (!old || value === undefined || JSON.stringify(value) === JSON.stringify(old.default)) continue;
      if (spec.type === "menu") {
        const hit = spec.options.find((o) => String(o) === String(value));
        if (hit !== undefined) kept[spec.name] = hit;
        continue;
      }
      try {
        kept[spec.name] = paramspec.coerce(spec, paramspec.valueAtoms(old, value));
      } catch (e) {
        // not a value of the new declaration: the default
      }
    }
    return kept;
  }

  function schedule() {
    pending.cancel();
    pending.schedule(DEBOUNCE_MS);
  }

  /** The output a change asked for (auto_dump 1). */
  function autoRun() {
    if (state.bypass) return;
    runNow();
  }

  /** A run: unless the type first asks the roll for the score (request), then runs when it comes in. */
  function runNow() {
    pending.cancel();
    if (!state.compiled || state.bypass) return;
    if (hook("request")) return;
    process();
  }

  /** Run on the score in hand: the score out of outlet 0. */
  function process() {
    pending.cancel();
    if (!state.compiled || state.bypass) return;
    let result;
    try {
      result = loader.run(state.compiled, state.values, hook("source") || null);
      if (result.score && type.output) result.score = type.output(result.score);
    } catch (e) {
      return fail(e);
    }
    state.changed = false;
    const what = result.score ? "notes" : "notes selected";
    tellPanel("status", "ok", `${result.notes} ${what}, ${result.ms} ms`);
    status("algo_done", result.notes, result.ms);
    hook("ran", result);  // a selector sends its score and commands
    if (result.score) sendScore(result.score);
    done();
  }

  /** A score out of outlet 0, as dictionary <name>. */
  function sendScore(score) {
    snapPitches(score, SNAP_STEPS[state.snap]);
    scoreDict.clear();
    scoreDict.parse(JSON.stringify(score));
    lastScore.clear();
    lastScore.parse(JSON.stringify(score));
    max.outlet(OUT.SCORE, "dictionary", scoreDict.name);
  }

  /** write_to_playground: the last score sent, to <playground>/scores/<name>.json. */
  function writeScore() {
    if (!state.path) return refuse("write_to_playground: no algorithm loaded, so no playground to write to");
    if (!hasLastScore()) return refuse("write_to_playground: no score sent yet");
    const playground = state.path.replace(/[^\/:]*$/, "").replace(/[^\/:]+[\/:]$/, "");
    const path = playground + "scores/" + state.name + ".json";
    if (!files.write(path, lastScore.stringify())) return fail(`could not write ${path}`);
    tellPanel("status", "ok", `score written to ${path}`);
  }

  function checkFile() {
    if (!state.path || !state.watching) return;
    const text = files.read(state.path);
    if (text !== null && text !== state.text) {
      state.text = text;
      say(`${basename(state.path)} changed on disk`);
      compile();
    }
  }

  return {
    OUT, state, files, max,
    say, fail, refuse, status, tellPanel, flag,
    setType, setname, load, loadAlgo, tryLoadAlgo, reload, autoDump, verbose, watch, setParam,
    changed, quietly, setBypass, setSourceMode, setProcessOnlySelection, setDumpSelectionOnly, setInvolutive, setSnap, passThrough, bang, repeat, runNow, process, schedule, sendScore, writeScore, deleted,
    get type() { return type; },
  };
}

module.exports = { createEngine, OUT, flag };
