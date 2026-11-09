// The runner (bachmcp.runner.js) wired to the panel (bachmcp.gui.params.v8ui.js), for each type:
// runner outlet 2 -> panel, panel outlet 0 -> runner, both for real on the Max stand-in.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { load, Dict } = require("./maxmock.js");

const FILES = {
  generator: `// climbs
const params = { times: { type: "slider", range: [1, 16], value: 4 } };
function produce(p) { const s = score(); const v = s.voice("Flute"); for (let i = 0; i < p.times; i++) v.note(i * 100, 6000 + i * 100, 100); return s; }`,
  transformer: `// shifts
const params = { shift: { type: "slider", range: [-1200, 1200], value: 100, unit: "mc" } };
function transform(source, p) { const out = copy(source); eachNote(out, (n) => { n.pitch += p.shift; }); return out; }`,
  selector: `// picks the high notes
const params = { above: { type: "slider", range: [0, 12700], value: 6000 } };
function select(source, p) { const out = []; eachNote(source, (n) => { if (n.pitch > p.above) out.push(n); }); return out; }`,
};

const SCORE = { voices: [{ chords: [
  { onset: 0, notes: [{ pitch: 5500, dur: 500, vel: 90 }, { pitch: 6400, dur: 500, vel: 90 }] },
  { onset: 500, notes: [{ pitch: 7200, dur: 500, vel: 90 }] },
] }] };

function file(text) {
  const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "bachmcp-panel-")), "algo.js");
  fs.writeFileSync(f, text);
  return f;
}

/** A runner of a type and a panel, wired (a panel can be given: the same panel, a new runner, as on reopening). */
function wire(type, panel) {
  const runner = load("bachmcp.runner.js", { args: [type] });
  panel = panel || load("bachmcp.gui.params.v8ui.js", { legacy: true, width: 320, height: 2000 });
  let fromRunner = 0, fromPanel = panel.out.length;
  const toPanel = [];
  function pump() {
    for (let k = 0; k < 20; k++) {
      let moved = false;
      while (fromRunner < runner.out.length) {
        const [i, selector, ...args] = runner.out[fromRunner++];
        if (i !== 2) continue;
        toPanel.push(selector);
        panel.send(selector, ...args);  // throws if the panel has no handler for it
        moved = true;
      }
      while (fromPanel < panel.out.length) {
        const [, selector, ...args] = panel.out[fromPanel++];
        runner.send(selector, ...args);
        moved = true;
      }
      runner.flush();
      if (!moved) return;
    }
    throw new Error("runner and panel keep answering each other");
  }
  return { runner, panel, pump, toPanel };
}

const runs = (w) => w.runner.out.filter((o) => o[0] === 4 && o[2] === "algo_done").length;
const scores = (w) => w.runner.out.filter((o) => o[0] === 0).length;

function input(w, score) {
  const d = new Dict(`panel_in_${Math.random().toString(36).slice(2)}`);
  d.parse(JSON.stringify(score));
  w.runner.send("dictionary", d.name);
  w.pump();
}

for (const type of ["generator", "transformer", "selector"]) {
  test(`${type}: the panel takes everything the runner sends, and a load runs nothing`, () => {
    const w = wire(type);
    w.runner.send("set_name", "a1");
    w.runner.send("load", file(FILES[type]));
    w.pump();
    const p = w.panel.ctx.panel;
    assert.equal(p.type, type);
    assert.equal(p.hasSource(), type !== "generator", "a source row only for a transformer and a selector");
    assert.equal(scores(w), 0, "a load is not a run");
    w.runner.send("bang");
    if (type !== "generator") input(w, SCORE);
    w.pump();
    assert.equal(runs(w), 1);
    for (const m of [["snap", 0], ["bypass", 1], ["bypass", 0], ["auto_dump", 0], ["type", type]]) w.runner.send(...m);
    if (type !== "generator") for (const m of [["source_mode", 0], ["process_only_selection", 1], ["capture"]]) w.runner.send(...m);
    if (type === "selector") for (const m of [["dump_selection_only", 0], ["involutive", 1], ["clear_selection"]]) w.runner.send(...m);
    w.runner.send("param", "tempo", 3);  // an error: status error to the panel
    w.pump();
    assert.ok(w.toPanel.includes("spec") && w.toPanel.includes("status"));
  });

  test(`${type}: on reopening, the panel's values reach a new runner without a run`, () => {
    const f = file(FILES[type]);
    const first = wire(type);
    first.runner.send("load", f);
    first.pump();
    const name = Object.keys(JSON.parse(first.runner.out.find((o) => o[1] === "spec")[2]).params.reduce((a, q) => (a[q.name] = 1, a), {}))[0];
    first.runner.send("param", name, 9);
    first.runner.send("snap", 1);
    if (type !== "generator") first.runner.send("source_mode", 0);
    first.pump();

    const again = wire(type, first.panel);  // the patch reopened: the panel kept its values, the runner did not
    again.runner.send("load", f);
    again.pump();
    const synced = again.panel.out.slice(-3).map((o) => o[1]);
    assert.ok(synced.every((s) => s === "sync"), `the panel answers with sync: ${synced}`);
    assert.equal(scores(again), 0, "the values arrive, nothing runs");
    assert.deepEqual(again.runner.out.filter((o) => o[0] === 2 && o[1] === "set" && o[2] === name).pop().slice(3), [9]);
    assert.ok(again.runner.out.some((o) => o[0] === 2 && o[1] === "snap" && o[2] === 1));
    again.runner.send("bang");
    if (type !== "generator") input(again, SCORE);
    assert.equal(runs(again), 1, "bang runs with them");
  });
}

