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
    name      "generator" | "transformer" | "selector"   shown in the Max console and in errors
    accepts   "producer" | "transformer" | "selector"    the kind the loader must find in the file
    needs     how such a file starts, for the error, e.g. "function produce(p) { ... }"
    panel     the panel's outlet (default 1)
    status    the status outlet (default 2)

hooks (all optional), for what the kind adds:
    source()            the score a run works on (a transformer's source)
    spec()              more to tell the panel, e.g. {source: {notes, from}}
    loaded()            after a file compiled; true: no run on load
    request()           before a run; true if the hook asked for the score first and calls process() when it comes
    forget()            a different file is loaded: drop what belonged to the old one
    deleted()           the object is deleted: stop what the hook started
    automatic()         false holds back an output a parameter change asked for (auto_dump)
    output(score)       a run's score -> the score sent (process_only_selection 1 puts back the rest)
    ran(result)         after a run, with the loader's result ({score} or a selector's {selection});
                        a selector's hook sends what the run made, the engine sends only scores

The runner's outlets (a selector's panel and status are 2 and 3, see its runner):
    0  dictionary <name>                         the score (bachjson-complete)
    1  spec / set / status ...                   the parameter panel (GUI_parameters/)
    2  <name> algo_loaded <file> <notes> <ms>    what happened, for the patch and the server,
       <name> algo_done <notes> <ms>             which waits for algo_loaded or algo_error
       <name> algo_error <message>               after a load

Every runner also takes bypass 0/1 (runs do nothing; a score at the inlet goes
straight out of outlet 0, see passThrough) and repeat (the last score sent, out
of outlet 0 again), and snap 0/1/3: the pitches of every score sent rounded to semitones (0), quarter tones (1) or left free (3, default).

The last score sent is also kept in a dict of its own (lastScore), used only by
write_to_playground: writeScore() writes it to the playground's scores folder,
<playground>/scores/<name>.json (the algorithm is in <playground>/algorithms/).
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
    bypass: false,       // bypass 1: runs do nothing, inputs pass through
    snap: 3,             // the output's pitches: 0 semitones, 1 quarter tones, 3 free
    verbose: false,      // verbose 1: say in the Max console what happens (errors are always said)      // inside load_algo: a file that does not compile is "impossible to load"
  };
  const PANEL = kind.panel === undefined ? 1 : kind.panel;
  const STATUS = kind.status === undefined ? 2 : kind.status;
  const scoreDict = new max.Dict();
  const lastScore = new max.Dict();  // only for write_to_playground
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
    max.outlet(PANEL, "status", "error", message);
    max.outlet(STATUS, state.name, "algo_error", message);
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
    max.outlet(PANEL, "set", name, ...paramspec.valueAtoms(spec, state.values[name]));
    if (state.autorun) schedule();
  }

  /** bypass 1: no runs; the runner passes what comes in straight through (passThrough). */
  function setBypass(on) {
    const m = Number(on);
    if (m !== 0 && m !== 1) return fail(`bypass is 0 or 1, got ${on}`);
    state.bypass = m === 1;
    if (state.bypass) pending.cancel();
    max.outlet(PANEL, "bypass", m);
  }

  /** snap 0 semitones, 1 quarter tones, 3 free: the output's pitches, from the next run (now, with auto_dump). */
  function setSnap(n) {
    const m = Number(n);
    if (!(m in SNAP_STEPS)) return fail(`snap is 0 (semitones), 1 (quarter tones) or 3 (free), got ${n}`);
    state.snap = m;
    max.outlet(PANEL, "snap", m);
    if (state.autorun && state.compiled) schedule();
  }

  /** A score at the inlet while bypassed: out of outlet 0 as it came. */
  function passThrough(name) {
    max.outlet(0, "dictionary", String(name));
  }

  /** repeat: the last score sent, out of outlet 0 again. */
  function repeat() {
    const text = lastScore.stringify();
    if (!text || text === "{}" || !JSON.parse(text).voices) return fail("repeat: no score sent yet");
    sendScore(JSON.parse(text));
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
    max.outlet(PANEL, "spec", JSON.stringify(Object.assign({
      title: basename(state.path).replace(/\.js$/, ""), path: state.path, kind: next.kind, params,
    }, hooks.spec ? hooks.spec() : {})));
    say(`loaded ${basename(state.path)}: ${paramspec.describe(next.specs, state.values).join("; ")}`);
    if (!(hooks.loaded && hooks.loaded())) return runNow();
    state.fresh = false;  // no run, so no algo_loaded: the first run is algo_done
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
    if (state.bypass) return;
    if (hooks.automatic && !hooks.automatic()) return;
    runNow();
  }

  /** A run: unless the runner's kind first asks for the score (request), then runs when it comes in. */
  function runNow() {
    pending.cancel();
    if (!state.compiled || state.bypass) return;
    if (hooks.request && hooks.request()) return;
    process();
  }

  /** Run on the score in hand: the score out of outlet 0. */
  function process() {
    pending.cancel();
    if (!state.compiled || state.bypass) return;
    let result;
    try {
      result = loader.run(state.compiled, state.values, hooks.source ? hooks.source() : null);
      if (result.score && hooks.output) result.score = hooks.output(result.score);
    } catch (e) {
      state.fresh = false;
      return fail(e);
    }
    const what = result.score ? "notes" : "notes selected";
    max.outlet(PANEL, "status", "ok", `${result.notes} ${what}, ${result.ms} ms`);
    if (state.fresh) max.outlet(STATUS, state.name, "algo_loaded", basename(state.path), result.notes, result.ms);
    else max.outlet(STATUS, state.name, "algo_done", result.notes, result.ms);
    state.fresh = false;
    if (hooks.ran) hooks.ran(result);  // before the score: it may come straight back
    if (result.score) sendScore(result.score);
  }

  /** A score out of outlet 0, as dictionary <name>. */
  function sendScore(score) {
    snapPitches(score, SNAP_STEPS[state.snap]);
    scoreDict.clear();
    scoreDict.parse(JSON.stringify(score));
    lastScore.clear();
    lastScore.parse(JSON.stringify(score));
    max.outlet(0, "dictionary", scoreDict.name);
  }

  /** write_to_playground: the last score sent, to <playground>/scores/<name>.json. */
  function writeScore() {
    if (!state.path) return fail("write_to_playground: no algorithm loaded, so no playground to write to");
    const text = lastScore.stringify();
    if (!text || text === "{}" || !JSON.parse(text).voices) return fail("write_to_playground: no score sent yet");
    const playground = state.path.replace(/[^\/:]*$/, "").replace(/[^\/:]+[\/:]$/, "");
    const path = playground + "scores/" + state.name + ".json";
    if (!files.write(path, text)) return fail(`could not write ${path}`);
    max.outlet(PANEL, "status", "ok", `score written to ${path}`);
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
    state, files, say, fail, schedule, runNow, process, sendScore, writeScore, PANEL, STATUS,
    setBypass, setSnap, passThrough, repeat,
    setname, load, loadAlgo, tryLoadAlgo, reload, autoDump, verbose, watch, setParam, deleted,
  };
}

module.exports = { createEngine };
