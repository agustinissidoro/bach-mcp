// An algorithm edited and saved while watched: what the runner and the panel hold afterwards,
// for every element type. Both run for real here (runner <-> panel wired on the Max stand-in).
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { load } = require("./maxmock.js");

const BODY = "\nfunction produce(p) { return score(); }";

/** A generator runner and a panel, wired: runner outlet 1 -> panel, panel outlet 0 -> runner. */
function wire(file, panelOptions = {}) {
  const runner = load("bachmcp.runner.generator.js");
  const panel = load("bachmcp.gui.params.v8ui.js", Object.assign({ legacy: true, width: 320, height: 2000 }, panelOptions));
  let fromRunner = 0, fromPanel = 0;
  function pump() {
    for (let k = 0; k < 20; k++) {
      let moved = false;
      while (fromRunner < runner.out.length) {
        const [i, selector, ...args] = runner.out[fromRunner++];
        if (i === 1) {
          panel.send(selector, ...args);
          moved = true;
        }
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
  return { runner, panel, pump, file };
}

function algoFile(params) {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "bachmcp-reload-")), "algo.js");
  fs.writeFileSync(file, `const params = ${JSON.stringify(params)};${BODY}`);
  return file;
}

function save(w, params) {
  fs.writeFileSync(w.file, `const params = ${JSON.stringify(params)};${BODY}`);
  w.runner.flush(true);  // the watcher notices
  w.pump();
}

function start(params) {
  const w = wire(algoFile(params));
  w.runner.send("load", w.file);
  w.pump();
  return w;
}

/** What the runner holds: its last spec's values, then every "set" it echoed since. */
function runnerValues(w) {
  const specs = w.runner.out.filter((o) => o[0] === 1 && o[1] === "spec");
  const last = specs[specs.length - 1];
  const values = {};
  for (const p of JSON.parse(last[2]).params) values[p.name] = [].concat(...[].concat(p.value).map((x) => [].concat(x)));
  for (const o of w.runner.out.slice(w.runner.out.indexOf(last))) {
    if (o[0] === 1 && o[1] === "set") values[o[2]] = o.slice(3);
  }
  for (const k in values) values[k] = values[k].map((x) => (typeof x === "boolean" ? (x ? 1 : 0) : x));
  return values;
}

/** The panel's value of each parameter, as atoms; asserts the runner holds the same. */
function agreed(w) {
  const panel = {};
  for (const it of w.panel.ctx.panel.items) panel[it.name] = it.atoms();
  const plain = JSON.parse(JSON.stringify(panel));  // the panel's arrays come from another context
  assert.deepEqual(plain, runnerValues(w), "the panel shows what the runner runs with");
  return plain;
}

const param = (w, name, ...value) => {
  w.runner.send("param", name, ...value);
  w.pump();
};