test("type: the panel is cleared when the loaded file is of the old type", () => {
  const w = wire("generator");
  w.runner.send("load", file(FILES.generator));
  w.pump();
  assert.equal(w.panel.ctx.panel.items.length, 1);
  w.runner.send("type", "transformer");
  w.pump();
  assert.equal(w.panel.ctx.panel.items.length, 0, "no controls of the generator left");
  assert.equal(w.panel.ctx.panel.state.kind, "error", "the reason shows in the panel");
  w.runner.send("load", file(FILES.transformer));
  w.pump();
  assert.equal(w.panel.ctx.panel.type, "transformer");
});

test("sync applies a value without a run, whatever auto_dump says; it takes only the panel's settings", () => {
  const w = wire("generator");
  w.runner.send("load", file(FILES.generator));
  w.pump();
  w.runner.send("sync", "param", "times", 8);
  w.runner.flush();
  assert.equal(scores(w), 0);
  w.runner.send("bang");
  assert.equal(require("./maxmock.js").readDict(w.runner.out.filter((o) => o[0] === 0).pop()[2]).voices[0].chords.length, 8);
  w.runner.send("sync", "load", "/x.js");
  assert.match(w.runner.out.filter((o) => o[0] === 4).pop()[3], /sync: load cannot be synced/);
});

test("type: after the runner's type changes, the cleared panel is the new type's base panel", () => {
  const w = wire("generator");
  w.runner.send("load", file(FILES.generator));
  w.pump();
  w.runner.send("type", "selector");
  w.pump();
  const p = w.panel.ctx.panel;
  assert.equal(p.items.length, 0);
  assert.equal(p.type, "selector");
  assert.equal(p.hasSource(), true, "a selector's base panel, ready for a selector's file");
});

test("get_specs: a panel that was not listening at load gets the spec, with the values set since", () => {
  const runner = load("bachmcp.runner.js", { args: ["generator"] });
  runner.send("load", file(FILES.generator));
  runner.send("param", "times", 9);
  const panel = load("bachmcp.gui.params.v8ui.js", { legacy: true, width: 320, height: 2000 });  // not listening at load
  const before = runner.out.length;
  runner.send("get_specs");
  const specs = runner.out.slice(before);
  assert.deepEqual(specs.map((o) => o.slice(0, 2)), [[2, "spec"], [4, "algo"]]);
  assert.deepEqual(specs[1].slice(2), ["specs", 1], "it says so on dumpout");
  panel.send("spec", specs[0][2]);
  assert.equal(panel.ctx.panel.title, "algo");
  assert.equal(panel.ctx.panel.items.find((it) => it.name === "times").value, 9, "the current value, not the declared one");
  assert.deepEqual(runner.out.slice(before + 2).filter((o) => o[0] === 0 || o[0] === 4), [], "no run, no algo_loaded");

  const empty = load("bachmcp.runner.js", { args: ["transformer"] });
  empty.send("get_specs");
  assert.deepEqual(empty.out, [[4, "algo", "specs", 0]], "nothing loaded: no spec, and it says so");
});
