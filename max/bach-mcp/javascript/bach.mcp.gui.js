/*
bach.mcp.gui.js
---------------
The GUI elements of bach.mcp.params: one element per parameter type, and the
Panel that lays them out, draws them with mgraphics and turns mouse gestures
into "<param> <value...>" messages for bach.mcp.algo.

Written in ECMAScript 5, because jsui runs Max's legacy JavaScript engine (it
also runs unchanged in v8ui and in Node, where the tests draw it on a mock).

A parameter arrives as the runner describes it:
  { name: "times", type: "slider", range: [1, 64], step: 1, unit: "", value: 16, default: 16 }
Types: slider, range, toggle, menu, seed, curve, list. Placement is automatic:
one row per parameter, curve and list get a drawing area below their name.
*/
"use strict";

var THEME = {
  bg: [0.14, 0.14, 0.15, 1],
  row: [0.19, 0.19, 0.2, 1],
  track: [0.28, 0.28, 0.3, 1],
  fill: [0.96, 0.63, 0.24, 1],
  fillDim: [0.96, 0.63, 0.24, 0.28],
  knob: [1, 0.86, 0.66, 1],
  text: [0.9, 0.9, 0.9, 1],
  dim: [0.58, 0.58, 0.6, 1],
  ok: [0.5, 0.8, 0.5, 1],
  error: [0.96, 0.4, 0.34, 1],
  font: "Arial",
  fontSize: 11,
  titleSize: 12
};

var M = {
  pad: 6,
  row: 20,
  gap: 3,
  title: 22,
  status: 18,
  valueMin: 36,
  valueMax: 120,
  charWidth: 6.4,
  labelMin: 54,
  labelMax: 132,
  curve: 76,
  list: 58,
  grab: 7
};

// ── Numbers ─────────────────────────────────────────────────────────────── //

function clamp(x, lo, hi) {
  return Math.min(hi, Math.max(lo, x));
}

function tidy(x) {
  return Number(Number(x).toFixed(6));
}

function snap(spec, x) {
  var lo = spec.range[0], hi = spec.range[1];
  x = clamp(x, lo, hi);
  if (spec.step > 0) x = clamp(lo + Math.round((x - lo) / spec.step) * spec.step, lo, hi);
  return tidy(x);
}

function formatNumber(x, step) {
  if (step >= 1 || Math.round(x) === x) return String(Math.round(x));
  var digits = step > 0 ? Math.min(4, Math.max(0, Math.ceil(-Math.log(step) / Math.LN10))) : 3;
  var s = x.toFixed(digits);
  if (s.indexOf(".") >= 0) s = s.replace(/0+$/, "").replace(/\.$/, "");
  return s;
}

function copy(x) {
  return x === undefined ? undefined : JSON.parse(JSON.stringify(x));
}

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function inside(r, x, y) {
  return x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
}

// ── Drawing helpers ─────────────────────────────────────────────────────── //

function color(g, c) {
  g.set_source_rgba(c[0], c[1], c[2], c[3]);
}

function box(g, x, y, w, h, c) {
  color(g, c);
  g.rectangle(x, y, Math.max(0, w), Math.max(0, h));
  g.fill();
}

function rounded(g, x, y, w, h, radius, c) {
  color(g, c);
  g.rectangle_rounded(x, y, Math.max(0, w), Math.max(0, h), radius, radius);
  g.fill();
}

function dot(g, x, y, radius, c) {
  color(g, c);
  g.arc(x, y, radius, 0, 2 * Math.PI);
  g.fill();
}

function fit(g, text, width) {
  text = String(text);
  if (width <= 0) return "";
  if (g.text_measure(text)[0] <= width) return text;
  while (text.length > 1 && g.text_measure(text + "…")[0] > width) text = text.slice(0, -1);
  return text + "…";
}