// [type, first declaration, a value the user sets, the declaration saved next,
//  the value after it if untouched, the value after it if set]
const CASES = [
  ["slider: a new default; a set value stays",
    { type: "slider", range: [0, 100], value: 20 }, [70], { type: "slider", range: [0, 100], value: 40 }, [40], [70]],
  ["slider: a narrower range clamps a set value",
    { type: "slider", range: [0, 100], value: 20 }, [70], { type: "slider", range: [0, 10], value: 5 }, [5], [10]],
  ["slider: a finer step",
    { type: "slider", range: [0, 10], value: 2 }, [7], { type: "slider", range: [0, 10], value: 2.5, step: 0.5 }, [2.5], [7]],
  ["slider: another unit is another value (a plain number becomes a pitch)",
    { type: "slider", range: [0, 100], value: 20 }, [70], { type: "slider", range: [3600, 8400], value: 6000, unit: "mc" }, [6000], [6000]],
  ["range: a new default",
    { type: "range", range: [0, 100], value: [10, 20] }, [40, 50], { type: "range", range: [0, 100], value: [30, 60] }, [30, 60], [40, 50]],
  ["toggle: a new default",
    { type: "toggle", value: false }, [1], { type: "toggle", value: true }, [1], [1]],
  ["toggle: a new default, set the other way",
    { type: "toggle", value: true }, [0], { type: "toggle", value: false }, [0], [0]],
  ["menu: options renamed",
    { type: "menu", options: ["up", "down"], value: "up" }, ["down"], { type: "menu", options: ["rise", "fall"], value: "fall" }, ["fall"], ["fall"]],
  ["menu: options reordered, the set one still there",
    { type: "menu", options: ["a", "b", "c"], value: "a" }, ["b"], { type: "menu", options: ["c", "b", "a", "d"], value: "d" }, ["d"], ["b"]],
  ["menu: numbers as options are never positions",
    { type: "menu", options: [1, 2, 4], value: 1 }, [2], { type: "menu", options: [3, 5, 7], value: 5 }, [5], [5]],
  ["seed: a new default",
    { type: "seed", value: 1 }, [42], { type: "seed", value: 7 }, [7], [42]],
  ["curve: a new default",
    { type: "curve", value: [[0, 0], [1, 1]] }, [0, 0.5, 1, 0.25], { type: "curve", value: [[0, 1], [0.5, 0], [1, 1]] },
    [0, 1, 0.5, 0, 1, 1], [0, 0.5, 1, 0.25]],
  ["list: a new default of another length",
    { type: "list", range: [0, 10], value: [1, 2, 3] }, [9, 9, 9], { type: "list", range: [0, 10], value: [1, 2, 3, 4, 5] }, [1, 2, 3, 4, 5], [9, 9, 9]],
  ["list: a narrower range clamps",
    { type: "list", range: [0, 10], value: [1, 2, 3] }, [9, 9, 9], { type: "list", range: [0, 5], value: [1, 2, 3] }, [1, 2, 3], [5, 5, 5]],
  ["another type is another value",
    { type: "slider", range: [0, 100], value: 20 }, [70], { type: "range", range: [0, 100], value: [10, 90] }, [10, 90], [10, 90]],
];

for (const [title, before, set, after, untouched, touched] of CASES) {
  test(`saved while watched, ${title}`, () => {
    const a = start({ x: before });
    save(a, { x: after });
    assert.deepEqual(agreed(a).x, untouched, "untouched: the file's new value");

    const b = start({ x: before });
    param(b, "x", ...set);
    assert.deepEqual(agreed(b).x, set);
    save(b, { x: after });
    assert.deepEqual(agreed(b).x, touched, "set by the user");

    // the panel shows the new declaration itself
    const item = b.panel.ctx.panel.find("x");
    const spec = JSON.parse(b.runner.out.filter((o) => o[1] === "spec").pop()[2]).params[0];
    for (const key of ["type", "range", "step", "unit", "options", "kind"]) {
      if (spec[key] !== undefined) assert.deepEqual(JSON.parse(JSON.stringify(item[key])), spec[key], key);
    }
    assert.deepEqual(JSON.parse(JSON.stringify(item.def)), spec.default, "the new default (double-click goes back to it)");
  });
}

test("saved while watched: parameters renamed, added, removed and reordered", () => {
  const w = start({ a: { type: "slider", range: [0, 100], value: 20 }, b: { type: "toggle", value: true }, c: { type: "seed", value: 3 } });
  param(w, "b", 0);
  param(w, "c", 99);
  save(w, { z: { type: "slider", range: [0, 1], value: 0.5 }, b: { type: "toggle", value: true }, a2: { type: "slider", range: [0, 100], value: 20 } });
  assert.deepEqual(w.panel.ctx.panel.items.map((i) => i.name).join(), "z,b,a2", "the file's order");
  assert.deepEqual(agreed(w), { z: [0.5], b: [0], a2: [20] });
  assert.equal(w.panel.ctx.panel.rows.length, 3, "laid out again");
});

