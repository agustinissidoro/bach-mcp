#!/usr/bin/env node
/*
algo_check.js — run an algorithm file the way bach.mcp.algo will, before it reaches Max.

    node algo_check.js <file.js>

Loads the file with the same core library, runs it with its declared values, then
once more for each slider at its minimum and maximum, each toggle flipped and each
other menu option, so that every setting reachable from the panel is known to work.
Prints one JSON line:
    {"ok": true, "params": [...], "describe": [...], "score": {...}, "notes": n, "ms": t, "runs": k}
    {"ok": false, "error": "...", "line": n, "context": "with times = 111 (its maximum)"}
Before each run it writes the setting to stderr, so a caller that has to stop an
endless loop can tell which setting caused it.
*/
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const core = require(path.join(__dirname, "..", "..", "max", "bach-mcp", "javascript", "bach.mcp.core.js"));

const MAX_RUNS = 48;

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
  const file = process.argv[2];
  if (!file) {
    reply({ ok: false, error: "usage: node algo_check.js <file.js>" });
    return;
  }
  const code = fs.readFileSync(file, "utf8");
  let compiled;
  try {
    compiled = core.compile(code);
  } catch (e) {
    const line = e.line || (String(e.message).startsWith("syntax error") ? syntaxLine(code) : null);
    reply({ ok: false, error: e.message, line });
    return;
  }

  const values = core.defaults(compiled.specs);
  let first;
  process.stderr.write("run: the declared values\n");
  try {
    first = core.run(compiled, values);
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
      core.run(compiled, Object.assign({}, values, { [spec.name]: value }));
    } catch (e) {
      reply({ ok: false, error: e.message, line: e.line || null, context });
      return;
    }
    runs += 1;
  }

  reply({
    ok: true,
    params: compiled.specs,
    describe: core.describe(compiled.specs),
    score: first.score,
    notes: first.notes,
    ms: first.ms,
    runs,
  });
}

main();
