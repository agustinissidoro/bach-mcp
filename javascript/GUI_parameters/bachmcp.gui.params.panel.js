/*
bachmcp.gui.params.panel.js
---------------------------
The Panel: a title row (the algorithm and its kind), then two sections.
Drags land on each slider's grid; alt lets one through. "Options": reset
all; then bypass ("bypass 0|1"), repeat ("repeat"); pitch cards toggle ½ | ¼ | free ("snap 0|1|3"), time cards 100ms | 10ms | free; a transformer adds its source card: how many notes, write
(write_to_playground), capture (capture_source) and the source mode as two
segments, non-destructive (the source is held; every output starts again from
it) or destructive (every score at the runner's inlet becomes the source), sent
as "source_mode 1|0". A selector has the same card, and under the mode
two more segments, whole score | selection only (sent as "dump_selection_only 0|1"). "Parameters": one card each, its name and value above its
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
  this.name = "";  // set_name: shown while no algorithm is loaded; kept by clear
  this.clear();
}

/** The instance's name, drawn while no algorithm is loaded. */
Panel.prototype.setName = function (name) {
  var next = name === undefined || name === null ? "" : String(name);
  if (next === this.name) return false;
  this.name = next;
  return !this.title;
};

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
  this.involutive = false;  // selectors: sel (false) or select (true)
  this.selectionOnly = true;  // selectors: dump_selection_only
  this.bypass = false;
  this.withinSelection = false;  // process_only_selection
  this.pitchSnap = 3;  // the output's pitches: 0 semitones, 1 quarter tones, 3 free
  this.timeSnap = 0;   // time sliders: 0 their own grid, 1 100 ms, 2 10 ms
};

/** Transformers and selectors work on a source: they have the source card. */
Panel.prototype.hasSource = function () {
  return this.kind === "transformer" || this.kind === "selector";
};

/** The two segments of the source mode, and whether the right one is on. */
Panel.prototype.modes = function () {
  return { left: "non-destructive", right: "destructive", on: this.sourceMode === "destructive" };
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
  this.applyGrids();
  this.active = null;
  this.width = 0;
  this.places = null;
  // the runner starts nondestructive: tell it the mode this panel is in
  if (this.hasSource() && this.sourceMode !== "nondestructive") messages.push(["source_mode", 0]);
  if (this.kind === "selector" && !this.selectionOnly) messages.push(["dump_selection_only", 0]);
  if (this.bypass) messages.push(["bypass", 1]);
  if (this.hasSource() && this.withinSelection) messages.push(["process_only_selection", 1]);
  if (this.pitchSnap !== 3) messages.push(["snap", this.pitchSnap]);
  return messages;
};

/** The source mode set from outside (the runner's echo): shown, not sent back. */
Panel.prototype.setSourceMode = function (flag) {
  if (String(flag) !== "0" && String(flag) !== "1") return false;
  this.sourceMode = String(flag) === "0" ? "destructive" : "nondestructive";
  return true;
};

/** A selector's mode set from outside (the runner's echo). */
Panel.prototype.setInvolutive = function (flag) {
  if (String(flag) !== "0" && String(flag) !== "1") return false;
  this.involutive = String(flag) === "1";
  return true;
};

/** A selector's dump_selection_only set from outside (the runner's echo). */
Panel.prototype.setSelectionOnly = function (flag) {
  if (String(flag) !== "0" && String(flag) !== "1") return false;
  this.selectionOnly = String(flag) === "1";
  return true;
};

/** bypass and snap set from outside (the runner's echo). */
Panel.prototype.setWithinSelection = function (flag) {
  if (String(flag) !== "0" && String(flag) !== "1") return false;
  this.withinSelection = String(flag) === "1";
  return true;
};

Panel.prototype.setBypass = function (flag) {
  if (String(flag) !== "0" && String(flag) !== "1") return false;
  this.bypass = String(flag) === "1";
  return true;
};

Panel.prototype.setPitchSnap = function (n) {
  if (["0", "1", "3"].indexOf(String(n)) < 0) return false;
  this.pitchSnap = Number(n);
  this.applyGrids();
  return true;
};