test("saved while watched: a broken save keeps the panel as it was; the next good save goes on", () => {
  const w = start({ a: { type: "slider", range: [0, 100], value: 20 } });
  param(w, "a", 70);
  fs.writeFileSync(w.file, "const params = { a: { type: \"slider\", range: [0, 100], value: 20 } };\nfunction produce(p) { return score(; }");
  w.runner.flush(true);
  w.pump();
  assert.equal(w.panel.ctx.panel.state.kind, "error");
  assert.deepEqual(agreed(w), { a: [70] });
  save(w, { a: { type: "slider", range: [0, 200], value: 20 } });
  assert.deepEqual(agreed(w), { a: [70] });
  assert.equal(w.panel.ctx.panel.find("a").range.join(), "0,200");
});

test("reopening the patch: the panel's saved values go to the runner, the file's new defaults show", () => {
  const w = start({ a: { type: "slider", range: [0, 100], value: 20 }, b: { type: "slider", range: [0, 100], value: 20 },
    m: { type: "menu", options: ["x", "y"], value: "x" } });
  param(w, "a", 70);
  param(w, "m", "y");
  w.panel.ctx.save();
  const saved = w.panel.embedded.pop();
  // the file's defaults changed while the patch was closed
  fs.writeFileSync(w.file, `const params = ${JSON.stringify({ a: { type: "slider", range: [0, 100], value: 30 },
    b: { type: "slider", range: [0, 100], value: 30 }, m: { type: "menu", options: ["x", "y"], value: "x" } })};${BODY}`);
  const again = wire(w.file);
  again.panel.send(...saved);
  again.runner.send("load", w.file);
  again.pump();
  assert.deepEqual(agreed(again), { a: [70], b: [30], m: ["y"] });
});

test("after a save, every control works with the new declaration", () => {
  const w = start({
    s: { type: "slider", range: [0, 10], value: 5 },
    r: { type: "range", range: [0, 10], value: [2, 8] },
    t: { type: "toggle", value: false },
    m: { type: "menu", options: ["a", "b"], value: "a" },
    d: { type: "seed", value: 1 },
    c: { type: "curve", range: [0, 1], value: [[0, 0], [1, 1]] },
    l: { type: "list", range: [0, 10], value: [1, 2, 3] },
  });
  save(w, {
    s: { type: "slider", range: [0, 1000], value: 500 },
    r: { type: "range", range: [-50, 50], value: [-10, 10] },
    t: { type: "toggle", value: true },
    m: { type: "menu", options: ["a", "b", "c", "d"], value: "a" },
    d: { type: "seed", range: [0, 99], value: 1 },
    c: { type: "curve", range: [0, 100], value: [[0, 0], [1, 100]] },
    l: { type: "list", range: [0, 100], value: [10, 20, 30, 40, 50, 60] },
  });
  const P = w.panel.ctx.panel;
  P.paint(w.panel.ctx.mgraphics, 320, 2000);
  const control = (name) => P.rows.find((r) => r.item.name === name).control;
  const click = (name, fx, fy, mods = {}) => {
    const c = control(name);
    const x = c.x + fx * c.w, y = c.y + fy * c.h;
    for (const m of P.mouseDown(x, y, mods)) w.panel.ctx.outlet(0, m);
    P.mouseUp();
    w.pump();
  };
  click("s", 1, 0.5);
  click("r", 0, 0.5);
  click("t", 0.01, 0.5);
  click("m", 0.99, 0.5);
  click("l", 0.99, 0);
  click("c", 0.5, 0.0);
  const v = agreed(w);
  assert.deepEqual(v.s, [1000], "the slider reaches the new top");
  assert.deepEqual(v.r, [-50, 10], "the range reaches the new bottom");
  assert.deepEqual(v.t, [0], "the toggle flips from its new default");
  assert.deepEqual(v.m, ["d"], "the menu shows the new options");
  assert.equal(v.l.length, 6, "the list has its new length");
  assert.equal(v.l[5], 100, "and its new range");
  assert.equal(v.c.length, 6, "a point added to the curve");
  assert.equal(v.c[3], 100, "at the top of its new range");
  click("d", 0.99, 0.5);
  const seed = agreed(w).d[0];
  assert.ok(seed >= 0 && seed <= 99, "a new seed in the new range");
});