// Text in a box: align "left", "right" or "center", vertically centred.
function label(g, text, r, align, c, size) {
  size = size || THEME.fontSize;
  g.select_font_face(THEME.font);
  g.set_font_size(size);
  var shown = fit(g, text, r.w);
  var w = g.text_measure(shown)[0];
  var x = align === "right" ? r.x + r.w - w : (align === "center" ? r.x + (r.w - w) / 2 : r.x);
  color(g, c);
  g.move_to(x, r.y + (r.h + size * 0.72) / 2);
  g.show_text(shown);
}

// ── Elements ────────────────────────────────────────────────────────────── //

function Element(spec) {
  this.name = spec.name;
  this.type = spec.type;
  this.range = spec.range ? spec.range.slice() : null;
  this.step = spec.step || 0;
  this.unit = spec.unit || "";
  this.options = spec.options ? spec.options.slice() : null;
  this.value = copy(spec.value);
  this.def = copy(spec["default"] !== undefined ? spec["default"] : spec.value);
  this.tall = false;
  this.grab = null;
}

Element.prototype.atoms = function () {
  return [].concat(this.value);
};

// A value from atoms ("set" messages, pattr), clamped to this element. Returns false if unusable.
Element.prototype.accept = function (atoms) {
  var n = Number(atoms[0]);
  if (isNaN(n)) return false;
  this.value = snap(this, n);
  return true;
};

Element.prototype.text = function () {
  return formatNumber(this.value, this.step) + (this.unit ? " " + this.unit : "");
};

// The longest value text this element can show, to size the value column.
Element.prototype.widest = function () {
  var keep = this.value, out = "";
  var probes = this.range ? [this.range[0], this.range[1]] : [];
  if (this.range && this.step < 1) probes.push(this.range[0] + (this.range[1] - this.range[0]) / 3);
  for (var i = 0; i < probes.length; i++) {
    this.value = this.type === "range" ? [probes[i], probes[(i + 1) % probes.length]] : probes[i];
    if (this.text().length > out.length) out = this.text();
  }
  this.value = keep;
  return out || this.text();
};

Element.prototype.fraction = function (v) {
  return (v - this.range[0]) / (this.range[1] - this.range[0]);
};

Element.prototype.at = function (r, x) {
  return this.range[0] + clamp((x - r.x) / r.w, 0, 1) * (this.range[1] - this.range[0]);
};

Element.prototype.down = function () {
  return false;
};

Element.prototype.drag = function () {
  return false;
};

Element.prototype.reset = function () {
  this.value = copy(this.def);
};

Element.prototype.paintTrack = function (g, r, from, to) {
  var y = r.y + r.h / 2 - 3;
  rounded(g, r.x, y, r.w, 6, 3, THEME.track);
  rounded(g, r.x + from * r.w, y, (to - from) * r.w, 6, 3, THEME.fill);
};

// slider: one number in a range
function Slider(spec) {
  Element.call(this, spec);
}
Slider.prototype = Object.create(Element.prototype);

Slider.prototype.down = function (r, x, y, mods) {
  this.grab = { x: x, value: this.value };
  return this.drag(r, x, y, mods);
};

Slider.prototype.drag = function (r, x, y, mods) {
  var v = mods && mods.shift && this.grab
    ? this.grab.value + ((x - this.grab.x) / r.w) * (this.range[1] - this.range[0]) / 10
    : this.at(r, x);
  var old = this.value;
  this.value = snap(this, v);
  return this.value !== old;
};

Slider.prototype.paint = function (g, r) {
  var f = clamp(this.fraction(this.value), 0, 1);
  this.paintTrack(g, r, 0, f);
  dot(g, r.x + f * r.w, r.y + r.h / 2, 5, THEME.knob);
};

// range: two numbers, low and high
function Range(spec) {
  Element.call(this, spec);
}
Range.prototype = Object.create(Element.prototype);

Range.prototype.accept = function (atoms) {
  var a = Number(atoms[0]), b = Number(atoms[1]);
  if (isNaN(a) || isNaN(b)) return false;
  this.value = [snap(this, Math.min(a, b)), snap(this, Math.max(a, b))];
  return true;
};

Range.prototype.text = function () {
  return formatNumber(this.value[0], this.step) + "–" + formatNumber(this.value[1], this.step) +
    (this.unit ? " " + this.unit : "");
};