/**
 * The snap toggles, three states each, on the cards they act on. A pitch (or
 * interval) card's toggle is the runner's snap: ½ (semitones), ¼ (quarter
 * tones), free; it sets where those sliders drag to and is sent as "snap
 * 0|1|3". A time card's toggle only sets where time sliders drag to: 100 ms,
 * 10 ms, free (the slider's own grid).
 */
var PITCH_SNAPS = [[0, "\u00bd", 100], [1, "\u00bc", 50], [3, "free", 0]];
var TIME_SNAPS = [[1, "100ms", 100], [2, "10ms", 10], [0, "free", 0]];

function pitchy(item) {
  return item.kind === "pitch" || item.kind === "interval";
}

function timed(item) {
  return item.kind === "time";
}

function snapStates(item) {
  return pitchy(item) ? PITCH_SNAPS : timed(item) ? TIME_SNAPS : null;
}

function stateOf(states, value) {
  for (var i = 0; i < states.length; i++) if (states[i][0] === value) return i;
  return states.length - 1;
}

/** The toggle's state for this item: [value, text, step], or null if it has none. */
Panel.prototype.snapState = function (item) {
  var states = snapStates(item);
  if (!states) return null;
  return states[stateOf(states, pitchy(item) ? this.pitchSnap : this.timeSnap)];
};

/** A click on an item's toggle: the next state; the messages for the runner. */
Panel.prototype.nextSnap = function (item) {
  var states = snapStates(item);
  var next = states[(stateOf(states, pitchy(item) ? this.pitchSnap : this.timeSnap) + 1) % states.length][0];
  if (pitchy(item)) this.pitchSnap = next;
  else this.timeSnap = next;
  this.applyGrids();
  return pitchy(item) ? [["snap", next]] : [];
};

Panel.prototype.applyGrids = function () {
  for (var i = 0; i < this.items.length; i++) {
    var it = this.items[i];
    if (it.baseGrid === undefined) it.baseGrid = it.grid;
    var st = this.snapState(it);
    if (st) it.grid = st[2] || it.baseGrid;
  }
};

