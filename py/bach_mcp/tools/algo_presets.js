/*
algo_presets.js
---------------
Carries an algorithm's presets over to its new version (send_algorithm, before the
new file replaces the old one):

    node algo_presets.js <old.js> <new.js>

The presets of <old.js> are written into <new.js> (in place), keeping in every slot
only the parameters the new file still declares with the same meaning (name, type,
kind and unit: paramspec.sameMeaning) and whose stored value the new declaration
accepts (coerce: snapped into its range, a menu option it still has). A slot left
with nothing is dropped. A new file that declares presets itself keeps its own.

Replies one JSON line:
    {"ok": true, "slots": {"3": {"kept": [...], "dropped": [...]}, ...}}
    {"ok": true, "slots": {}}            nothing to carry
    {"ok": false, "error": "..."}        the files are left as they were
*/
"use strict";

const fs = require("fs");
const path = require("path");

const JS = path.join(__dirname, "..", "..", "..", "javascript");
const loader = require(path.join(JS, "runners", "bachmcp.runner.loader.js"));
const paramspec = require(path.join(JS, "runners", "bachmcp.runner.paramspec.js"));
const presets = require(path.join(JS, "runners", "bachmcp.runner.presets.js"));

function reply(data) {
  process.stdout.write(JSON.stringify(data) + "\n");
}

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

/** The value as the new declaration takes it, or undefined when it does not. */
function adapt(spec, value) {
  try {
    const v = paramspec.coerce(spec, paramspec.valueAtoms(spec, value));
    return v;
  } catch (e) {
    return undefined;
  }
}

function carry(oldCode, newCode) {
  const before = loader.compile(oldCode);
  const after = loader.compile(newCode);
  const report = {};
  if (!presets.slots(before.presets).length || presets.slots(after.presets).length) {
    return { code: newCode, report };
  }
  const oldSpecs = new Map(before.specs.map((s) => [s.name, s]));
  const kept = {};
  for (const slot of presets.slots(before.presets)) {
    const stored = before.presets[slot];
    const out = {};
    const dropped = [];
    for (const name of Object.keys(stored)) {
      const spec = after.specs.find((s) => s.name === name);
      const was = oldSpecs.get(name);
      const v = spec && (!was || paramspec.sameMeaning(was, spec)) ? adapt(spec, stored[name]) : undefined;
      if (v === undefined) dropped.push(name);
      else out[name] = v;
    }
    if (Object.keys(out).length) kept[slot] = out;
    report[slot] = { kept: Object.keys(out), dropped,
      changed: Object.keys(out).filter((n) => !same(out[n], stored[n])) };
  }
  return { code: presets.withPresets(newCode, kept), report };
}

function main() {
  const [oldFile, newFile] = process.argv.slice(2);
  if (!oldFile || !newFile) {
    reply({ ok: false, error: "usage: node algo_presets.js <old.js> <new.js>" });
    return;
  }
  try {
    const { code, report } = carry(fs.readFileSync(oldFile, "utf8"), fs.readFileSync(newFile, "utf8"));
    if (Object.keys(report).length) fs.writeFileSync(newFile, code);
    reply({ ok: true, slots: report });
  } catch (e) {
    reply({ ok: false, error: String((e && e.message) || e) });
  }
}

if (require.main === module) main();

module.exports = { carry };