Range.prototype.down = function (r, x) {
  var x0 = r.x + this.fraction(this.value[0]) * r.w;
  var x1 = r.x + this.fraction(this.value[1]) * r.w;
  if (x > x0 + M.grab && x < x1 - M.grab) this.grab = { which: "both", x: x, value: this.value.slice() };
  else this.grab = { which: Math.abs(x - x0) <= Math.abs(x - x1) ? 0 : 1 };
  if (this.grab.which === 0 && x0 === x1 && x > x1) this.grab.which = 1;
  return this.drag(r, x);
};

Range.prototype.drag = function (r, x) {
  var old = this.value.slice();
  if (!this.grab) return false;
  if (this.grab.which === "both") {
    var span = this.range[1] - this.range[0];
    var d = ((x - this.grab.x) / r.w) * span;
    d = clamp(d, this.range[0] - this.grab.value[0], this.range[1] - this.grab.value[1]);
    this.value = [snap(this, this.grab.value[0] + d), snap(this, this.grab.value[1] + d)];
  } else {
    var v = snap(this, this.at(r, x));
    if (this.grab.which === 0) this.value = [Math.min(v, this.value[1]), this.value[1]];
    else this.value = [this.value[0], Math.max(v, this.value[0])];
  }
  return !same(old, this.value);
};

Range.prototype.paint = function (g, r) {
  var a = clamp(this.fraction(this.value[0]), 0, 1);
  var b = clamp(this.fraction(this.value[1]), 0, 1);
  this.paintTrack(g, r, a, b);
  dot(g, r.x + a * r.w, r.y + r.h / 2, 5, THEME.knob);
  dot(g, r.x + b * r.w, r.y + r.h / 2, 5, THEME.knob);
};

// toggle: on or off
function Toggle(spec) {
  Element.call(this, spec);
  this.value = Boolean(this.value);
  this.def = Boolean(this.def);
}
Toggle.prototype = Object.create(Element.prototype);

Toggle.prototype.atoms = function () {
  return [this.value ? 1 : 0];
};

Toggle.prototype.accept = function (atoms) {
  var a = atoms[0];
  this.value = a === "true" || a === "on" || (Number(a) !== 0 && !isNaN(Number(a)));
  return true;
};

Toggle.prototype.text = function () {
  return this.value ? "on" : "off";
};

Toggle.prototype.down = function () {
  this.value = !this.value;
  return true;
};

Toggle.prototype.paint = function (g, r) {
  var s = Math.min(14, r.h - 4);
  var y = r.y + (r.h - s) / 2;
  rounded(g, r.x, y, s, s, 3, this.value ? THEME.fill : THEME.track);
  if (this.value) rounded(g, r.x + 4, y + 4, s - 8, s - 8, 2, THEME.bg);
};

// menu: one of a list of options (segments, or a stepper when they do not fit)
function Menu(spec) {
  Element.call(this, spec);
}
Menu.prototype = Object.create(Element.prototype);

Menu.prototype.index = function () {
  for (var i = 0; i < this.options.length; i++) if (String(this.options[i]) === String(this.value)) return i;
  return 0;
};

Menu.prototype.accept = function (atoms) {
  for (var i = 0; i < this.options.length; i++) {
    if (String(this.options[i]) === String(atoms[0])) {
      this.value = this.options[i];
      return true;
    }
  }
  var n = Number(atoms[0]);
  if (n === Math.floor(n) && n >= 0 && n < this.options.length) {
    this.value = this.options[n];
    return true;
  }
  return false;
};

Menu.prototype.text = function () {
  return "";
};

Menu.prototype.segmented = function (r) {
  return r.w / this.options.length >= 34;
};

Menu.prototype.down = function (r, x) {
  var old = this.value;
  var i = this.index();
  if (this.segmented(r)) i = clamp(Math.floor(((x - r.x) / r.w) * this.options.length), 0, this.options.length - 1);
  else i = (i + (x < r.x + r.w / 2 ? this.options.length - 1 : 1)) % this.options.length;
  this.value = this.options[i];
  return this.value !== old;
};

