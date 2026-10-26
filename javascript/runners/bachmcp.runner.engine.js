/*
bachmcp.runner.engine.js
------------------------
What every runner does, whatever its kind: load an algorithm file (with the
loader and the algorithmic core library), check that it is the runner's kind,
hand its parameters to the panel, run it again when a parameter changes or the
file changes on disk, and say what happened. Each runner (generator,
transformer, later selector) is a small [v8] script that adds only what its
kind needs. Text files are read and written by bachmcp.runner.files.js.

    const engine = createEngine(max, kind, hooks)

max: what the runner's [v8] has and a module does not (outlet, post, messnamed,
Dict, Task, File), passed in by the runner.

kind: what the runner takes:
    name      "generator" | "transformer"     shown in the Max console and in errors
    accepts   "producer" | "transformer"      the kind the loader must find in the file
    needs     how such a file starts, for the error, e.g. "function produce(p) { ... }"

hooks (all optional), for what the kind adds:
    source()            the score a run works on (a transformer's source)
    spec()              more to tell the panel, e.g. {source: {notes, from}}
    loaded()            after a file compiled; true if the hook starts the first run itself
    forget()            a different file is loaded: drop what belonged to the old one
    deleted()           the object is deleted: stop what the hook started
    automatic()         false holds back an output a parameter change asked for (auto_dump)
    ran(score)          after a run, with the score it made

The runner's outlets:
    0  dictionary <name>                         the score (bachjson-complete)
    1  spec / set / status ...                   the parameter panel (GUI_parameters/)
    2  <name> algo_loaded <file> <notes> <ms>    what happened, for the patch and the server,
       <name> algo_done <notes> <ms>             which waits for algo_loaded or algo_error
       <name> algo_error <message>               after a load
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

const DEBOUNCE_MS = 20;
const WATCH_MS = 1000;

function createEngine(max, kind, hooks = {}) {
  const files = makeFiles(max.File);
  const state = {
    name: "algo",        // the instance's name, from set_name
    path: "",            // the algorithm file
    text: "",
    compiled: null,
    values: {},
    autorun: true,
    watching: true,
    fresh: false,        // the next run is the first of a load: algo_loaded, not algo_done
    loading: false,
    verbose: false,      // verbose 1: say in the Max console what happens (errors are always said)      // inside load_algo: a file that does not compile is "impossible to load"
  };
  const scoreDict = new max.Dict();
  const pending = new max.Task(autoRun);
  const watcher = new max.Task(checkFile);
  watcher.interval = WATCH_MS;

  // ── Saying what happened ─────────────────────────────────────────────── //

  function post(message) {
    max.post(`${kind.name} ${state.name}: ${message}\n`);
  }

  function say(message) {
    if (state.verbose) post(message);
  }

  function fail(e) {
    const message = typeof e === "string" ? e : (e.message || String(e)) + (e.line ? ` (line ${e.line})` : "");
    post(`error: ${message}`);
    max.outlet(1, "status", "error", message);
    max.outlet(2, state.name, "algo_error", message);
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

  /** load, silently: a file that cannot be read, or is not a working file of this kind, is ignored. */
  function tryLoadAlgo(path) {
    if (path === undefined) return;
    const text = files.read(String(path));
    if (text === null) return;
    try {
      if (loader.compile(text).kind !== kind.accepts) return;
    } catch (e) {
      return;
    }
    take(path, text);
  }

  function take(path, text) {
    if (String(path) !== state.path && hooks.forget) hooks.forget();
    state.path = String(path);
    state.text = text;
    state.fresh = true;
    compile();
    if (state.watching) watcher.repeat();
  }

  function reload() {
    if (!state.path) return fail("nothing loaded");
    load(state.path);
  }

  /** verbose 1: what happens is said in the Max console; 0 (default): only errors. */
  function verbose(on) {
    state.verbose = Boolean(Number(on));
  }

  /** auto_dump 1: a parameter change outputs a score; 0: only dump (or bang) does. */
  function autoDump(on) {
    state.autorun = Boolean(Number(on));
  }

  function watch(on) {
    state.watching = Boolean(Number(on));
    if (state.watching && state.path) watcher.repeat();
    else watcher.cancel();
  }

  function setParam(name, args) {
    const compiled = state.compiled;
    if (!compiled) return fail(`no algorithm loaded (received "${name}")`);
    const spec = compiled.specs.find((s) => s.name === name);
    if (!spec) {
      return fail(`"${name}" is not a parameter. Parameters: ${compiled.specs.map((s) => s.name).join(", ")}`);
    }
    try {
      state.values[name] = paramspec.coerce(spec, args);
    } catch (e) {
      return fail(e);
    }
    max.outlet(1, "set", name, ...paramspec.valueAtoms(spec, state.values[name]));
    if (state.autorun) schedule();
  }

  function deleted() {
    pending.cancel();
    watcher.cancel();
    if (hooks.deleted) hooks.deleted();
  }

  // ── Compiling and running ─────────────────────────────────────────────── //

  function compile() {
    let next;
    try {
      next = loader.compile(state.text);
      if (next.kind !== kind.accepts) {
        throw new Error(`this is a ${kind.name}: the file must define ${kind.needs}`);
      }
    } catch (e) {
      state.fresh = false;
      return fail(state.loading ? `error: impossible to load ${basename(state.path)}: ${e.message || e}` : e);
    }
    state.values = keptValues(next);
    state.compiled = next;
    const params = next.specs.map((s) => Object.assign({}, s, { value: state.values[s.name] }));
    max.outlet(1, "spec", JSON.stringify(Object.assign({
      title: basename(state.path).replace(/\.js$/, ""), path: state.path, kind: next.kind, params,
    }, hooks.spec ? hooks.spec() : {})));
    say(`loaded ${basename(state.path)}: ${paramspec.describe(next.specs, state.values).join("; ")}`);
    if (!(hooks.loaded && hooks.loaded())) runNow();
  }

  /** The values for a new version of the file: a parameter that keeps its name and type keeps its value. */
  function keptValues(next) {
    const kept = {};
    const before = state.compiled;
    for (const spec of next.specs) {
      const old = before && before.specs.find((s) => s.name === spec.name && s.type === spec.type);
      kept[spec.name] = copy(spec.default);
      if (old && state.values[spec.name] !== undefined) {
        try {
          kept[spec.name] = paramspec.coerce(spec, paramspec.valueAtoms(old, state.values[spec.name]));
        } catch (e) {
          // out of the new options: back to the default
        }
      }
    }
    return kept;
  }

  function schedule() {
    pending.cancel();
    pending.schedule(DEBOUNCE_MS);
  }

  /** The output a parameter change asked for, unless the runner's kind holds it back. */
  function autoRun() {
    if (hooks.automatic && !hooks.automatic()) return;
    runNow();
  }

  function runNow() {
    pending.cancel();
    if (!state.compiled) return;
    let result;
    try {
      result = loader.run(state.compiled, state.values, hooks.source ? hooks.source() : null);
    } catch (e) {
      state.fresh = false;
      return fail(e);
    }
    scoreDict.clear();
    scoreDict.parse(JSON.stringify(result.score));
    max.outlet(1, "status", "ok", `${result.notes} notes, ${result.ms} ms`);
    if (state.fresh) max.outlet(2, state.name, "algo_loaded", basename(state.path), result.notes, result.ms);
    else max.outlet(2, state.name, "algo_done", result.notes, result.ms);
    state.fresh = false;
    if (hooks.ran) hooks.ran(result.score);  // before the score: it may come straight back
    max.outlet(0, "dictionary", scoreDict.name);
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
    state, files, say, fail, schedule, runNow,
    setname, load, loadAlgo, tryLoadAlgo, reload, autoDump, verbose, watch, setParam, deleted,
  };
}

module.exports = { createEngine };
