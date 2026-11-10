// The parameter panel (v8ui: GUI_parameters/bachmcp.gui.params.*.js), run on a stand-in for Max.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { load, legacyRequire, JS_DIR } = require("./maxmock.js");

const SPEC = {
  title: "walkers",
  path: "/tmp/walkers.js",
  params: [
    { name: "times", type: "slider", range: [1, 64], step: 1, value: 16, default: 16 },
    { name: "amount", type: "slider", range: [0, 1], step: 0, value: 0.5, default: 0.5, unit: "x" },
    { name: "register", type: "range", range: [3600, 9600], step: 1, value: [4800, 8400], default: [4800, 8400], unit: "mc" },
    { name: "legato", type: "toggle", value: false, default: false },
    { name: "mode", type: "menu", options: ["up", "down", "both"], value: "up", default: "up" },
    { name: "many", type: "menu", options: ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"], value: "a", default: "a" },
    { name: "seed", type: "seed", range: [0, 9999], step: 1, value: 1, default: 1 },
    { name: "shape", type: "curve", range: [0, 1], step: 0, value: [[0, 0], [1, 1]], default: [[0, 0], [1, 1]] },
    { name: "durs", type: "list", range: [0, 1000], step: 1, value: [100, 200, 300, 400], default: [100, 200, 300, 400] },
  ],
};

// The parts keep to `exports` (no `module`), so they also load as the legacy engine would.
function loadPanel(options) {
  return load("bachmcp.gui.params.v8ui.js", Object.assign({ legacy: true }, options));
}

function panelWith(spec = SPEC) {
  const m = loadPanel({ width: 320, height: 100 });
  m.send("spec", JSON.stringify(spec));
  return m;
}

function row(m, name) {
  return m.ctx.panel.rows.find((r) => r.item.name === name);
}

// A point inside a control: fx, fy as fractions of its width and height.
function at(m, name, fx, fy = 0.5) {
  const c = row(m, name).control;
  return [c.x + fx * c.w, c.y + fy * c.h];
}

function click(m, name, fx, fy, mods = {}) {
  const [x, y] = at(m, name, fx, fy);
  m.ctx.onclick(x, y, 1, 0, mods.shift ? 1 : 0, 0, 0, 0);
}

function drag(m, name, fx, fy, mods = {}) {
  const [x, y] = at(m, name, fx, fy);
  m.ctx.ondrag(x, y, 1, 0, mods.shift ? 1 : 0, 0, 0, 0);
}

function release(m) {
  m.ctx.ondrag(0, 0, 0, 0, 0, 0, 0, 0);
}

// What the panel sent, without the "param" in front of a parameter (checked here: a bare name fails).
function sent(m) {
  const names = new Set(m.ctx.panel.items.map((it) => it.name));
  const out = m.out.map((o) => {
    assert.ok(!names.has(o[1]), `"${o[1]}" was sent without "param"`);
    return o[1] === "param" ? o.slice(2) : o.slice(1);
  });
  m.out.length = 0;
  return out;
}

test("the panel builds itself, resizes to fit and draws every element", () => {
  const m = panelWith();
  assert.equal(m.ctx.panel.items.length, 9);
  const rect = m.ctx.box.rect;
  assert.ok(rect[3] - rect[1] > 250, "taller than the default box");
  m.ctx.mgraphics.size = [320, rect[3] - rect[1]];
  m.ctx.paint();
  const texts = m.ctx.mgraphics.calls.filter((c) => c[0] === "show_text").map((c) => c[1]);
  for (const name of ["walkers", "times", "register", "16", "4800–8400 mc", "0.5 x", "off", "both", "2 points"]) {
    assert.ok(texts.includes(name), `draws ${name}`);
  }
  assert.ok(texts.includes("a"), "the long menu is a stepper showing its value");
  assert.equal(sent(m).length, 0, "building the panel sends nothing");
});

test("rows do not overlap and controls stay inside the panel", () => {
  const m = panelWith();
  const rows = m.ctx.panel.rows;
  for (let i = 1; i < rows.length; i++) assert.ok(rows[i].y >= rows[i - 1].y + rows[i - 1].h);
  for (const r of rows) assert.ok(r.control.x >= 0 && r.control.x + r.control.w <= 320, r.item.name);
});

test("an empty panel: No algorithm loaded., under the set_name name if there is one", () => {
  const m = loadPanel({ width: 200, height: 60 });
  const texts = () => {
    m.ctx.mgraphics.calls.length = 0;
    m.ctx.paint();
    return m.ctx.mgraphics.calls.filter((c) => c[0] === "show_text").map((c) => c[1]);
  };
  assert.deepEqual(texts(), ["No algorithm loaded.", "set active"]);
  m.send("set_name", "t1");
  assert.deepEqual(texts(), ["t1", "No algorithm loaded.", "set active"]);
  m.send("set_name");
  assert.deepEqual(texts(), ["No algorithm loaded.", "set active"], "set active is always there");
  const named = loadPanel({ width: 200, height: 60, args: ["t2"] });
  named.ctx.paint();
  assert.deepEqual(named.ctx.mgraphics.calls.filter((c) => c[0] === "show_text").map((c) => c[1]),
                   ["t2", "No algorithm loaded.", "set active"], "the box's first argument is the name");
});

test("slider: click jumps, drag follows, shift drag is fine, double-click resets", () => {
  const m = panelWith();
  click(m, "times", 1);
  assert.deepEqual(sent(m), [["times", 64]]);
  drag(m, "times", 0);
  assert.deepEqual(sent(m), [["times", 1]]);
  drag(m, "times", 0);
  assert.deepEqual(sent(m), [], "no change, nothing sent");
  release(m);
  click(m, "amount", 0.5);
  drag(m, "amount", 1, 0.5, { shift: true });
  const fine = sent(m).pop();
  assert.ok(fine[1] > 0.5 && fine[1] < 0.6, `fine drag moved ${fine[1]}`);
  release(m);
  const [x, y] = at(m, "times", 0.3);
  m.ctx.ondblclick(x, y);
  assert.deepEqual(sent(m), [["times", 16]]);
});

test("range: each end, and the middle moves both", () => {
  const m = panelWith();
  click(m, "register", 0);
  assert.deepEqual(sent(m), [["register", 3600, 8400]]);
  release(m);
  click(m, "register", 1);
  assert.deepEqual(sent(m), [["register", 3600, 9600]]);
  release(m);
  m.send("set", "register", 6000, 7000); // 0.4 to 0.567 of the track
  click(m, "register", 0.48);
  drag(m, "register", 0.58);
  const [[, lo, hi]] = sent(m).slice(-1);
  assert.equal(hi - lo, 1000, "the span is kept");
  assert.ok(lo > 6000);
});

test("toggle, menu segments and menu stepper", () => {
  const m = panelWith();
  click(m, "legato", 0.05);
  assert.deepEqual(sent(m), [["legato", 1]]);
  click(m, "mode", 0.9);
  assert.deepEqual(sent(m), [["mode", "both"]]);
  click(m, "many", 0.9);
  assert.deepEqual(sent(m), [["many", "b"]]);
  click(m, "many", 0.1);
  click(m, "many", 0.1);
  assert.deepEqual(sent(m), [["many", "a"], ["many", "j"]]);
});

test("seed: the square draws a new seed, dragging changes it", () => {
  const m = panelWith();
  click(m, "seed", 0.99);
  const [[name, value]] = sent(m);
  assert.equal(name, "seed");
  assert.notEqual(value, 1);
  release(m);
  m.send("set", "seed", 10);
  click(m, "seed", 0.2);
  drag(m, "seed", 0.4);
  assert.ok(sent(m).pop()[1] > 10);
});

test("curve: click adds a point, drag moves it, shift-click removes it; the ends stay at 0 and 1", () => {
  const m = panelWith();
  click(m, "shape", 0.5, 0.2);
  const added = sent(m).pop();
  assert.equal(added.length, 1 + 6);
  assert.equal(added[3], 0.5);
  assert.ok(Math.abs(added[4] - 0.8) < 0.02);
  drag(m, "shape", 0.6, 0.5);
  const moved = sent(m).pop();
  assert.ok(Math.abs(moved[3] - 0.6) < 0.02 && Math.abs(moved[4] - 0.5) < 0.02);
  release(m);
  click(m, "shape", 0, 1);
  drag(m, "shape", 0.3, 0);
  const end = sent(m).pop();
  assert.deepEqual([end[1], end[2]], [0, 1], "the first point keeps x = 0");
  release(m);
  click(m, "shape", 0.6, 0.5, { shift: true });
  assert.equal(sent(m).pop().length, 1 + 4);
});

test("list: drawing across the bars sets each of them", () => {
  const m = panelWith();
  click(m, "durs", 0.05, 0);
  drag(m, "durs", 0.95, 0);
  const all = sent(m);
  assert.deepEqual(all[all.length - 1], ["durs", 1000, 1000, 1000, 1000]);
});

test("a new spec keeps the values of parameters with the same name and type, and sends them", () => {
  const m = panelWith();
  m.send("set", "times", 40);
  m.send("set", "mode", "down");
  const next = JSON.parse(JSON.stringify(SPEC));
  next.params[0].range = [1, 32];
  next.params[4].type = "slider";
  next.params[4].range = [0, 1];
  next.params[4].value = 0;
  m.send("spec", JSON.stringify(next));
  assert.deepEqual(sent(m), [["sync", "param", "times", 32]], "clamped to the new range; mode changed type, so not kept; sync: it runs nothing");
});

test("status line, reset and bang", () => {
  const m = panelWith();
  m.send("status", "error", "something", "broke", "(line", "3)");
  assert.deepEqual(JSON.parse(JSON.stringify(m.ctx.panel.state)), { kind: "error", text: "something broke (line 3)" });
  m.send("set", "times", 3);
  m.send("reset");
  assert.deepEqual(sent(m), [["times", 16]]);
  m.send("bang");
  assert.equal(sent(m).length, 9);
});

test("saved with the patch: restore rebuilds the panel and sends nothing", () => {
  const m = panelWith();
  m.send("set", "times", 33);
  m.ctx.save();
  const [[selector, text]] = m.embedded;
  assert.equal(selector, "restore");
  const fresh = loadPanel({ width: 320, height: 100 });
  fresh.send("restore", text);
  assert.equal(fresh.ctx.panel.find("times").value, 33);
  fresh.flush();
  assert.deepEqual(sent(fresh), [], "no load on restore");
  // the runner answers with its spec at the declared values; the panel sends back what it kept
  fresh.send("spec", JSON.stringify(SPEC));
  assert.deepEqual(sent(fresh), [["sync", "param", "times", 33]]);
});

test("pattr: getvalueof and setvalueof round trip", () => {
  const m = panelWith();
  const flat = m.ctx.getvalueof();
  m.send("set", "times", 2);
  m.send("set", "mode", "both");
  m.send("set", "shape", 0, 0.5, 0.5, 0.2, 1, 1);
  m.ctx.setvalueof(...flat);
  const back = sent(m);
  assert.deepEqual(back.map((b) => b[0]), ["times", "mode", "shape"]);
  assert.deepEqual(back[1], ["mode", "up"]);
  assert.deepEqual(back[2], ["shape", 0, 0, 1, 1]);
});

// The parts (not the v8ui script) stay ECMAScript 5: no modern syntax or built-ins.
const GUI_DIR = path.join(JS_DIR, "GUI_parameters");
for (const file of fs.readdirSync(GUI_DIR).filter((f) => f.endsWith(".js") && !f.endsWith(".v8ui.js"))) {
  test(`${file} is ECMAScript 5`, () => {
    const code = fs.readFileSync(path.join(GUI_DIR, file), "utf8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/.*$/gm, "")
      .replace(/"(?:[^"\\]|\\.)*"/g, '""');
    for (const pattern of [/\blet\s/, /\bconst\s/, /=>/, /`/, /\bclass\s/, /\.\.\./, /\bof\s/]) {
      assert.doesNotMatch(code, pattern, `${file} uses ${pattern}`);
    }
  });
}

test("the panel loads through jsui's require (exports only, no module), and loads its parts", () => {
  assert.equal(typeof legacyRequire("bachmcp.gui.params.panel.js").Panel, "function");
  assert.equal(typeof legacyRequire("bachmcp.gui.params.elements.js").makeElement, "function");
});

test("without the element library the panel says so once and keeps working", () => {
  const broken = loadPanel({ width: 200, height: 60 });
  broken.ctx.panel = null; // what the script holds when require fails
  broken.ctx.paint();
  broken.send("spec", JSON.stringify(SPEC));
  broken.ctx.save();
  broken.ctx.onclick(10, 10, 1, 0, 0, 0, 0, 0);
  const texts = broken.ctx.mgraphics.calls.filter((c) => c[0] === "show_text").map((c) => c[1]);
  assert.ok(texts.some((t) => t.includes("bachmcp.gui.params.panel.js not found")));
  assert.deepEqual(broken.out, []);
});

test("the panel uses no ES2015 built-ins", () => {
  // Every part runs in a context without them, as jsui's legacy engine would.
  const WITHOUT = `
    delete Object.assign; delete Object.entries; delete Object.values; delete Object.fromEntries;
    delete Array.from; delete Array.of; delete Array.prototype.find; delete Array.prototype.findIndex;
    delete Array.prototype.includes; delete Array.prototype.fill; delete Array.prototype.flat;
    delete Number.isInteger; delete Number.isFinite; delete Number.isNaN; delete Number.EPSILON;
    delete String.prototype.includes; delete String.prototype.startsWith; delete String.prototype.endsWith;
    delete String.prototype.repeat; delete String.prototype.padStart;
    delete Math.sign; delete Math.trunc; delete Math.log10; delete Math.hypot;
    delete globalThis.Map; delete globalThis.Set; delete globalThis.Symbol; delete globalThis.Promise;
  `;
  function strictRequire(name) {
    const ctx = { exports: {}, require: strictRequire };
    vm.createContext(ctx);
    vm.runInContext(WITHOUT, ctx);
    vm.runInContext(fs.readFileSync(path.join(GUI_DIR, path.basename(name)), "utf8"), ctx);
    return ctx.exports;
  }
  const gui = strictRequire("bachmcp.gui.params.panel.js");
  const panel = new gui.Panel();
  panel.setSpec(JSON.parse(JSON.stringify(SPEC)));
  const g = load("bachmcp.gui.params.v8ui.js").ctx.mgraphics;
  panel.paint(g, 320, panel.layout(320));
  const r = panel.rows;
  for (const row of r) {
    const c = row.control;
    panel.mouseDown(c.x + c.w * 0.7, c.y + c.h * 0.3, {});
    panel.mouseDrag(c.x + c.w * 0.2, c.y + c.h * 0.8, {});
    panel.mouseUp();
    panel.doubleClick(c.x + 1, c.y + 1);
  }
  panel.setFlatValues(panel.flatValues());
  panel.restore(panel.snapshot());
});

test("a transformer's panel has its source row and a capture button", () => {
  const m = panelWith(Object.assign({}, SPEC, { type: "transformer" }));
  m.ctx.paint();
  const texts = m.ctx.mgraphics.calls.filter((c) => c[0] === "show_text").map((c) => c[1]);
  assert.ok(texts.includes("capture"));
  assert.ok(texts.includes("SOURCE"), "the source row, without its notes (for now)");
  const b = m.ctx.panel.captureRect(320);
  m.ctx.onclick(b.x + 5, b.y + 5, 1, 0, 0, 0, 0, 0);
  assert.deepEqual(sent(m), [["capture"]]);
  const w = m.ctx.panel.writeRect(320);
  m.ctx.onclick(w.x + 5, w.y + 5, 1, 0, 0, 0, 0, 0);
  assert.deepEqual(sent(m), [["write_to_playground"]]);
  m.send("source", 12, "inlet");  // an old runner's message: taken, shown nowhere
  const generator = panelWith();
  generator.ctx.paint();
  assert.ok(!generator.ctx.mgraphics.calls.some((c) => c[0] === "show_text" && c[1] === "capture"));
});

const KINDS = {
  title: "kinds",
  params: [
    { name: "target", type: "slider", kind: "pitch", grid: 100, unit: "mc", range: [0, 12700], step: 1, value: 6400, default: 6400 },
    { name: "step", type: "slider", kind: "interval", grid: 100, unit: "mc", range: [-1200, 1200], step: 1, value: 400, default: 400 },
    { name: "register", type: "range", kind: "pitch", grid: 100, unit: "mc", range: [0, 12700], step: 1, value: [4800, 8400], default: [4800, 8400] },
    { name: "gap", type: "slider", kind: "time", grid: 20, unit: "ms", range: [50, 2000], step: 1, value: 300, default: 300 },
  ],
};

function texts(m) {
  const rect = m.ctx.box.rect;
  m.ctx.mgraphics.size = [rect[2] - rect[0], rect[3] - rect[1]];  // Max resizes the drawing with the box
  m.ctx.mgraphics.calls.length = 0;
  m.ctx.paint();
  return m.ctx.mgraphics.calls.filter((c) => c[0] === "show_text").map((c) => c[1]);
}

function clickValue(m, name) {
  const v = row(m, name).value;
  m.ctx.onclick(v.x + v.w / 2, v.y + v.h / 2, 1, 0, 0, 0, 0, 0);
  release(m);
}

test("a pitch shows as a name; clicking its value text switches to midicents, MIDI and back, sending nothing", () => {
  const m = panelWith(KINDS);
  let t = texts(m);
  for (const shown of ["E4", "+400 mc", "C3–C6", "300 ms", "reset"]) assert.ok(t.includes(shown), `draws ${shown}`);
  clickValue(m, "target");
  assert.ok(texts(m).includes("6400 mc"));
  clickValue(m, "target");
  assert.ok(texts(m).includes("64 midi"));
  clickValue(m, "target");
  assert.ok(texts(m).includes("E4"));
  clickValue(m, "step");
  assert.ok(texts(m).includes("+4 st"));
  clickValue(m, "gap");
  assert.ok(texts(m).includes("300 ms"), "a time has one way to be shown");
  assert.deepEqual(sent(m), []);
});

test("free is free: a drag lands anywhere, alt snaps it to the card's grid; ½ snaps, alt lets it through", () => {
  const m = panelWith(KINDS);
  const alt = (name, fx) => {
    const [x, y] = at(m, name, fx);
    m.ctx.onclick(x, y, 1, 0, 0, 0, 1, 0);
    const [[, v]] = sent(m);
    release(m);
    return v;
  };
  // pitches start free
  click(m, "target", 0.5513);  // about 7001 cents
  const [[, free]] = sent(m);
  assert.notEqual(free % 100, 0, `a free drag is free: ${free}`);
  release(m);
  assert.equal(alt("target", 0.5513) % 100, 0, "alt snaps it to semitones");
  click(m, "register", 0.0137);
  assert.notEqual(sent(m)[0][1] % 100, 0, "a free range too");
  release(m);
  // ½: snapped; alt lets it through
  m.send("snap", 0);
  click(m, "target", 0.6013);  // about 7637 cents
  assert.deepEqual(sent(m), [["target", 7600]]);
  release(m);
  assert.notEqual(alt("target", 0.5037) % 100, 0, "alt drag is free");
  // a time card starts free: no grid either
  const gap = m.ctx.panel.rows.find((r) => r.item.name === "gap");
  assert.equal(m.ctx.panel.snapState(gap.item)[1], "free");
  click(m, "gap", 0.3011);
  assert.notEqual(sent(m)[0][1] % 10, 0, "a free time is free");
  release(m);
  click(m, "gap", 0);
  assert.deepEqual(sent(m), [["gap", 50]], "the ends of the range stay reachable");
});

test("the display is saved with the patch, and kept when the code is reloaded", () => {
  const m = panelWith(KINDS);
  clickValue(m, "target");
  m.send("spec", JSON.stringify(KINDS));
  assert.equal(m.ctx.panel.find("target").display, "mc", "a new spec keeps the display");
  const snapshot = m.ctx.panel.snapshot();
  const n = loadPanel({ width: 320, height: 100 });
  n.ctx.panel.restore(snapshot);
  assert.equal(n.ctx.panel.find("target").display, "mc");
});

test("a transformer's source mode: click to switch, sent to the runner, kept with the patch", () => {
  const spec = Object.assign({}, SPEC, { type: "transformer" });
  const m = panelWith(spec);
  const r = m.ctx.panel.modeRect(m.ctx.panel.width);
  assert.ok(texts(m).includes("destructive"), "a toggle, off: non-destructive");
  m.ctx.onclick(r.x + 2, r.y + 2, 1, 0, 0, 0, 0, 0);
  release(m);
  assert.deepEqual(sent(m), [["source_mode", 0]]);
  m.send("spec", JSON.stringify(spec));
  assert.deepEqual(sent(m).filter((x) => x[1] === "source_mode"), [["sync", "source_mode", 0]], "a reload tells the runner");
  m.send("source_mode", 1);
  assert.equal(m.ctx.panel.sourceMode, "nondestructive");
  assert.deepEqual(sent(m), [], "the runner's echo is not sent back");
  m.ctx.onclick(r.x + 2, r.y + 2, 1, 0, 0, 0, 0, 0);
  release(m);
  const n = loadPanel({ width: 320, height: 100 });
  n.ctx.panel.restore(m.ctx.panel.snapshot());
  assert.equal(n.ctx.panel.sourceMode, "destructive");
});

test("reset all in the options, and hovering a card redraws only when it changes", () => {
  const m = panelWith();
  click(m, "times", 1);
  release(m);
  sent(m);
  const r = m.ctx.panel.resetRect(320);
  m.ctx.onclick(r.x + 2, r.y + 2, 1, 0, 0, 0, 0, 0);
  assert.deepEqual(sent(m), [["times", 16]]);
  const before = m.ctx.mgraphics.redraws;
  const [x, y] = at(m, "amount", 0.5);
  m.ctx.onidle(x, y);
  m.ctx.onidle(x, y);
  assert.equal(m.ctx.mgraphics.redraws, before + 1);
  m.ctx.onidleout();
  assert.equal(m.ctx.mgraphics.redraws, before + 2);
});

const M_TITLE = 30;

test("set active sits in the title row, also with no algorithm, and sends set_as_active_instance", () => {
  const m = panelWith(KINDS);
  const panel = m.ctx.panel;
  const p = panel.ui(panel.width);
  assert.ok(p.setActive.y < M_TITLE && p.bypass.x + p.bypass.w <= p.setActive.x, "on top, right of bypass");
  m.ctx.onclick(p.setActive.x + 2, p.setActive.y + 2, 1, 0, 0, 0, 0, 0);
  release(m);
  assert.deepEqual(sent(m), [["set_as_active_instance"]]);
  const empty = loadPanel({ width: 320, height: 100 });
  const q = empty.ctx.panel.ui(320);
  assert.ok(q.setActive && !q.bypass, "an instance with no algorithm can be made active");
  empty.ctx.onclick(q.setActive.x + 2, q.setActive.y + 2, 1, 0, 0, 0, 0, 0);
  release(empty);
  assert.deepEqual(sent(empty), [["set_as_active_instance"]]);
});

test("bypass sits in the title row; a pitch card's toggle cycles ½ | ¼ | free, sets its grid and is sent as snap", () => {
  const m = panelWith(KINDS);
  const panel = m.ctx.panel;
  const p = panel.ui(panel.width);
  assert.ok(p.bypass.y < M_TITLE, "bypass on top");
  m.ctx.onclick(p.bypass.x + 2, p.bypass.y + 2, 1, 0, 0, 0, 0, 0);
  release(m);
  assert.deepEqual(sent(m), [["bypass", 1]]);
  const row = panel.rows.find((r) => r.item.name === "target");
  assert.ok(row.snapToggle, "the toggle is on the pitch card");
  const t = row.snapToggle;
  m.ctx.onclick(t.x + 2, t.y + 2, 1, 0, 0, 0, 0, 0);
  release(m);
  assert.deepEqual(sent(m), [["snap", 0]], "free -> ½");
  assert.equal(panel.find("target").grid, 100);
  m.ctx.onclick(t.x + 2, t.y + 2, 1, 0, 0, 0, 0, 0);
  release(m);
  assert.deepEqual(sent(m), [["snap", 1]]);
  assert.equal(panel.find("target").grid, 50, "quarter tones");
  m.send("snap", 0);
  assert.equal(panel.find("target").grid, 100);
  assert.deepEqual(sent(m), [], "the echo is not sent back");
  click(m, "target", 0.5513);
  assert.equal(sent(m)[0][1] % 100, 0);
  release(m);
  const time = panel.rows.find((r) => r.item.kind === "time");
  if (time) {
    m.ctx.onclick(time.snapToggle.x + 2, time.snapToggle.y + 2, 1, 0, 0, 0, 0, 0);
    release(m);
    assert.deepEqual(sent(m), [], "a time toggle stays in the panel");
    assert.equal(time.item.grid, 100);
  }
});

test("the panel goes compact when its parameters do not fit the box: one line each", () => {
  const panel = loadPanel({ width: 320, height: 100 }).ctx.panel;
  panel.setSpec(KINDS);
  const full = panel.layout(320);
  assert.equal(panel.compact, false);
  const compact = panel.layout(320, full - 40);
  assert.equal(panel.compact, true);
  assert.ok(compact < full);
  const row = panel.rows[0];
  assert.equal(row.label.y, row.control.y, "name and control on one line");
});

test("process sel. toggles process_only_selection on a transformer's and a selector's source row", () => {
  for (const kind of ["transformer", "selector"]) {
    const m = panelWith(Object.assign({}, SPEC, { type: kind }));
    const r = m.ctx.panel.ui(m.ctx.panel.width).within;
    assert.ok(texts(m).includes("process sel."));
    m.ctx.onclick(r.x + 2, r.y + 2, 1, 0, 0, 0, 0, 0);
    release(m);
    assert.deepEqual(sent(m), [["process_only_selection", 1]]);
    m.send("process_only_selection", 0);
    assert.equal(m.ctx.panel.withinSelection, false);
    assert.deepEqual(sent(m), []);
  }
  const g = panelWith(SPEC);
  assert.equal(g.ctx.panel.ui(g.ctx.panel.width).within, null, "a generator has no source row");
});

test("the prompt's progress: prompt <stage> draws one icon in the title row", () => {
  const m = panelWith();
  const panel = m.ctx.panel;
  let now = 1000;
  panel.clock = () => now;
  const arcs = () => m.ctx.mgraphics.calls.filter((c) => c[0] === "arc" && c[2] < M_TITLE).length;
  const paint = () => { m.ctx.mgraphics.calls.length = 0; m.ctx.paint(); };

  paint();
  const idle = arcs();
  m.send("prompt", "thinking");
  assert.equal(panel.prompt.stage, "thinking");
  paint();
  assert.ok(arcs() > idle, "the icon is drawn in the title row");
  assert.ok(panel.promptMoving(), "and it moves");
  m.send("prompt", "calling", "get_chord");
  assert.deepEqual([panel.prompt.stage, panel.prompt.detail], ["calling", "get_chord"]);
  m.send("prompt", "done", 120, 3400);
  assert.ok(panel.promptShown());
  now += 5000;
  assert.ok(!panel.promptShown() && !panel.promptMoving(), "done fades out");
  m.send("prompt", "error", "the", "model", "is", "not", "ready");
  now += 60000;
  assert.ok(panel.promptShown() && !panel.promptMoving(), "an error stays, still");
  m.send("prompt", "idle");
  assert.ok(!panel.promptShown());
  for (const stage of ["received", "queued", "starting", "sent", "writing", "running", "stopped", "whatever"]) {
    m.send("prompt", stage);
    paint();
  }
});

test("the description comes with the spec, is drawn under the title and is kept with the patch", () => {
  const m = panelWith(Object.assign({}, SPEC, { description: "  Random walks,\n in a narrow range " }));
  const panel = m.ctx.panel;
  assert.equal(panel.description, "Random walks, in a narrow range");
  m.ctx.paint();
  assert.ok(m.ctx.mgraphics.calls.some((c) => c[0] === "show_text" && String(c[1]).indexOf("Random walks") === 0));
  m.ctx.save();
  const fresh = loadPanel({ width: 320, height: 100 });
  fresh.send("restore", m.embedded[m.embedded.length - 1][1]);
  assert.equal(fresh.ctx.panel.description, "Random walks, in a narrow range");
  m.send("spec", JSON.stringify(SPEC));
  assert.equal(panel.description, "", "a file without one clears it");
});

test("a wider panel draws bigger, as far as its height holds it; height left over goes to lists and curves", () => {
  const panel = loadPanel({ width: 320, height: 100 }).ctx.panel;
  panel.setSpec(SPEC);
  const natural = panel.layout(300);
  assert.equal(panel.scale, 1);
  const small = panel.rows.find((r) => r.item.name === "amount").control;
  // twice as wide, height to spare: everything twice as big
  panel.layout(600, natural * 3);
  assert.equal(panel.scale, 2);
  const big = panel.rows.find((r) => r.item.name === "amount").control;
  assert.ok(big.h === small.h * 2 && big.w >= small.w * 2, "controls grow with the panel");
  // the rest grows less: the title row and its buttons a third as much
  assert.equal(panel.chrome, 1 + 0.33);
  assert.ok(Math.abs(panel.places.setActive.h - 20 * 1.33) < 1e-9, "set active grows a third as much");
  assert.ok(panel.places.repeat.w < 50 * 2, "so do the output buttons");
  // twice as wide, the same height: as big as the height holds (here, scale 1)
  panel.layout(600, natural);
  assert.equal(panel.scale, 1);
  // as wide, much taller: the list and the curve take the height, the slider does not
  panel.layout(300, natural + 200);
  assert.equal(panel.scale, 1);
  const list = panel.rows.find((r) => r.item.name === "durs").control;
  const curve = panel.rows.find((r) => r.item.name === "shape").control;
  assert.equal(panel.rows.find((r) => r.item.name === "amount").control.h, small.h);
  assert.ok(Math.abs(list.h - (58 + 100)) < 0.01 && Math.abs(curve.h - (76 + 100)) < 0.01, "the spare 200 px shared");
  // capped: a list at most M.tallGrow times its height
  panel.layout(300, natural + 5000);
  assert.ok(panel.rows.find((r) => r.item.name === "durs").control.h <= 58 * 4 + 0.01);
});

test("bigger controls are more precise: finer marks, free values to the pixel", () => {
  const base = legacyRequire("bachmcp.gui.params.base.js");
  // a semitone grid over 8 octaves: octave marks when narrow, semitones when wide enough
  assert.equal(base.tickStep(9600, 200, 100, 6, true), 1200);
  assert.equal(base.tickStep(9600, 700, 100, 6, true), 100);
  assert.equal(base.tickStep(100, 300, 1, 6, false), 2);
  assert.equal(base.tickStep(100, 600, 1, 6, false), 1);
  assert.equal(base.tickStep(1e6, 10, 1, 6, false), 0, "nothing when even the coarsest step does not fit");
  const panel = loadPanel({ width: 320, height: 100 }).ctx.panel;
  panel.setSpec(SPEC);
  const amount = panel.find("amount");
  amount.accept([0.123456]);
  panel.layout(300);
  const narrow = amount.text();
  panel.layout(300 * 20);  // far wider than scale 2: a pixel is worth a finer step
  assert.ok(amount.text().length >= narrow.length, `${amount.text()} vs ${narrow}`);
  assert.ok(amount.resolution < 0.001);
  // drawing at scale 2 works for every element
  const g = loadPanel({ width: 600, height: 2000 });
  g.send("spec", JSON.stringify(SPEC));
  g.ctx.paint();
});

// ── set_type: the base panel of a type, before any algorithm ───────────── //

test("set_type: the base panel of each type before any algorithm; kept by clear and with the patch", () => {
  const plain = loadPanel({ width: 320, height: 400 });
  assert.deepEqual(texts(plain).filter((t) => /algorithm|capture|generator|transformer/.test(t)), ["No algorithm loaded."],
    "no type: only the line");
  for (const [type, hasSource, dumpSel] of [["generator", false, false], ["transformer", true, false],
    ["selector", true, true]]) {
    const m = loadPanel({ width: 320, height: 400 });
    m.send("set_name", "a1");
    m.send("set_type", type);
    const p = m.ctx.panel;
    assert.equal(p.type, type);
    const shown = texts(m);
    assert.ok(shown.includes(type), `${type}: the type in the title row`);
    assert.ok(shown.includes("a1") && shown.includes("No algorithm loaded.") && shown.includes("bypass"), type);
    assert.equal(shown.includes("capture"), hasSource, `${type}: the source row`);
    assert.equal(shown.includes("dump sel."), dumpSel, type);
    m.send("clear");
    assert.equal(p.type, type, "clear keeps the type");
    m.ctx.save();
    const again = loadPanel({ width: 320, height: 400 });
    again.send("restore", m.embedded.pop()[1]);
    assert.equal(again.ctx.panel.type, type, "saved with the patch");
    assert.equal(again.ctx.panel.hasSource(), hasSource);
  }
});

test("set_type: a base panel's controls work before a load; a bad type is said once", () => {
  const m = loadPanel({ width: 320, height: 400 });
  m.send("set_type", "transformer");
  texts(m);
  const r = m.ctx.panel.captureRect(m.ctx.panel.width);
  m.ctx.onclick(r.x + 2, r.y + 2, 1, 0, 0, 0, 0, 0);
  release(m);
  assert.deepEqual(sent(m), [["capture"]]);
  m.send("set_type", "sorter");
  assert.match(m.posts.join(""), /set_type is generator, transformer or selector, got sorter/);
  assert.equal(m.ctx.panel.type, "transformer");
  m.send("spec", JSON.stringify(Object.assign({}, SPEC, { type: "transformer" })));
  assert.ok(texts(m).includes("transformer"));
  assert.ok(!texts(m).includes("No algorithm loaded."));
});

test("a panel saved before the spec said type: its kind gives the type", () => {
  for (const [kind, type] of [["producer", "generator"], ["transformer", "transformer"], ["selector", "selector"]]) {
    const m = loadPanel({ width: 320, height: 400 });
    m.send("restore", JSON.stringify(Object.assign({}, SPEC, { kind })));
    assert.equal(m.ctx.panel.type, type, kind);
  }
});

test("spec_file builds the panel from a .json file (as send_gen writes for a synth or an fx)", () => {
  const folder = fs.mkdtempSync(path.join(require("os").tmpdir(), "bachmcp-spec "));  // a space in the path
  const file = path.join(folder, "jeje.json");
  fs.writeFileSync(file, JSON.stringify({
    description: "Une voix FM très brillante.", type: "synth",
    inlets: [{ index: 1, about: "pitch" }], outlets: [{ index: 1, about: "left" }],
    params: [
      { name: "ratio", type: "slider", kind: "", range: [0.5, 8], step: 0.01, value: 2, grid: 0.01, default: 2, send: 2 },
      { name: "shape", type: "menu", options: ["sine", "saw"], value: "saw", default: "saw", send: 1 },
      { name: "drive", type: "toggle", value: true, default: true, send: 1 },
    ],
    buffers: [],
  }));
  const m = loadPanel({ width: 320, height: 100 });
  m.send("spec_file", ...file.split(" "));  // as Max hands it over: split at the space
  assert.deepEqual(Array.from(m.ctx.panel.items, (it) => it.name), ["ratio", "shape", "drive"]);
  assert.equal(m.ctx.panel.title, "jeje");
  assert.equal(m.ctx.panel.path, file);
  assert.equal(m.ctx.panel.description, "Une voix FM très brillante.");
  assert.equal(m.posts.length, 0);

  m.send("spec_file", path.join(folder, "nobody.json"));
  assert.match(m.posts.pop(), /cannot open/);
  fs.writeFileSync(file, "{ not json");
  m.send("spec_file", file);
  assert.match(m.posts.pop(), /is not JSON/);
  assert.equal(m.ctx.panel.items.length, 3, "a file that cannot be read leaves the panel as it was");
  fs.rmSync(folder, { recursive: true });
});
