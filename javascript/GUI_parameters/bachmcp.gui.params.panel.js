/*
bachmcp.gui.params.panel.js
---------------------------
The Panel: a title row (the algorithm and its kind), then two sections.
"Options": snap (drags land on the grid; alt inverts it while dragging) and
reset all; a transformer adds its source card: how many notes, write
(write_to_playground), capture (capture_source) and the source mode as two
segments, non-destructive (the source is held; every output starts again from
it) or destructive (every score at the runner's inlet becomes the source), sent
as "source_mode 1|0". "Parameters": one card each, its name and value above its
control. A status line closes the panel.

The Panel turns mouse gestures into "param <name> <value...>" messages for a runner
(runners/) and gives its state to be saved with the patch and to pattr
(snapshot, restore, flat values).

Drawn by bachmcp.gui.params.v8ui.js. Kept in ECMAScript 5 with `exports` only,
so it also loads in the legacy engine and in Node (the tests draw it on a mock).
*/
"use strict";

// Max finds a file by its name, on the search path; Node by where it is.
function need(name) {
  try {
    return require(name);
  } catch (e) {
    return require("./" + name);
  }
}

var base = need("bachmcp.gui.params.base.js");
var elements = need("bachmcp.gui.params.elements.js");
var THEME = base.THEME,
  M = base.M,
  clamp = base.clamp,
  snap = base.snap,
  copy = base.copy,
  same = base.same,
  inside = base.inside,
  box = base.box,
  rounded = base.rounded,
  label = base.label,
  outline = base.outline,
  dot = base.dot;
var makeElement = elements.makeElement;

function Panel() {
  this.clear();
}

Panel.prototype.clear = function () {
  this.title = "";
  this.path = "";
  this.kind = "producer";
  this.source = null;  // transformers: {notes, from}
  this.items = [];
  this.rows = [];
  this.state = { kind: "", text: "" };
  this.width = 0;
  this.active = null;
  this.places = null;
  this.hover = null;
  this.snap = true;  // drags snap to each element's grid; alt inverts it for one gesture
  this.sourceMode = "nondestructive";  // transformers: or "destructive" (see the runner)
};

/**
 * Show a new set of parameters. A parameter that keeps its name and type keeps the
 * value it has here, so reloading code (or reopening the patch) does not lose the
 * user's settings. Returns the messages to send for the values kept that way.
 */
Panel.prototype.setSpec = function (spec) {
  var old = {}, i;
  for (i = 0; i < this.items.length; i++) old[this.items[i].name] = this.items[i];
  this.title = spec.title || "";
  this.path = spec.path || "";
  this.kind = spec.kind || "producer";
  this.source = spec.source || null;
  this.items = [];
  var messages = [];
  var params = spec.params || [];
  for (i = 0; i < params.length; i++) {
    var item = makeElement(params[i]);
    var was = old[item.name];
    if (was && was.type === item.type) {
      if (was.kind === item.kind && params[i].display === undefined) item.display = was.display;
      var before = item.atoms();
      if (item.accept(was.atoms()) && !same(before, item.atoms())) messages.push(this.message(item));
    }
    this.items.push(item);
  }
  this.active = null;
  this.width = 0;
  this.places = null;
  // the runner starts nondestructive: tell it the mode this panel is in
  if (this.kind === "transformer" && this.sourceMode !== "nondestructive") messages.push(["source_mode", 0]);
  return messages;
};

/** The source mode set from outside (the runner's echo): shown, not sent back. */
Panel.prototype.setSourceMode = function (flag) {
  if (String(flag) !== "0" && String(flag) !== "1") return false;
  this.sourceMode = String(flag) === "0" ? "destructive" : "nondestructive";
  return true;
};

Panel.prototype.find = function (name) {
  for (var i = 0; i < this.items.length; i++) if (this.items[i].name === name) return this.items[i];
  return null;
};

/** A value set from outside (the runner's echo): shown, not sent back. */
Panel.prototype.setValue = function (name, atoms) {
  var item = this.find(name);
  return item ? item.accept(atoms) : false;
};

Panel.prototype.setStatus = function (kind, text) {
  this.state = { kind: String(kind || ""), text: String(text || "") };
};

/** A transformer's source score: how many notes, and where it was taken from. */
Panel.prototype.setSource = function (notes, from) {
  this.source = { notes: Number(notes) || 0, from: String(from || "") };
};

/** Where the options are, for this width: computed by layout(). */
Panel.prototype.ui = function (width) {
  if (!this.places || width !== this.width) this.layout(width);
  return this.places;
};

/** The button that takes the score in the roll as the transformer's new source. */
Panel.prototype.captureRect = function (width) {
  return this.ui(width).capture;
};