/** Whether a drag of this item snaps (before alt): always, on its toggle's step or its own grid. */
Panel.prototype.snapping = function (item) {
  var st = this.snapState(item);
  return st && st[2] ? true : this.snap;
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
  if (!this.places || width !== this.width) this.layout(width, this.height);
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
 * Place everything for this width (and height, when known); returns the height
 * the panel needs. Title row: the algorithm, its kind and the bypass toggle.
 * "output": repeat, write. Pitch and time cards carry their snap toggle
 * (see snapState). "source"
 * (transformers, selectors; its header says how many notes): capture and the
 * toggles destructive and, for selectors, selection only. "parameters": its
 * header holds the grid toggle and reset; one card each. When everything does
 * not fit the height, the panel is compact: smaller headers, and each
 * parameter on one line (name, control, value).
 */
Panel.prototype.layout = function (width, height) {
  this.height = height || 0;
  var full = this.place(width, false);
  if (height > 0 && full > height + 0.5) {
    this.compact = true;
    return this.place(width, true);
  }
  this.compact = false;
  return full;
};

Panel.prototype.place = function (width, compact) {
  this.width = width;
  this.rows = [];
  var p = { within: null, bypass: null, repeat: null, write: null, capture: null, mode: null, only: null,
    snap: null, reset: null, sections: [] };
  this.places = p;
  var inner = width - 2 * M.pad;
  var section = compact ? 14 : M.section;
  var y = M.title + M.gap;
  if (!this.items.length && !this.title) return y + M.row + M.status;
  p.bypass = { x: width - M.pad - 56, y: (M.title - M.button) / 2, w: 56, h: M.button };
  // output
  p.sections.push({ text: "output", y: y, h: section });
  y += section;
  p.repeat = { x: M.pad, y: y, w: 50, h: M.button };
  p.write = { x: M.pad + 54, y: y, w: 44, h: M.button };
  y += M.button + M.gap;
  // source
  if (this.hasSource()) {
    p.sections.push({ text: "source", y: y, h: section, source: true });
    y += section;
    var n = this.kind === "selector" ? 4 : 3, w = (inner - (n - 1) * 4) / n;
    p.capture = { x: M.pad, y: y, w: w, h: M.button };
    p.mode = { x: M.pad + w + 4, y: y, w: w, h: M.button };
    p.within = { x: M.pad + 2 * (w + 4), y: y, w: w, h: M.button };
    if (n === 4) p.only = { x: M.pad + 3 * (w + 4), y: y, w: w, h: M.button };
    y += M.button + M.gap;
  }
  // parameters, reset in the header
  var head = { text: "parameters" + (this.items.length ? " \u00b7 " + this.items.length : ""), y: y, h: section };
  p.sections.push(head);
  var by = y + (section - 16) / 2 - 1;
  p.reset = { x: width - M.pad - 44, y: by, w: 44, h: 16 };
  y += section + 2;
  var vw = this.valueWidth();
  var lw = clamp(Math.round(inner * 0.28), M.labelMin, M.labelMax);
  for (var i = 0; i < this.items.length; i++) {
    var item = this.items[i];
    var row = { item: item, y: y };
    var ch = item.tall || M.row;
    if (compact && !item.tall) {
      row.label = { x: M.pad + 8, y: y + 3, w: lw, h: M.row };
      row.value = { x: width - M.pad - 6 - vw, y: y + 3, w: vw, h: M.row };
      row.control = { x: row.label.x + lw + 4, y: y + 3, w: row.value.x - row.label.x - lw - 10, h: M.row };
      row.h = M.row + 6;
    } else {
      row.label = { x: M.pad + 8, y: y + 4, w: inner - vw - 20, h: M.head };
      row.value = { x: width - M.pad - 8 - vw, y: y + 4, w: vw, h: M.head };
      row.control = { x: M.pad + 8, y: y + 4 + M.head + 2, w: inner - 16, h: ch };
      row.h = 4 + M.head + 2 + ch + 6;
    }
    if (snapStates(item)) {
      // the snap toggle, left of the value
      row.snapToggle = { x: row.value.x - 42, y: row.value.y + (row.value.h - 16) / 2, w: 38, h: 16 };
      if (compact) row.control.w -= 42;
      else row.label.w -= 42;
    }
    this.rows.push(row);
    y += row.h + (compact ? 2 : M.gap);
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
  if (width !== this.width || height !== this.height || !this.places) this.layout(width, height);
  var p = this.places;
  box(g, 0, 0, width, height, THEME.bg);
  // title row
  box(g, 0, 0, width, M.title, THEME.header);
  box(g, 0, M.title - 1, width, 1, THEME.line);
  var kindText = this.title ? ({ transformer: "transformer", selector: "selector" }[this.kind] || "generator") : "";
  var titleRight = p.bypass ? p.bypass.x - 6 : width - M.pad;
  if (kindText) {
    var kw = kindText.length * 6 + 14;
    var kr = { x: titleRight - kw, y: (M.title - 16) / 2, w: kw, h: 16 };
    rounded(g, kr.x, kr.y, kr.w, kr.h, 8, THEME.button);
    label(g, kindText, kr, "center", THEME.dim, THEME.smallSize);
    titleRight = kr.x - 6;
  }
  // no algorithm: the instance's name (set_name) over "No algorithm loaded.", or that alone
  label(g, this.title || this.name || "No algorithm loaded.", { x: M.pad + 2, y: 0, w: titleRight - M.pad - 2, h: M.title },
    "left", this.title || this.name ? THEME.text : THEME.dim, THEME.titleSize, THEME.bold);
  if (!this.items.length && !this.title && this.name) {
    label(g, "No algorithm loaded.", { x: M.pad + 2, y: M.title + M.gap, w: width - 2 * M.pad, h: M.row }, "left", THEME.dim);
  }
  if (p.bypass) button(g, p.bypass, this.bypass ? "bypassed" : "bypass", this.bypass, this.hot(p.bypass));
  for (var k = 0; k < p.sections.length; k++) {
    var sec = p.sections[k];
    var text = sec.text.toUpperCase(), tc = THEME.faint;
    if (sec.source) {
      var has = this.source && this.source.notes;
      text += has ? " \u00b7 " + this.source.notes + " notes" + (this.source.from ? " \u00b7 " + this.source.from : "") : " \u00b7 none";
      if (!has) tc = THEME.error;
    }
    label(g, text.toUpperCase(), { x: M.pad + 2, y: sec.y, w: width - 2 * M.pad, h: sec.h - 4 }, "left", tc, THEME.smallSize, THEME.bold);
  }
  if (p.repeat) button(g, p.repeat, "repeat", false, this.hot(p.repeat));
  if (p.write) button(g, p.write, "write", false, this.hot(p.write));
  if (p.capture) button(g, p.capture, "capture", false, this.hot(p.capture));
  if (p.mode) button(g, p.mode, "destructive", this.sourceMode === "destructive", this.hot(p.mode));
  if (p.within) button(g, p.within, "process sel.", this.withinSelection, this.hot(p.within));
  if (p.only) button(g, p.only, "dump sel.", this.selectionOnly, this.hot(p.only));
  if (p.reset) button(g, p.reset, "reset", false, this.hot(p.reset));
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
    var st = this.snapState(row.item);
    if (st && row.snapToggle) button(g, row.snapToggle, st[1], st[2] > 0, this.hot(row.snapToggle));
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
  if (p.within && inside(p.within, x, y)) {
    this.withinSelection = !this.withinSelection;
    return [["process_only_selection", this.withinSelection ? 1 : 0]];
  }
  if (p.only && inside(p.only, x, y)) {
    this.selectionOnly = !this.selectionOnly;
    return [["dump_selection_only", this.selectionOnly ? 1 : 0]];
  }
  if (p.mode && inside(p.mode, x, y)) {
    this.sourceMode = this.sourceMode === "destructive" ? "nondestructive" : "destructive";
    return [["source_mode", this.sourceMode === "destructive" ? 0 : 1]];
  }
  if (p.snap && inside(p.snap, x, y)) {
    this.snap = !this.snap;
    return [];
  }
  if (p.reset && inside(p.reset, x, y)) return this.resetAll();
  if (p.bypass && inside(p.bypass, x, y)) {
    this.bypass = !this.bypass;
    return [["bypass", this.bypass ? 1 : 0]];
  }
  if (p.repeat && inside(p.repeat, x, y)) return [["repeat"]];
  for (var k = 0; k < this.rows.length; k++) {
    if (this.rows[k].snapToggle && inside(this.rows[k].snapToggle, x, y)) return this.nextSnap(this.rows[k].item);
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
  row.item.snapping = this.snapping(row.item) !== Boolean(mods.alt);
  return row.item.down(row.control, x, y, mods) ? [this.message(row.item)] : [];
};

Panel.prototype.mouseDrag = function (x, y, mods) {
  var row = this.active;
  if (!row) return [];
  mods = mods || {};
  row.item.snapping = this.snapping(row.item) !== Boolean(mods.alt);
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
      kind: it.kind, grid: it.baseGrid !== undefined ? it.baseGrid : it.grid, display: it.display });
  }
  return { title: this.title, path: this.path, kind: this.kind, source: this.source, params: params, snap: this.snap,
    sourceMode: this.sourceMode, involutive: this.involutive, selectionOnly: this.selectionOnly,
    bypass: this.bypass, withinSelection: this.withinSelection, pitchSnap: this.pitchSnap, timeSnap: this.timeSnap };
};

Panel.prototype.restore = function (snapshot) {
  this.setSpec({ title: snapshot.title, path: snapshot.path, kind: snapshot.kind, params: [] });
  this.sourceMode = snapshot.sourceMode === "destructive" ? "destructive" : "nondestructive";
  this.involutive = snapshot.involutive === true;
  this.selectionOnly = snapshot.selectionOnly !== false;
  this.bypass = snapshot.bypass === true;
  this.withinSelection = snapshot.withinSelection === true;
  this.pitchSnap = [0, 1, 3].indexOf(snapshot.pitchSnap) < 0 ? 3 : snapshot.pitchSnap;
  this.timeSnap = [0, 1, 2].indexOf(snapshot.timeSnap) < 0 ? 0 : snapshot.timeSnap;
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
