/*
bachmcp.gui.params.base.js
--------------------------
What every part of the parameter panel leans on: the theme and the sizes, numbers
(snapping, formatting, pitch names) and the drawing helpers over mgraphics.

Written in ECMAScript 5, because jsui runs Max's legacy JavaScript engine (it
also runs unchanged in v8ui and in Node, where the tests draw it on a mock).
jsui's require gives a module only `exports`, so every name leaves through it.
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

var SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

/** The name of a pitch in midicents: nearest semitone with sharps, then the cents: 6050 -> "C4+50". */
function centsToName(cents) {
  cents = tidy(cents);
  var semitone = Math.ceil((cents - 50) / 100);
  var offset = tidy(cents - semitone * 100);
  var text = SHARP_NAMES[((semitone % 12) + 12) % 12] + (Math.floor(semitone / 12) - 1);
  if (offset) text += (offset > 0 ? "+" : "-") + formatNumber(Math.abs(offset), 0.01);
  return text;
}

// How each kind of number can be shown; the first is the default.
var DISPLAYS = { pitch: ["name", "mc", "midi"], interval: ["cents", "semitones"] };

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

exports.THEME = THEME;
exports.M = M;
exports.clamp = clamp;
exports.tidy = tidy;
exports.snap = snap;
exports.formatNumber = formatNumber;
exports.SHARP_NAMES = SHARP_NAMES;
exports.centsToName = centsToName;
exports.DISPLAYS = DISPLAYS;
exports.copy = copy;
exports.same = same;
exports.inside = inside;
exports.color = color;
exports.box = box;
exports.rounded = rounded;
exports.dot = dot;
exports.fit = fit;
exports.label = label;