/** The button that writes the source to the playground (write_to_playground). */
Panel.prototype.writeRect = function (width) {
  return this.ui(width).write;
};

/** The switch between holding the source (non-destructive) and working on every result (destructive). */
Panel.prototype.modeRect = function (width) {
  return this.ui(width).mode;
};

/** The switch that turns snapping to the grid on and off. */
Panel.prototype.snapRect = function (width) {
  return this.ui(width).snap;
};

/** The button that sets every parameter back to its declared value. */
Panel.prototype.resetRect = function (width) {
  return this.ui(width).reset;
};

Panel.prototype.hasGrid = function () {
  for (var i = 0; i < this.items.length; i++) if (this.items[i].grid > 0) return true;
  return false;
};

Panel.prototype.valueWidth = function () {
  var longest = 0;
  for (var i = 0; i < this.items.length; i++) longest = Math.max(longest, this.items[i].widest().length);
  return clamp(Math.ceil(longest * M.charWidth) + 12, M.valueMin, M.valueMax);
};

/**
 * Place everything for this width; returns the height the panel needs.
 * Title row, then "options" (snap, reset; a transformer's source), then
 * "parameters": one card each, its name and value above its control.
 */
Panel.prototype.layout = function (width) {
  this.width = width;
  this.rows = [];
  var p = { snap: null, reset: null, capture: null, write: null, mode: null, source: null, sections: [] };
  this.places = p;
  var inner = width - 2 * M.pad;
  var y = M.title + M.gap;
  if (!this.items.length && !this.title) return y + M.row + M.status;
  p.sections.push({ text: "options", y: y });
  y += M.section;
  var x = M.pad;
  if (this.hasGrid()) {
    p.snap = { x: x, y: y, w: 58, h: M.button };
    x += 62;
  }
  p.reset = { x: x, y: y, w: 62, h: M.button };
  y += M.button + M.gap;
  if (this.kind === "transformer") {
    var cardY = y;
    p.capture = { x: width - M.pad - 6 - 56, y: y + 6, w: 56, h: M.button };
    p.write = { x: p.capture.x - 50, y: y + 6, w: 46, h: M.button };
    p.source = { x: M.pad + 8, y: y + 6, w: p.write.x - M.pad - 14, h: M.button };
    p.mode = { x: M.pad + 6, y: y + 6 + M.button + M.gap, w: inner - 12, h: M.button };
    y = p.mode.y + M.button + 6;
    p.sourceCard = { x: M.pad, y: cardY, w: inner, h: y - cardY };
    y += M.gap;
  }
  p.sections.push({ text: "parameters" + (this.items.length ? " · " + this.items.length : ""), y: y + 2 });
  y += M.section + 2;
  var vw = this.valueWidth();
  for (var i = 0; i < this.items.length; i++) {
    var item = this.items[i];
    var row = { item: item, y: y };
    row.label = { x: M.pad + 8, y: y + 4, w: inner - vw - 20, h: M.head };
    row.value = { x: width - M.pad - 8 - vw, y: y + 4, w: vw, h: M.head };
    var ch = item.tall || M.row;
    row.control = { x: M.pad + 8, y: y + 4 + M.head + 2, w: inner - 16, h: ch };
    row.h = 4 + M.head + 2 + ch + 6;
    this.rows.push(row);
    y += row.h + M.gap;
  }
  return y + M.status;
};

function button(g, r, text, on, hot) {
  rounded(g, r.x, r.y, r.w, r.h, 4, on ? THEME.fill : (hot ? THEME.buttonHover : THEME.button));
  label(g, text, r, "center", on ? THEME.bg : THEME.text, 10);
}

Panel.prototype.hot = function (r) {
  return Boolean(r && this.hover && inside(r, this.hover[0], this.hover[1]));
};

