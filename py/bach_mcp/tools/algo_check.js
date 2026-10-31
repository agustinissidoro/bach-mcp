#!/usr/bin/env node
/*
algo_check.js — run an algorithm file the way the runners in Max will, before it reaches Max.

    node algo_check.js <file.js> [--source <score file>]

Loads the file with the same loader and algorithmic core library as Max, runs it
with its declared values, then once more for each slider at its minimum and
maximum, each toggle flipped and each other menu option, so that every setting
reachable from the panel is known to work.
A transformer or a selector runs on the --source score (a bachjson-complete
file), or on a small built-in score without one.
Prints one JSON line:
    {"ok": true, "kind": "producer" | "transformer" | "selector", "source": {"notes": n, "given": true} | null,
     "params": [...], "describe": [...], "score": {...}, "notes": n, "ms": t, "runs": k}
    (a selector: "selection": [[voice, chord, note], ...] in place of "score", "notes" the notes picked)
    {"ok": false, "error": "...", "line": n, "context": "with times = 111 (its maximum)"}
Before each run it writes the setting to stderr, so a caller that has to stop an
endless loop can tell which setting caused it.
*/
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const JS = path.join(__dirname, "..", "..", "..", "javascript");
const loader = require(path.join(JS, "runners", "bachmcp.runner.loader.js"));
const paramspec = require(path.join(JS, "runners", "bachmcp.runner.paramspec.js"));

// What a transformer is checked on when there is no score to give it: two voices,
// phrases separated by silences, a chord, a few marks.
const SAMPLE_SOURCE = {
  voices: [
    { name: "Flute", chords: [
      { onset: 0, dyn: "mp", notes: [{ pitch: 7200, dur: 250 }] },
      { onset: 250, notes: [{ pitch: 7400, dur: 250 }] },
      { onset: 500, notes: [{ pitch: 7600, dur: 250 }] },
      { onset: 750, art: "tenuto", notes: [{ pitch: 7900, dur: 500 }] },
      { onset: 2000, notes: [{ pitch: 8100, dur: 300 }] },
      { onset: 2300, notes: [{ pitch: 7700, dur: 300 }] },
      { onset: 2600, notes: [{ pitch: 7450, dur: 600 }] },
      { onset: 4500, art: "staccato", notes: [{ pitch: 6900, dur: 150 }] },
      { onset: 4700, art: "staccato", notes: [{ pitch: 7100, dur: 150 }] },
      { onset: 4900, notes: [{ pitch: 7300, dur: 1200, gliss: -200 }] },
    ] },
    { name: "Cello", chords: [
      { onset: 0, notes: [{ pitch: 3600, dur: 1500 }, { pitch: 4300, dur: 1500 }] },
      { onset: 2000, notes: [{ pitch: 3800, dur: 1200 }] },
      { onset: 4500, notes: [{ pitch: 3500, dur: 1600 }] },
    ] },
  ],
};

function readSource(file) {
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text);
}

const MAX_RUNS = 48;

function countNotes(score) {
  let n = 0;
  for (const v of (score && score.voices) || []) for (const c of (v && v.chords) || []) n += ((c && c.notes) || []).length;
  return n;
}

function reply(data) {
  process.stdout.write(JSON.stringify(data) + "\n");
}

/** Line of a syntax error: compiling the file as a plain script gives it in the stack. */
function syntaxLine(code) {
  try {
    new vm.Script(code, { filename: "algorithm.js" });
  } catch (e) {
    const m = /algorithm\.js:(\d+)/.exec(String(e.stack));
    if (m) return Number(m[1]);
  }
  return null;
}

function settings(specs) {
  const out = [];
  for (const s of specs) {
    if (s.type === "slider") {
      if (s.value !== s.range[0]) out.push([s, s.range[0], "its minimum"]);
      if (s.value !== s.range[1]) out.push([s, s.range[1], "its maximum"]);
    } else if (s.type === "range") {
      if (s.value[0] !== s.range[0] || s.value[1] !== s.range[1]) out.push([s, s.range.slice(), "its widest"]);
    } else if (s.type === "toggle") {
      out.push([s, !s.value, "flipped"]);
    } else if (s.type === "menu") {
      for (const o of s.options) if (String(o) !== String(s.value)) out.push([s, o, "another option"]);
    }
  }
  return out.slice(0, MAX_RUNS);
}

function main() {
  const args = process.argv.slice(2);
  const file = args[0];
  const sourceFile = args.indexOf("--source") >= 0 ? args[args.indexOf("--source") + 1] : null;
  if (!file) {
    reply({ ok: false, error: "usage: node algo_check.js <file.js> [--source <score file>]" });
    return;
  }
  const code = fs.readFileSync(file, "utf8");
  let compiled;
  try {
    compiled = loader.compile(code);
  } catch (e) {
    const line = e.line || (String(e.message).startsWith("syntax error") ? syntaxLine(code) : null);
    reply({ ok: false, error: e.message, line });
    return;
  }

  let source = null;
  if (compiled.kind === "transformer" || compiled.kind === "selector") {
    try {
      source = sourceFile ? readSource(sourceFile) : SAMPLE_SOURCE;
    } catch (e) {
      reply({ ok: false, error: `cannot read the source score (${e.message})`, fatal: true });
      return;
    }
  }

  const values = paramspec.defaults(compiled.specs);
  let first;
  process.stderr.write("run: the declared values\n");
  try {
    first = loader.run(compiled, values, source);
  } catch (e) {
    reply({ ok: false, error: e.message, line: e.line || null, context: "with the declared values" });
    return;
  }

  let runs = 1;
  for (const [spec, value, why] of settings(compiled.specs)) {
    const shown = JSON.stringify(value);
    const context = `with ${spec.name} = ${shown} (${why})`;
    process.stderr.write(`run: ${context}\n`);
    try {
      loader.run(compiled, Object.assign({}, values, { [spec.name]: value }), source);
    } catch (e) {
      reply({ ok: false, error: e.message, line: e.line || null, context });
      return;
    }
    runs += 1;
  }

  reply({
    ok: true,
    kind: compiled.kind,
    source: source ? { notes: countNotes(source), given: Boolean(sourceFile) } : null,
    params: compiled.specs,
    describe: paramspec.describe(compiled.specs),
    score: first.score,
    selection: first.selection,
    notes: first.notes,
    ms: first.ms,
    runs,
  });
}

main();
