/*
bachmcp.gui.params.panel.js
---------------------------
The Panel: a title row (the algorithm, its type, bypass and "set active": the
instance Claude's tools work for, sent as "set_as_active_instance"), under it the
algorithm's one-line description when its file has one (the spec's description:
the // comment that opens the file), then two sections.
Left of the type, one animated icon follows the instance's prompt (setPrompt).
Drags land on each slider's grid; alt lets one through. "Options": reset
all; then bypass ("bypass 0|1"), repeat ("repeat"); pitch cards toggle ½ | ¼ | free ("snap 0|1|3"), time cards 100ms | 10ms | free; a transformer adds its source card: how many notes, write
(write_to_playground), capture and the source mode as two
segments, non-destructive (the source is held; every output starts again from
it) or destructive (every score at the runner's inlet becomes the source), sent
as "source_mode 1|0". A selector has the same card, and under the mode
two more segments, whole score | selection only (sent as "dump_selection_only 0|1"). "Parameters": one card each, its name and value above its
control. A status line closes the panel.

Size: a bigger panel draws its parameters bigger (layout: the scale grows with
the width past M.baseWidth, up to M.maxScale, as long as the height still holds
it), and height left over goes to lists and curves (up to M.tallGrow times taller).
The rest (title row, buttons, section headers, status line) grows only
M.chromeGrow as much: the parameters are what a bigger panel is for.
Bigger controls are more precise: the elements mark finer steps and show free
values to the pixel (see bachmcp.gui.params.elements.js).

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
  scaled = base.scaled,
  scaleFor = base.scaleFor,
  clamp = base.clamp,
  copy = base.copy,
  same = base.same,
  inside = base.inside,
  box = base.box,
  rounded = base.rounded,
  label = base.label,
  outline = base.outline,
  dot = base.dot,
  color = base.color;
var makeElement = elements.makeElement;

// The algorithm's type (the spec's type), as the runner says it.
var TYPES = { generator: true, transformer: true, selector: true };
// Panels saved before the spec said type: their kind.
var TYPE_OF_KIND = { producer: "generator", transformer: "transformer", selector: "selector" };

function Panel() {
  this.name = "";  // set_name: shown while no algorithm is loaded; kept by clear
  this.type = "";  // set_type: the base layout while no algorithm is loaded; kept by clear
  this.prompt = { stage: "", detail: "", at: 0 };  // the prompt's progress (setPrompt); kept by clear
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
  this.description = "";  // one line on what the algorithm does: the comment that opens its file
  this.path = "";
  // this.source = null;  // transformers: {notes, from}. Commented out for now: the panel does not show the source
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

/**
 * set_type generator|transformer|selector: the panel of that type, before any algorithm
 * (its title row, output and, for a transformer or a selector, its source row).
 * Returns null for an unknown type, else whether anything changed.
 */
Panel.prototype.setType = function (type) {
  var t = String(type);
  if (!TYPES[t]) return null;
  if (t === this.type) return false;
  this.type = t;
  this.places = null;
  this.width = 0;
  return true;
};

/** Transformers and selectors work on a source: they have the source card. */
Panel.prototype.hasSource = function () {
  return this.type === "transformer" || this.type === "selector";
};

/**
 * Show a new set of parameters (a file loaded, saved while watched, or the patch
 * reopened). A value the user set here (it differs from the old default) is kept
 * when the parameter still means the same: same name, type, kind and unit;
 * clamped to the new range, a menu's only if its option is still there (by name,
 * never by position). Everything else shows the spec's value, so a default edited
 * in the file shows at once. Returns the messages to send for the values kept.
 */