Menu.prototype.paint = function (g, r) {
  var i = this.index();
  rounded(g, r.x, r.y + 2, r.w, r.h - 4, 3, THEME.track);
  if (this.segmented(r)) {
    var w = r.w / this.options.length;
    rounded(g, r.x + i * w, r.y + 2, w, r.h - 4, 3, THEME.fill);
    for (var k = 0; k < this.options.length; k++) {
      label(g, this.options[k], { x: r.x + k * w + 3, y: r.y, w: w - 6, h: r.h }, "center", k === i ? THEME.bg : THEME.text);
    }
  } else {
    label(g, "‹", { x: r.x + 4, y: r.y, w: 10, h: r.h }, "left", THEME.dim);
    label(g, "›", { x: r.x + r.w - 14, y: r.y, w: 10, h: r.h }, "right", THEME.dim);
    label(g, this.value, { x: r.x + 16, y: r.y, w: r.w - 32, h: r.h }, "center", THEME.text);
  }
};

// seed: an integer, dragged like a number box; the square on the right draws a new one
function Seed(spec) {
  Element.call(this, spec);
  if (!this.range) this.range = [0, 9999];
  this.step = 1;
}
Seed.prototype = Object.create(Element.prototype);

Seed.prototype.dice = function (r) {
  return { x: r.x + r.w - r.h, y: r.y, w: r.h, h: r.h };
};

Seed.prototype.down = function (r, x, y) {
  if (inside(this.dice(r), x, y)) {
    var old = this.value;
    while (this.value === old && this.range[1] > this.range[0]) {
      this.value = this.range[0] + Math.floor(Math.random() * (this.range[1] - this.range[0] + 1));
    }
    this.grab = null;
    return true;
  }
  this.grab = { x: x, y: y, value: this.value };
  return false;
};

Seed.prototype.drag = function (r, x, y) {
  if (!this.grab) return false;
  var old = this.value;
  this.value = snap(this, this.grab.value + Math.round((x - this.grab.x) / 4 - (y - this.grab.y) / 4));
  return this.value !== old;
};

Seed.prototype.paint = function (g, r) {
  var d = this.dice(r);
  rounded(g, r.x, r.y + 2, r.w - d.w - 4, r.h - 4, 3, THEME.track);
  label(g, "drag", { x: r.x + 6, y: r.y, w: r.w - d.w - 16, h: r.h }, "left", THEME.dim);
  rounded(g, d.x + 2, d.y + 2, d.w - 4, d.h - 4, 3, THEME.fill);
  dot(g, d.x + d.w / 2 - 3, d.y + d.h / 2 - 3, 1.6, THEME.bg);
  dot(g, d.x + d.w / 2 + 3, d.y + d.h / 2 + 3, 1.6, THEME.bg);
};

// curve: breakpoints [[x, y], ...], x from 0 to 1; click adds a point, shift-click removes one
function Curve(spec) {
  Element.call(this, spec);
  this.tall = M.curve;
}
Curve.prototype = Object.create(Element.prototype);

Curve.prototype.atoms = function () {
  var out = [];
  for (var i = 0; i < this.value.length; i++) out.push(this.value[i][0], this.value[i][1]);
  return out;
};

Curve.prototype.accept = function (atoms) {
  if (atoms.length < 4 || atoms.length % 2) return false;
  var pts = [];
  for (var i = 0; i < atoms.length; i += 2) {
    var x = Number(atoms[i]), y = Number(atoms[i + 1]);
    if (isNaN(x) || isNaN(y)) return false;
    pts.push([tidy(clamp(x, 0, 1)), snap(this, y)]);
  }
  pts.sort(function (a, b) { return a[0] - b[0]; });
  pts[0][0] = 0;
  pts[pts.length - 1][0] = 1;
  this.value = pts;
  return true;
};

Curve.prototype.text = function () {
  return this.value.length + " points";
};

Curve.prototype.toPixel = function (r, p) {
  return [r.x + p[0] * r.w, r.y + r.h - this.fraction(p[1]) * r.h];
};

