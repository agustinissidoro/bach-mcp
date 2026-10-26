/*
bachmcp.gui.params.elements.js
------------------------------
One element per parameter type: slider, range, toggle, menu, seed, curve, list.
Each one holds its value, draws itself and turns mouse gestures into a new value;
makeElement(spec) makes the right one for a parameter as the runner describes it:
  { name: "times", type: "slider", range: [1, 64], step: 1, unit: "", value: 16, default: 16 }

The runner also says what a number is (`kind`: pitch, interval, time or plain)
and where a drag snaps to (`grid`): a pitch shows as a name, midicents or MIDI,
an interval as cents or semitones (click the value text to switch).

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
var THEME = base.THEME,
  M = base.M,
  clamp = base.clamp,
  tidy = base.tidy,
  snap = base.snap,
  formatNumber = base.formatNumber,
  centsToName = base.centsToName,
  DISPLAYS = base.DISPLAYS,
  copy = base.copy,
  same = base.same,
  inside = base.inside,
  color = base.color,
  box = base.box,
  rounded = base.rounded,
  dot = base.dot,
  fit = base.fit,
  label = base.label;

function Element(spec) {
  this.name = spec.name;
  this.type = spec.type;
  this.range = spec.range ? spec.range.slice() : null;
  this.step = spec.step || 0;
  this.unit = spec.unit || "";
  this.options = spec.options ? spec.options.slice() : null;
  this.value = copy(spec.value);
  this.def = copy(spec["default"] !== undefined ? spec["default"] : spec.value);
  this.kind = spec.kind || "";
  this.grid = spec.grid || 0;
  var shown = DISPLAYS[this.kind] || [];
  this.display = shown.indexOf(spec.display) >= 0 ? spec.display : (shown[0] || "");
  this.snapping = false;  // set by the panel for each gesture
  this.tall = false;
  this.grab = null;
}

/** The ways this value can be shown (empty: only one). */
Element.prototype.displays = function () {
  return DISPLAYS[this.kind] || [];
};

/** Show the value the next way; false if there is no other way. */
Element.prototype.nextDisplay = function () {
  var shown = this.displays();
  if (shown.length < 2) return false;
  this.display = shown[(shown.indexOf(this.display) + 1) % shown.length];
  return true;
};

/** One number as this element shows it, without the unit. */
Element.prototype.fmt = function (x) {
  if (this.display === "name") return centsToName(x);
  if (this.display === "midi" || this.display === "semitones") {
    var t = formatNumber(x / 100, this.step / 100);
    return this.display === "semitones" && x > 0 ? "+" + t : t;
  }
  if (this.kind === "interval" && x > 0) return "+" + formatNumber(x, this.step);
  return formatNumber(x, this.step);
};

/** What follows the numbers: the unit, or what the display is. */
Element.prototype.suffix = function () {
  if (this.display === "name") return "";
  if (this.display === "midi") return " midi";
  if (this.display === "semitones") return " st";
  return this.unit ? " " + this.unit : "";
};

/** A value from a gesture: on the grid while snapping (the ends of the range stay reachable). */
Element.prototype.gesture = function (x) {
  var lo = this.range[0], hi = this.range[1];
  if (!this.snapping || !(this.grid > 0) || x <= lo || x >= hi) return snap(this, x);
  return snap(this, Math.round(x / this.grid) * this.grid);
};

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
  return this.fmt(this.value) + this.suffix();
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
  this.value = this.gesture(v);
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
  return this.fmt(this.value[0]) + "–" + this.fmt(this.value[1]) + this.suffix();
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
    if (this.snapping && this.grid > 0) d = Math.round(d / this.grid) * this.grid;
    d = clamp(d, this.range[0] - this.grab.value[0], this.range[1] - this.grab.value[1]);
    this.value = [snap(this, this.grab.value[0] + d), snap(this, this.grab.value[1] + d)];
  } else {
    var v = this.gesture(this.at(r, x));
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
  return [tidy(clamp((x - r.x) / r.w, 0, 1)), this.gesture(this.range[0] + fy * (this.range[1] - this.range[0]))];
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
  rounded(g, r.x, r.y, r.w, r.h, 4, THEME.well);
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
  label(g, this.fmt(this.range[1]), { x: r.x + 3, y: r.y, w: 60, h: 12 }, "left", THEME.dim, 9);
  label(g, this.fmt(this.range[0]), { x: r.x + 3, y: r.y + r.h - 12, w: 60, h: 12 }, "left", THEME.dim, 9);
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
  for (var i = 0; i < this.value.length && i < 6; i++) shown.push(this.fmt(this.value[i]));
  return shown.join(" ") + (this.value.length > 6 ? " …" : "") + this.suffix();
};

List.prototype.indexAt = function (r, x) {
  return clamp(Math.floor(((x - r.x) / r.w) * this.value.length), 0, this.value.length - 1);
};

List.prototype.valueAt = function (r, y) {
  return this.gesture(this.range[0] + clamp((r.y + r.h - y) / r.h, 0, 1) * (this.range[1] - this.range[0]));
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
  rounded(g, r.x, r.y, r.w, r.h, 4, THEME.well);
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

exports.Element = Element;
exports.makeElement = makeElement;
exports.TYPES = TYPES;