Panel.prototype.setSpec = function (spec) {
  var old = {}, i;
  for (i = 0; i < this.items.length; i++) old[this.items[i].name] = this.items[i];
  this.title = spec.title || "";
  var type = spec.type || TYPE_OF_KIND[spec.kind];
  if (TYPES[type]) this.type = type;
  this.setDescription(spec.description);
  this.path = spec.path || "";
  // this.source = spec.source || null;  // commented out for now: the panel does not show the source
  this.items = [];
  var messages = [];
  var params = spec.params || [];
  for (i = 0; i < params.length; i++) {
    var item = makeElement(params[i]);
    var was = old[item.name];
    if (was && was.type === item.type && was.kind === item.kind && was.unit === item.unit) {
      if (params[i].display === undefined) item.display = was.display;
      if (keeps(was, item)) {
        var before = item.atoms();
        if (item.accept(was.atoms()) && !same(before, item.atoms())) messages.push(this.message(item));
      }
    }
    this.items.push(item);
  }
  this.applyGrids();
  this.active = null;
  this.width = 0;
  this.places = null;
  // the runner starts nondestructive: tell it the mode this panel is in
  if (this.hasSource() && this.sourceMode !== "nondestructive") messages.push(["source_mode", 0]);
  if (this.type === "selector" && !this.selectionOnly) messages.push(["dump_selection_only", 0]);
  if (this.bypass) messages.push(["bypass", 1]);
  if (this.hasSource() && this.withinSelection) messages.push(["process_only_selection", 1]);
  if (this.pitchSnap !== 3) messages.push(["snap", this.pitchSnap]);
  return messages;
};

/** Whether a value set by the user carries over to the new declaration (see setSpec). */
function keeps(was, item) {
  if (same(was.value, was.def)) return false;
  if (item.type !== "menu") return true;
  for (var i = 0; i < item.options.length; i++) if (String(item.options[i]) === String(was.value)) return true;
  return false;
}

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
 * 10 ms, free. Free is free: no grid at all, every pixel a value (alt then
 * snaps to the card's own grid).
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
    if (st) it.grid = st[2];
  }
};