Curve.prototype.fromPixel = function (r, x, y) {
  var fy = clamp((r.y + r.h - y) / r.h, 0, 1);
  return [tidy(clamp((x - r.x) / r.w, 0, 1)), snap(this, this.range[0] + fy * (this.range[1] - this.range[0]))];
};

Curve.prototype.down = function (r, x, y, mods) {
  var best = -1, bestD = M.grab;
  for (var i = 0; i < this.value.length; i++) {
    var p = this.toPixel(r, this.value[i]);
    var d = Math.sqrt((p[0] - x) * (p[0] - x) + (p[1] - y) * (p[1] - y));
    if (d <= bestD) {
      best = i;
      bestD = d;
    }
  }
  if (best >= 0 && mods && mods.shift) {
    this.grab = null;
    if (best > 0 && best < this.value.length - 1) {
      this.value.splice(best, 1);
      return true;
    }
    return false;
  }
  if (best < 0) {
    if (this.value.length >= 64) return false;
    var q = this.fromPixel(r, x, y);
    best = 0;
    while (best < this.value.length && this.value[best][0] <= q[0]) best++;
    if (best === 0) best = 1;
    if (best >= this.value.length) best = this.value.length - 1;
    this.value.splice(best, 0, q);
  }
  this.grab = { index: best };
  this.drag(r, x, y);
  return true;
};

Curve.prototype.drag = function (r, x, y) {
  if (!this.grab) return false;
  var i = this.grab.index, pts = this.value;
  var q = this.fromPixel(r, x, y);
  var old = copy(pts[i]);
  if (i === 0) q[0] = 0;
  else if (i === pts.length - 1) q[0] = 1;
  else q[0] = clamp(q[0], pts[i - 1][0], pts[i + 1][0]);
  pts[i] = q;
  return !same(old, q);
};

Curve.prototype.paint = function (g, r) {
  box(g, r.x, r.y, r.w, r.h, THEME.row);
  var i, p;
  color(g, THEME.fillDim);
  g.move_to(r.x, r.y + r.h);
  for (i = 0; i < this.value.length; i++) {
    p = this.toPixel(r, this.value[i]);
    g.line_to(p[0], p[1]);
  }
  g.line_to(r.x + r.w, r.y + r.h);
  g.close_path();
  g.fill();
  color(g, THEME.fill);
  g.set_line_width(1.5);
  for (i = 0; i < this.value.length; i++) {
    p = this.toPixel(r, this.value[i]);
    if (i === 0) g.move_to(p[0], p[1]);
    else g.line_to(p[0], p[1]);
  }
  g.stroke();
  for (i = 0; i < this.value.length; i++) {
    p = this.toPixel(r, this.value[i]);
    dot(g, p[0], p[1], 3.5, THEME.knob);
  }
  label(g, formatNumber(this.range[1], this.step), { x: r.x + 3, y: r.y, w: 60, h: 12 }, "left", THEME.dim, 9);
  label(g, formatNumber(this.range[0], this.step), { x: r.x + 3, y: r.y + r.h - 12, w: 60, h: 12 }, "left", THEME.dim, 9);
};

// list: several numbers, drawn as bars; drag across them to draw
function List(spec) {
  Element.call(this, spec);
  this.tall = M.list;
}
List.prototype = Object.create(Element.prototype);

List.prototype.accept = function (atoms) {
  var out = [];
  for (var i = 0; i < atoms.length && i < 256; i++) {
    var n = Number(atoms[i]);
    if (isNaN(n)) return false;
    out.push(snap(this, n));
  }
  if (!out.length) return false;
  this.value = out;
  return true;
};

List.prototype.text = function () {
  var shown = [];
  for (var i = 0; i < this.value.length && i < 6; i++) shown.push(formatNumber(this.value[i], this.step));
  return shown.join(" ") + (this.value.length > 6 ? " …" : "");
};

List.prototype.indexAt = function (r, x) {
  return clamp(Math.floor(((x - r.x) / r.w) * this.value.length), 0, this.value.length - 1);
};

