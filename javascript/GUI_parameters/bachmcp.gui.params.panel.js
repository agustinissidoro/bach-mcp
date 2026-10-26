/*
bachmcp.gui.params.panel.js
---------------------------
The Panel: it lays out one row per parameter (curve and list get a drawing area
below their name), draws the rows and the title row, and turns mouse gestures into
"<param> <value...>" messages for a runner (runners/). It also gives its state to
be saved with the patch and to pattr (snapshot, restore, flat values).

A transformer's title row also has its source mode: "keep" (the original score
stays until capture) or "follow" (every score at the runner's inlet becomes the
source); clicking it sends "sourcemode keep|follow". "snap" makes drags land on
the grid; alt inverts it while dragging.

Written in ECMAScript 5, because jsui runs Max's legacy JavaScript engine (it
also runs unchanged in v8ui and in Node, where the tests draw it on a mock).
jsui's require gives a module only `exports`, so every name leaves through it.
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
  label = base.label;
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
  this.snap = true;  // drags snap to each element's grid; alt inverts it for one gesture
  this.sourceMode = "keep";  // transformers: "keep" the original, or "follow" every input
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
      if (item.accept(was.atoms()) && !same(before, item.atoms())) messages.push([item.name].concat(item.atoms()));
    }
    this.items.push(item);
  }
  this.active = null;
  this.width = 0;
  // the runner starts in keep mode: tell it the mode this panel is in
  if (this.kind === "transformer" && this.sourceMode !== "keep") messages.push(["sourcemode", this.sourceMode]);
  return messages;
};

/** The source mode set from outside (the runner's echo): shown, not sent back. */
Panel.prototype.setSourceMode = function (mode) {
  if (mode !== "keep" && mode !== "follow") return false;
  this.sourceMode = mode;
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

/** The button that takes the score in the roll as the transformer's new source. */
Panel.prototype.captureRect = function (width) {
  var right = this.hasGrid() ? this.snapRect(width).x - 4 : width - M.pad - 4;
  return { x: right - 58, y: 3, w: 58, h: M.title - 6 };
};

/** The switch between keeping the original source and following every input. */
Panel.prototype.modeRect = function (width) {
  var c = this.captureRect(width);
  return { x: c.x - 50, y: c.y, w: 46, h: c.h };
};

/** The switch that turns snapping to the grid on and off. */
Panel.prototype.snapRect = function (width) {
  return { x: width - M.pad - 46, y: 3, w: 42, h: M.title - 6 };
};

Panel.prototype.hasGrid = function () {
  for (var i = 0; i < this.items.length; i++) if (this.items[i].grid > 0) return true;
  return false;
};

Panel.prototype.labelWidth = function () {
  var longest = 0;
  for (var i = 0; i < this.items.length; i++) longest = Math.max(longest, this.items[i].name.length);
  return clamp(Math.ceil(longest * M.charWidth) + 8, M.labelMin, M.labelMax);
};

Panel.prototype.valueWidth = function () {
  var longest = 0;
  for (var i = 0; i < this.items.length; i++) {
    if (!this.items[i].tall) longest = Math.max(longest, this.items[i].widest().length);
  }
  return clamp(Math.ceil(longest * M.charWidth) + 8, M.valueMin, M.valueMax);
};

/** Place every element for this width; returns the height the panel needs. */
Panel.prototype.layout = function (width) {
  this.width = width;
  this.rows = [];
  var lw = this.labelWidth();
  var vw = this.valueWidth();
  var y = M.title + M.pad;
  var inner = width - 2 * M.pad;
  for (var i = 0; i < this.items.length; i++) {
    var item = this.items[i];
    var row = { item: item, y: y };
    row.label = { x: M.pad + 4, y: y, w: lw - 4, h: M.row };
    row.value = { x: width - M.pad - vw, y: y, w: vw - 4, h: M.row };
    if (item.tall) {
      row.label.w = inner / 2 - 4;
      row.value = { x: M.pad + inner / 2, y: y, w: inner / 2 - 4, h: M.row };
      row.control = { x: M.pad + 4, y: y + M.row, w: inner - 8, h: item.tall };
      row.h = M.row + item.tall + 4;
    } else {
      row.control = { x: M.pad + lw + 6, y: y, w: Math.max(30, inner - lw - vw - 10), h: M.row };
      if (item.type === "menu") row.control.w = Math.max(30, inner - lw - 10);
      row.h = M.row;
    }
    this.rows.push(row);
    y += row.h + M.gap;
  }
  return y + M.pad + M.status;
};

Panel.prototype.paint = function (g, width, height) {
  if (width !== this.width) this.layout(width);
  box(g, 0, 0, width, height, THEME.bg);
  var titleWidth = width - 2 * M.pad - 8;
  if (this.hasGrid()) {
    var sw = this.snapRect(width);
    rounded(g, sw.x, sw.y, sw.w, sw.h, 3, this.snap ? THEME.fill : THEME.track);
    label(g, "snap", sw, "center", this.snap ? THEME.bg : THEME.dim, 10);
    titleWidth = sw.x - M.pad - 10;
  }
  if (this.kind === "transformer") {
    var b = this.captureRect(width);
    rounded(g, b.x, b.y, b.w, b.h, 3, THEME.fill);
    label(g, "capture", b, "center", THEME.bg, 10);
    var mr = this.modeRect(width);
    var follow = this.sourceMode === "follow";
    rounded(g, mr.x, mr.y, mr.w, mr.h, 3, follow ? THEME.fill : THEME.track);
    label(g, follow ? "follow" : "keep", mr, "center", follow ? THEME.bg : THEME.text, 10);
    var src = this.source && this.source.notes ? "source: " + this.source.notes + " notes" : "no source";
    var srcBox = { x: mr.x - 112, y: 0, w: 106, h: M.title };
    label(g, src, srcBox, "right", this.source && this.source.notes ? THEME.dim : THEME.error, 10);
    titleWidth = srcBox.x - M.pad - 10;
  }
  label(g, this.title || "bachmcp.gui.params", { x: M.pad + 4, y: 0, w: titleWidth, h: M.title },
    "left", this.title ? THEME.text : THEME.dim, THEME.titleSize);
  if (!this.items.length) {
    label(g, this.title ? "no parameters" : "waiting for a runner", { x: M.pad + 4, y: M.title, w: width - 2 * M.pad, h: M.row },
      "left", THEME.dim);
  }
  for (var i = 0; i < this.rows.length; i++) {
    var row = this.rows[i];
    if (row.y > height) break;
    box(g, M.pad, row.y, width - 2 * M.pad, row.h, THEME.row);
    label(g, row.item.name, row.label, "left", THEME.text);
    row.item.paint(g, row.control);
    var t = row.item.text();
    if (t) label(g, t, row.value, "right", THEME.dim);
  }
  var s = this.state;
  if (s.kind) {
    label(g, (s.kind === "ok" ? "" : s.kind + ": ") + s.text, { x: M.pad + 4, y: height - M.status, w: width - 2 * M.pad - 8, h: M.status - 2 },
      "left", s.kind === "error" ? THEME.error : THEME.ok, 10);
  }
};

Panel.prototype.rowAt = function (x, y) {
  for (var i = 0; i < this.rows.length; i++) if (inside(this.rows[i].control, x, y)) return this.rows[i];
  return null;
};

Panel.prototype.message = function (item) {
  return [item.name].concat(item.atoms());
};

Panel.prototype.mouseDown = function (x, y, mods) {
  if (this.kind === "transformer" && this.width && inside(this.captureRect(this.width), x, y)) {
    this.active = null;
    return [["capture"]];
  }
  if (this.kind === "transformer" && this.width && inside(this.modeRect(this.width), x, y)) {
    this.active = null;
    this.sourceMode = this.sourceMode === "keep" ? "follow" : "keep";
    return [["sourcemode", this.sourceMode]];
  }
  if (this.hasGrid() && this.width && inside(this.snapRect(this.width), x, y)) {
    this.active = null;
    this.snap = !this.snap;
    return [];
  }
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
  this.sourceMode = snapshot.sourceMode === "follow" ? "follow" : "keep";
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