Panel.prototype.paint = function (g, width, height) {
  if (width !== this.width || !this.places) this.layout(width);
  var p = this.places;
  box(g, 0, 0, width, height, THEME.bg);
  // title row
  box(g, 0, 0, width, M.title, THEME.header);
  box(g, 0, M.title - 1, width, 1, THEME.line);
  var kindText = this.title ? (this.kind === "transformer" ? "transformer" : "generator") : "";
  var titleRight = width - M.pad;
  if (kindText) {
    var kw = kindText.length * 6 + 14;
    var kr = { x: width - M.pad - kw, y: (M.title - 16) / 2, w: kw, h: 16 };
    rounded(g, kr.x, kr.y, kr.w, kr.h, 8, THEME.button);
    label(g, kindText, kr, "center", THEME.dim, THEME.smallSize);
    titleRight = kr.x - 6;
  }
  label(g, this.title || "bachmcp.gui.params", { x: M.pad + 2, y: 0, w: titleRight - M.pad - 2, h: M.title },
    "left", this.title ? THEME.text : THEME.dim, THEME.titleSize, THEME.bold);
  if (!this.items.length && !this.title) {
    label(g, "waiting for a runner", { x: M.pad + 2, y: M.title + M.gap, w: width - 2 * M.pad, h: M.row }, "left", THEME.dim);
  }
  for (var k = 0; k < p.sections.length; k++) {
    var sec = p.sections[k];
    label(g, sec.text.toUpperCase(), { x: M.pad + 2, y: sec.y, w: width - 2 * M.pad, h: M.section - 4 },
      "left", THEME.faint, THEME.smallSize, THEME.bold);
  }
  if (p.snap) button(g, p.snap, this.snap ? "snap on" : "snap off", this.snap, this.hot(p.snap));
  if (p.reset) button(g, p.reset, "reset all", false, this.hot(p.reset));
  if (p.sourceCard) {
    var c = p.sourceCard;
    rounded(g, c.x, c.y, c.w, c.h, M.radius, THEME.card);
    var has = this.source && this.source.notes;
    var from = has && this.source.from ? " · " + this.source.from : "";
    label(g, has ? "source: " + this.source.notes + " notes" + from : "no source", p.source, "left",
      has ? THEME.text : THEME.error);
    button(g, p.write, "write", false, this.hot(p.write));
    button(g, p.capture, "capture", true, false);
    if (this.hot(p.capture)) outline(g, p.capture.x, p.capture.y, p.capture.w, p.capture.h, 4, THEME.knob);
    // the source mode, as two segments
    var m = p.mode, half = m.w / 2, destructive = this.sourceMode === "destructive";
    rounded(g, m.x, m.y, m.w, m.h, 4, THEME.well);
    var on = { x: m.x + (destructive ? half : 0) + 2, y: m.y + 2, w: half - 4, h: m.h - 4 };
    rounded(g, on.x, on.y, on.w, on.h, 3, THEME.fill);
    label(g, "non-destructive", { x: m.x, y: m.y, w: half, h: m.h }, "center", destructive ? THEME.dim : THEME.bg, 10);
    label(g, "destructive", { x: m.x + half, y: m.y, w: half, h: m.h }, "center", destructive ? THEME.bg : THEME.dim, 10);
  }
  if (this.title && !this.items.length) {
    label(g, "no parameters", { x: M.pad + 2, y: (p.sections.length ? p.sections[p.sections.length - 1].y : M.title) + M.section,
      w: width - 2 * M.pad, h: M.row }, "left", THEME.dim);
  }
  for (var i = 0; i < this.rows.length; i++) {
    var row = this.rows[i];
    if (row.y > height) break;
    var active = this.active === row;
    var hovered = this.hover && this.hover[1] >= row.y && this.hover[1] <= row.y + row.h;
    rounded(g, M.pad, row.y, width - 2 * M.pad, row.h, M.radius, active || hovered ? THEME.cardHover : THEME.card);
    if (active) outline(g, M.pad, row.y, width - 2 * M.pad, row.h, M.radius, THEME.fillDim);
    label(g, row.item.name, row.label, "left", THEME.text, THEME.fontSize, THEME.bold);
    row.item.paint(g, row.control);
    var t = row.item.text();
    if (t) {
      var switchable = row.item.displays().length > 1;
      if (switchable && this.hot(row.value)) rounded(g, row.value.x - 2, row.value.y, row.value.w + 4, row.value.h, 3, THEME.button);
      label(g, t, row.value, "right", switchable ? THEME.knob : THEME.dim);
    }
  }
  var s = this.state;
  var sy = height - M.status;
  box(g, 0, sy, width, M.status, THEME.header);
  box(g, 0, sy, width, 1, THEME.line);
  if (s.kind) {
    var sc = s.kind === "error" ? THEME.error : THEME.ok;
    dot(g, M.pad + 4, sy + M.status / 2, 3, sc);
    label(g, (s.kind === "ok" ? "" : s.kind + ": ") + s.text, { x: M.pad + 12, y: sy, w: width - 2 * M.pad - 12, h: M.status },
      "left", s.kind === "error" ? THEME.error : THEME.dim, 10);
  }
};

/** The mouse over the panel without a button (null: it left). True when the drawing changes. */
Panel.prototype.mouseMove = function (x, y) {
  var before = JSON.stringify(this.hover);
  this.hover = x === null || x === undefined ? null : [x, y];
  return JSON.stringify(this.hover) !== before;
};

Panel.prototype.rowAt = function (x, y) {
  for (var i = 0; i < this.rows.length; i++) if (inside(this.rows[i].control, x, y)) return this.rows[i];
  return null;
};

Panel.prototype.message = function (item) {
  return ["param", item.name].concat(item.atoms());
};