List.prototype.valueAt = function (r, y) {
  return snap(this, this.range[0] + clamp((r.y + r.h - y) / r.h, 0, 1) * (this.range[1] - this.range[0]));
};

List.prototype.down = function (r, x, y) {
  this.grab = { index: this.indexAt(r, x) };
  var i = this.grab.index, old = this.value[i];
  this.value[i] = this.valueAt(r, y);
  return this.value[i] !== old;
};

List.prototype.drag = function (r, x, y) {
  if (!this.grab) return false;
  var i = this.indexAt(r, x), v = this.valueAt(r, y), changed = false;
  var from = this.grab.index, step = i >= from ? 1 : -1;
  for (var k = from; k !== i + step; k += step) {
    if (this.value[k] !== v) {
      this.value[k] = v;
      changed = true;
    }
  }
  this.grab.index = i;
  return changed;
};

List.prototype.paint = function (g, r) {
  box(g, r.x, r.y, r.w, r.h, THEME.row);
  var n = this.value.length, w = r.w / n;
  var base = clamp(this.fraction(0), 0, 1);
  var y0 = r.y + r.h - base * r.h;
  for (var i = 0; i < n; i++) {
    var y = r.y + r.h - clamp(this.fraction(this.value[i]), 0, 1) * r.h;
    box(g, r.x + i * w + 1, Math.min(y, y0), Math.max(1, w - 2), Math.max(1.5, Math.abs(y0 - y)), THEME.fill);
  }
};

var TYPES = { slider: Slider, range: Range, toggle: Toggle, menu: Menu, seed: Seed, curve: Curve, list: List };

function makeElement(spec) {
  var Kind = TYPES[spec.type];
  if (!Kind) throw new Error("unknown parameter type " + spec.type);
  return new Kind(spec);
}

// ── Panel ───────────────────────────────────────────────────────────────── //

function Panel() {
  this.clear();
}

Panel.prototype.clear = function () {
  this.title = "";
  this.path = "";
  this.items = [];
  this.rows = [];
  this.state = { kind: "", text: "" };
  this.width = 0;
  this.active = null;
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
  this.items = [];
  var messages = [];
  var params = spec.params || [];
  for (i = 0; i < params.length; i++) {
    var item = makeElement(params[i]);
    var was = old[item.name];
    if (was && was.type === item.type) {
      var before = item.atoms();
      if (item.accept(was.atoms()) && !same(before, item.atoms())) messages.push([item.name].concat(item.atoms()));
    }
    this.items.push(item);
  }
  this.active = null;
  this.width = 0;
  return messages;
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
  label(g, this.title || "bach.mcp.params", { x: M.pad + 4, y: 0, w: width - 2 * M.pad - 8, h: M.title },
    "left", this.title ? THEME.text : THEME.dim, THEME.titleSize);
  if (!this.items.length) {
    label(g, this.title ? "no parameters" : "waiting for bach.mcp.algo", { x: M.pad + 4, y: M.title, w: width - 2 * M.pad, h: M.row },
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
  var row = this.rowAt(x, y);
  this.active = row;
  if (!row) return [];
  return row.item.down(row.control, x, y, mods || {}) ? [this.message(row.item)] : [];
};

Panel.prototype.mouseDrag = function (x, y, mods) {
  var row = this.active;
  if (!row) return [];
  return row.item.drag(row.control, x, y, mods || {}) ? [this.message(row.item)] : [];
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
      options: it.options, value: copy(it.value), "default": copy(it.def) });
  }
  return { title: this.title, path: this.path, params: params };
};

Panel.prototype.restore = function (snapshot) {
  this.setSpec({ title: snapshot.title, path: snapshot.path, params: [] });
  this.setSpec(snapshot);
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

// jsui's legacy require gives a module only `exports`; Node and v8 also have `module`.
var api = {
  THEME: THEME,
  METRICS: M,
  Panel: Panel,
  makeElement: makeElement,
  formatNumber: formatNumber,
  snap: snap
};
if (typeof module !== "undefined" && module.exports) {
  module.exports = api;
} else if (typeof exports !== "undefined") {
  for (var key in api) exports[key] = api[key];
}