/** Whether a drag of this item snaps (before alt): on its toggle's step, never when free; else the panel's snap. */
Panel.prototype.snapping = function (item) {
  var st = this.snapState(item);
  return st ? st[2] > 0 : this.snap;
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

/** The algorithm's one-line description; "" removes it. True when it changes. */
Panel.prototype.setDescription = function (text) {
  var next = text === undefined || text === null ? "" : String(text).replace(/\s+/g, " ").trim();
  if (next === this.description) return false;
  this.description = next;
  this.places = null;
  return true;
};

/** The height of the description line under the title row (0 without one). */
Panel.prototype.descriptionHeight = function () {
  var k = this.k || M;
  return this.description ? k.row + 2 * (this.chrome || 1) : 0;
};

// ── The prompt's progress ───────────────────────────────────────────────── //
// The server's "prompt <instance> <stage> [detail]" (bachmcp.server's prompt info) as one
// animated icon in the title row: received, queued <ahead>, starting, sent, thinking,
// writing, calling <tool>, running <tool>, then done <tokens> <ms>, stopped or error <text>.
// done and stopped fade out; error stays until the next prompt.

var PROMPT_FADE = 4000;  // ms that done and stopped stay

/** A stage of the prompt ("" or "idle": no icon). True when the drawing changes. */
Panel.prototype.setPrompt = function (stage, detail) {
  var next = stage === undefined || stage === null ? "" : String(stage);
  if (next === "idle") next = "";
  var text = detail === undefined || detail === null ? "" : String(detail);
  if (next === this.prompt.stage && text === this.prompt.detail) return false;
  this.prompt = { stage: next, detail: text, at: this.clock() };
  return true;
};

Panel.prototype.clock = function () {
  return new Date().getTime();
};

/** Whether the icon is shown at all. */
Panel.prototype.promptShown = function () {
  var s = this.prompt.stage;
  if (!s) return false;
  if (s === "done" || s === "stopped") return this.clock() - this.prompt.at < PROMPT_FADE;
  return true;
};

/** Whether the icon still moves (the drawing needs redraws): everything but error and no icon. */
Panel.prototype.promptMoving = function () {
  return this.promptShown() && this.prompt.stage !== "error";
};

function strokeArc(g, x, y, r, a0, a1, c, width) {
  color(g, c);
  g.set_line_width(width);
  g.arc(x, y, r, a0, a1);
  g.stroke();
}

function fade(c, alpha) {
  return [c[0], c[1], c[2], c[3] * alpha];
}

// The icon centred on (x, y), radius r, t ms after the stage began.
function promptIcon(g, stage, x, y, r, t) {
  var s = t / 1000, TAU = 2 * Math.PI;
  var pulse = 0.5 + 0.5 * Math.sin(s * TAU / 1.2);
  var spin = function (turnsPerSecond, c, length) {
    var a = s * turnsPerSecond * TAU;
    strokeArc(g, x, y, r, 0, TAU, fade(c, 0.18), 1.5);
    strokeArc(g, x, y, r, a, a + length, c, 1.5);
  };
  if (stage === "received" || stage === "queued") {
    // waiting its turn: a ring that breathes (slower while queued)
    var slow = stage === "queued" ? 0.5 + 0.5 * Math.sin(s * TAU / 2.4) : pulse;
    strokeArc(g, x, y, r, 0, TAU, fade(THEME.dim, 0.35 + 0.65 * slow), 1.5);
  } else if (stage === "starting" || stage === "sent") {
    spin(0.8, THEME.dim, 1.6);
  } else if (stage === "thinking") {
    // a dot that swells inside a faint ring
    strokeArc(g, x, y, r, 0, TAU, fade(THEME.fill, 0.25), 1.5);
    dot(g, x, y, r * (0.3 + 0.4 * pulse), fade(THEME.fill, 0.55 + 0.45 * pulse));
  } else if (stage === "writing") {
    spin(1.6, THEME.fill, 2.2);
  } else if (stage === "calling" || stage === "running") {
    spin(1.1, THEME.ok, 1.8);
    dot(g, x, y, 1.6, THEME.ok);
  } else if (stage === "done" || stage === "stopped") {
    var left = 1 - Math.min(1, Math.max(0, (t - PROMPT_FADE / 2) / (PROMPT_FADE / 2)));
    if (stage === "done") {
      color(g, fade(THEME.ok, left));
      g.set_line_width(1.8);
      g.move_to(x - r * 0.6, y + r * 0.05);
      g.line_to(x - r * 0.15, y + r * 0.5);
      g.line_to(x + r * 0.7, y - r * 0.5);
      g.stroke();
    } else {
      box(g, x - r * 0.55, y - r * 0.55, r * 1.1, r * 1.1, fade(THEME.dim, left));
    }
  } else if (stage === "error") {
    color(g, THEME.error);
    g.set_line_width(1.8);
    g.move_to(x - r * 0.55, y - r * 0.55);
    g.line_to(x + r * 0.55, y + r * 0.55);
    g.move_to(x + r * 0.55, y - r * 0.55);
    g.line_to(x - r * 0.55, y + r * 0.55);
    g.stroke();
  } else {
    spin(0.8, THEME.dim, 1.6);  // a stage this panel does not know: busy all the same
  }
  g.set_line_width(1);
}

Panel.prototype.setStatus = function (kind, text) {
  this.state = { kind: String(kind || ""), text: String(text || "") };
};

/* Commented out for now: the panel does not show the source.
// A transformer's source score: how many notes, and where it was taken from.
Panel.prototype.setSource = function (notes, from) {
  this.source = { notes: Number(notes) || 0, from: String(from || "") };
};
*/

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

Panel.prototype.valueWidth = function () {
  var longest = 0;
  for (var i = 0; i < this.items.length; i++) longest = Math.max(longest, this.items[i].widest().length);
  var m = this.m || M;
  return clamp(Math.ceil(longest * m.charWidth) + 12 * (this.scale || 1), m.valueMin, m.valueMax);
};

/**
 * Place everything for this width (and height, when known); returns the height
 * the panel needs. Title row: the algorithm, its type, the bypass toggle and
 * "set active" (always: to make this instance the one Claude works on again, or
 * the one it starts on before it has an algorithm).
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
  var s = scaleFor(width);
  if (!(height > 0)) {
    this.compact = false;
    return this.place(width, false, s, 0);
  }
  // the height holds the panel at scale 1: grow as far as the width allows and the height holds
  var natural = this.place(width, false, 1, 0);
  if (natural > height + 0.5) {
    this.compact = true;
    return this.place(width, true, 1, 0);
  }
  this.compact = false;
  // the largest scale the width allows that the height still holds, in steps of 0.05
  var used = this.place(width, false, s, 0);
  while (used > height + 0.5 && s > 1) used = this.place(width, false, s = Math.max(1, Math.round((s - 0.05) * 20) / 20), 0);
  // what is left: to the lists and curves
  return height - used > 1 && this.hasTall() ? this.place(width, false, s, height - used) : used;
};

Panel.prototype.hasTall = function () {
  for (var i = 0; i < this.items.length; i++) if (this.items[i].tall) return true;
  return false;
};

/** Place everything at scale s; extra: height to share among the lists and curves. */
Panel.prototype.place = function (width, compact, s, extra) {
  s = s || 1;
  var c = 1 + (s - 1) * M.chromeGrow;  // the title row, buttons, headers, status: they grow less
  var m = scaled(s), u = function (n) { return n * s; };
  var k = scaled(c), v = function (n) { return n * c; };
  this.scale = s;
  this.chrome = c;
  this.m = m;
  this.k = k;
  this.width = width;
  this.rows = [];
  var p = { setActive: null, within: null, bypass: null, repeat: null, write: null, capture: null, mode: null, only: null,
    snap: null, reset: null, sections: [] };
  this.places = p;
  var inner = width - 2 * m.pad;
  var section = compact ? v(14) : k.section;
  var y = k.title + this.descriptionHeight() + k.gap;
  p.setActive = { x: width - k.pad - v(62), y: (k.title - k.button) / 2, w: v(62), h: k.button };
  if (!this.items.length && !this.title && !this.type) return y + k.row + k.status;
  p.bypass = { x: p.setActive.x - v(4) - v(56), y: (k.title - k.button) / 2, w: v(56), h: k.button };
  // output
  p.sections.push({ text: "output", y: y, h: section });
  y += section;
  p.repeat = { x: k.pad, y: y, w: v(50), h: k.button };
  p.write = { x: k.pad + v(54), y: y, w: v(44), h: k.button };
  y += k.button + k.gap;
  // source
  if (this.hasSource()) {
    p.sections.push({ text: "source", y: y, h: section, source: true });
    y += section;
    var n = this.type === "selector" ? 4 : 3, gap = v(4), w = (inner - (n - 1) * gap) / n;
    p.capture = { x: m.pad, y: y, w: w, h: k.button };
    p.mode = { x: m.pad + w + gap, y: y, w: w, h: k.button };
    p.within = { x: m.pad + 2 * (w + gap), y: y, w: w, h: k.button };
    if (n === 4) p.only = { x: m.pad + 3 * (w + gap), y: y, w: w, h: k.button };
    y += k.button + k.gap;
  }
  // parameters, reset in the header
  var head = { text: "parameters" + (this.items.length ? " · " + this.items.length : ""), y: y, h: section };
  p.sections.push(head);
  var by = y + (section - v(16)) / 2 - v(1);
  p.reset = { x: width - m.pad - v(44), y: by, w: v(44), h: v(16) };
  y += section + v(2);
  // each element at this scale, and the value one pixel of its control moves (free values)
  var tall = 0, i, item;
  for (i = 0; i < this.items.length; i++) {
    item = this.items[i];
    item.scale = s;
    item.resolution = item.range && !(item.step > 0) ? (item.range[1] - item.range[0]) / Math.max(1, inner - u(16)) : 0;
    if (item.tall) tall++;
  }
  var share = tall && extra > 0 ? extra / tall : 0;
  var vw = this.valueWidth();
  var lw = clamp(Math.round(inner * 0.28), m.labelMin, m.labelMax);
  for (i = 0; i < this.items.length; i++) {
    item = this.items[i];
    var row = { item: item, y: y };
    var ch = item.tall ? u(item.tall) + Math.min(share, u(item.tall) * (M.tallGrow - 1)) : m.row;
    if (compact && !item.tall) {
      row.label = { x: m.pad + u(8), y: y + u(3), w: lw, h: m.row };
      row.value = { x: width - m.pad - u(6) - vw, y: y + u(3), w: vw, h: m.row };
      row.control = { x: row.label.x + lw + u(4), y: y + u(3), w: row.value.x - row.label.x - lw - u(10), h: m.row };
      row.h = m.row + u(6);
    } else {
      row.label = { x: m.pad + u(8), y: y + u(4), w: inner - vw - u(20), h: m.head };
      row.value = { x: width - m.pad - u(8) - vw, y: y + u(4), w: vw, h: m.head };
      row.control = { x: m.pad + u(8), y: y + u(4) + m.head + u(2), w: inner - u(16), h: ch };
      row.h = u(4) + m.head + u(2) + ch + u(6);
    }
    if (snapStates(item)) {
      // the snap toggle, left of the value
      row.snapToggle = { x: row.value.x - u(42), y: row.value.y + (row.value.h - u(16)) / 2, w: u(38), h: u(16) };
      if (compact) row.control.w -= u(42);
      else row.label.w -= u(42);
    }
    this.rows.push(row);
    y += row.h + (compact ? u(2) : m.gap);
  }
  return y + k.status;
};

function button(g, r, text, on, hot, s) {
  s = s || 1;
  rounded(g, r.x, r.y, r.w, r.h, 4 * s, on ? THEME.fill : (hot ? THEME.buttonHover : THEME.button));
  label(g, text, r, "center", on ? THEME.bg : THEME.text, 10 * s);
}

Panel.prototype.hot = function (r) {
  return Boolean(r && this.hover && inside(r, this.hover[0], this.hover[1]));
};

Panel.prototype.paint = function (g, width, height) {
  if (width !== this.width || height !== this.height || !this.places) this.layout(width, height);
  var p = this.places, m = this.m, k = this.k, S = this.scale, C = this.chrome;
  var u = function (n) { return n * S; }, v = function (n) { return n * C; };
  box(g, 0, 0, width, height, THEME.bg);
  // title row
  box(g, 0, 0, width, k.title, THEME.header);
  box(g, 0, k.title - 1, width, 1, THEME.line);
  var kindText = this.title || this.type ? this.type || "generator" : "";
  var titleRight = p.bypass ? p.bypass.x - v(6) : p.setActive ? p.setActive.x - v(6) : width - k.pad;
  if (kindText) {
    var kw = v(kindText.length * 6 + 14);
    var kr = { x: titleRight - kw, y: (k.title - v(16)) / 2, w: kw, h: v(16) };
    rounded(g, kr.x, kr.y, kr.w, kr.h, v(8), THEME.button);
    label(g, kindText, kr, "center", THEME.dim, v(THEME.smallSize));
    titleRight = kr.x - v(6);
  }
  // the prompt's progress: one icon left of the type
  if (this.promptShown()) {
    promptIcon(g, this.prompt.stage, titleRight - v(7), k.title / 2, v(6), this.clock() - this.prompt.at);
    titleRight -= v(20);
  }
  // no algorithm: the instance's name (set_name), if any, over "No algorithm loaded."
  if (this.title || this.name) {
    label(g, this.title || this.name, { x: k.pad + v(2), y: 0, w: titleRight - k.pad - v(2), h: k.title },
      "left", THEME.text, v(THEME.titleSize), THEME.bold);
  }
  if (this.description) {
    label(g, this.description, { x: k.pad + v(2), y: k.title + v(1), w: width - 2 * k.pad - v(4), h: k.row }, "left", THEME.dim, v(11));
  }
  if (!this.items.length && !this.title && !this.type) {
    label(g, "No algorithm loaded.", { x: k.pad + v(2), y: k.title + this.descriptionHeight() + k.gap, w: width - 2 * k.pad, h: k.row },
      "left", THEME.dim, v(THEME.fontSize));
  }
  if (p.bypass) button(g, p.bypass, this.bypass ? "bypassed" : "bypass", this.bypass, this.hot(p.bypass), C);
  if (p.setActive) button(g, p.setActive, "set active", false, this.hot(p.setActive), C);
  for (var q = 0; q < p.sections.length; q++) {
    var sec = p.sections[q];
    var text = sec.text.toUpperCase(), tc = THEME.faint;
    /* Commented out for now: the panel does not show the source.
    if (sec.source) {
      var has = this.source && this.source.notes;
      text += has ? " · " + this.source.notes + " notes" + (this.source.from ? " · " + this.source.from : "") : " · none";
      if (!has) tc = THEME.error;
    }
    */
    label(g, text.toUpperCase(), { x: k.pad + v(2), y: sec.y, w: width - 2 * k.pad, h: sec.h - v(4) }, "left", tc, v(THEME.smallSize), THEME.bold);
  }
  if (p.repeat) button(g, p.repeat, "repeat", false, this.hot(p.repeat), C);
  if (p.write) button(g, p.write, "write", false, this.hot(p.write), C);
  if (p.capture) button(g, p.capture, "capture", false, this.hot(p.capture), C);
  if (p.mode) {
    var destructive = this.sourceMode === "destructive";
    button(g, p.mode, destructive ? "destructive" : "non-destructive", destructive, this.hot(p.mode), C);
  }
  if (p.within) button(g, p.within, "process sel.", this.withinSelection, this.hot(p.within), C);
  if (p.only) button(g, p.only, "dump sel.", this.selectionOnly, this.hot(p.only), C);
  if (p.reset) button(g, p.reset, "reset", false, this.hot(p.reset), C);
  if ((this.title || this.type) && !this.items.length) {
    label(g, this.title ? "no parameters" : "No algorithm loaded.", { x: k.pad + v(2), y: (p.sections.length ? p.sections[p.sections.length - 1].y : k.title) + k.section,
      w: width - 2 * k.pad, h: k.row }, "left", THEME.dim, v(THEME.fontSize));
  }
  for (var i = 0; i < this.rows.length; i++) {
    var row = this.rows[i];
    if (row.y > height) break;
    var active = this.active === row;
    var hovered = this.hover && this.hover[1] >= row.y && this.hover[1] <= row.y + row.h;
    rounded(g, m.pad, row.y, width - 2 * m.pad, row.h, m.radius, active || hovered ? THEME.cardHover : THEME.card);
    if (active) outline(g, m.pad, row.y, width - 2 * m.pad, row.h, m.radius, THEME.fillDim);
    label(g, row.item.name, row.label, "left", THEME.text, u(THEME.fontSize), THEME.bold);
    row.item.paint(g, row.control);
    var st = this.snapState(row.item);
    if (st && row.snapToggle) button(g, row.snapToggle, st[1], st[2] > 0, this.hot(row.snapToggle), S);
    var t = row.item.text();
    if (t) {
      var switchable = row.item.displays().length > 1;
      if (switchable && this.hot(row.value)) rounded(g, row.value.x - u(2), row.value.y, row.value.w + u(4), row.value.h, u(3), THEME.button);
      label(g, t, row.value, "right", switchable ? THEME.knob : THEME.dim, u(THEME.fontSize));
    }
  }
  var s = this.state;
  var sy = height - k.status;
  box(g, 0, sy, width, k.status, THEME.header);
  box(g, 0, sy, width, 1, THEME.line);
  if (s.kind) {
    var sc = s.kind === "error" ? THEME.error : THEME.ok;
    dot(g, k.pad + v(4), sy + k.status / 2, v(3), sc);
    label(g, (s.kind === "ok" ? "" : s.kind + ": ") + s.text, { x: k.pad + v(12), y: sy, w: width - 2 * k.pad - v(12), h: k.status },
      "left", s.kind === "error" ? THEME.error : THEME.dim, v(10));
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
  if (p.setActive && inside(p.setActive, x, y)) return [["set_as_active_instance"]];
  if (p.capture && inside(p.capture, x, y)) return [["capture"]];
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
      if (this.width) this.layout(this.width, this.height);  // the value column may need another width
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
  return { title: this.title, description: this.description, path: this.path, type: this.type, params: params, snap: this.snap,
    sourceMode: this.sourceMode, involutive: this.involutive, selectionOnly: this.selectionOnly,
    bypass: this.bypass, withinSelection: this.withinSelection, pitchSnap: this.pitchSnap, timeSnap: this.timeSnap };
};

Panel.prototype.restore = function (snapshot) {
  this.setSpec({ title: snapshot.title, path: snapshot.path, type: snapshot.type, kind: snapshot.kind, params: [] });
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