Panel.prototype.mouseDown = function (x, y, mods) {
  var p = this.width ? this.ui(this.width) : {};
  this.active = null;
  if (p.capture && inside(p.capture, x, y)) return [["capture_source"]];
  if (p.write && inside(p.write, x, y)) return [["write_to_playground"]];
  if (p.mode && inside(p.mode, x, y)) {
    var mode = x >= p.mode.x + p.mode.w / 2 ? "destructive" : "nondestructive";
    if (mode === this.sourceMode) return [];
    this.sourceMode = mode;
    return [["source_mode", mode === "destructive" ? 0 : 1]];
  }
  if (p.snap && inside(p.snap, x, y)) {
    this.snap = !this.snap;
    return [];
  }
  if (p.reset && inside(p.reset, x, y)) return this.resetAll();
  for (var i = 0; i < this.rows.length; i++) {
    if (inside(this.rows[i].value, x, y) && this.rows[i].item.nextDisplay()) {
      this.active = null;
      if (this.width) this.layout(this.width);  // the value column may need another width
      return [];
    }
  }
  var row = this.rowAt(x, y);
  this.active = row;
  if (!row) return [];
  mods = mods || {};
  row.item.snapping = this.snap !== Boolean(mods.alt);
  return row.item.down(row.control, x, y, mods) ? [this.message(row.item)] : [];
};

Panel.prototype.mouseDrag = function (x, y, mods) {
  var row = this.active;
  if (!row) return [];
  mods = mods || {};
  row.item.snapping = this.snap !== Boolean(mods.alt);
  return row.item.drag(row.control, x, y, mods) ? [this.message(row.item)] : [];
};

Panel.prototype.mouseUp = function () {
  if (this.active) this.active.item.grab = null;
  this.active = null;
};

/** Double-click on a control: back to the value the algorithm declares. */
Panel.prototype.doubleClick = function (x, y) {
  var row = this.rowAt(x, y);
  if (!row) return [];
  var before = row.item.atoms();
  row.item.reset();
  return same(before, row.item.atoms()) ? [] : [this.message(row.item)];
};

Panel.prototype.resetAll = function () {
  var out = [];
  for (var i = 0; i < this.items.length; i++) {
    var before = this.items[i].atoms();
    this.items[i].reset();
    if (!same(before, this.items[i].atoms())) out.push(this.message(this.items[i]));
  }
  return out;
};

Panel.prototype.allMessages = function () {
  var out = [];
  for (var i = 0; i < this.items.length; i++) out.push(this.message(this.items[i]));
  return out;
};

// ── Saving with the patch, presets ──────────────────────────────────────── //

Panel.prototype.snapshot = function () {
  var params = [];
  for (var i = 0; i < this.items.length; i++) {
    var it = this.items[i];
    params.push({ name: it.name, type: it.type, range: it.range, step: it.step, unit: it.unit,
      options: it.options, value: copy(it.value), "default": copy(it.def),
      kind: it.kind, grid: it.grid, display: it.display });
  }
  return { title: this.title, path: this.path, kind: this.kind, source: this.source, params: params, snap: this.snap,
    sourceMode: this.sourceMode };
};

Panel.prototype.restore = function (snapshot) {
  this.setSpec({ title: snapshot.title, path: snapshot.path, kind: snapshot.kind, params: [] });
  this.sourceMode = snapshot.sourceMode === "destructive" ? "destructive" : "nondestructive";
  this.setSpec(snapshot);
  this.snap = snapshot.snap !== false;
};

/** Every value as one flat list of numbers, for pattr (menus as their index). */
Panel.prototype.flatValues = function () {
  var out = [];
  for (var i = 0; i < this.items.length; i++) {
    var it = this.items[i];
    if (it.type === "menu") out.push(it.index());
    else if (it.type === "curve") out.push(it.value.length);
    if (it.type !== "menu") out = out.concat(it.atoms());
  }
  return out;
};

Panel.prototype.setFlatValues = function (flat) {
  var out = [], k = 0;
  for (var i = 0; i < this.items.length && k < flat.length; i++) {
    var it = this.items[i], n;
    if (it.type === "menu") {
      var option = it.options[clamp(Math.round(flat[k++]), 0, it.options.length - 1)];
      if (option !== it.value) {
        it.value = option;
        out.push(this.message(it));
      }
      continue;
    }
    if (it.type === "range") n = 2;
    else if (it.type === "list") n = it.value.length;
    else if (it.type === "curve") n = 2 * flat[k++];
    else n = 1;
    var before = it.atoms();
    if (it.accept(flat.slice(k, k + n)) && !same(before, it.atoms())) out.push(this.message(it));
    k += n;
  }
  return out;
};

exports.Panel = Panel;
