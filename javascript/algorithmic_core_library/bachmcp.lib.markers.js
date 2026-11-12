/*
bachmcp.lib.markers.js
----------------------
Markers with a role: the measures of a score still written in milliseconds.
bach.quantize (measureinfo "auto") reads them to turn a bach.roll into measured
notation. They live in the score's header, in bachjson-complete:

    header.markers: [{onset, name: [], role, content?}, ...]

`x` is a score: one being built (score()), or a source. Every function writes
into x.header.markers, kept in time order, and returns x (grid returns where it ended).

    timesig(x, onset, [4, 4])        a time signature; it is also the barline of the measure it opens
    barline(x, onset)                a barline (not where a timesig already is)
    division(x, onset)               a beat inside a measure (not the first: that is the barline)
    subdivision(x, onset)            a unit inside a beat (not the first), for 2+2+3/8 and the like
    tempo(x, onset, value, figure)   a tempo, figure "1/4" by default
    grid(x, {start, timesig, bar, count, beats})
                                     `count` equal measures of `bar` ms from `start`, with their closing
                                     barline; returns its onset. beats: mark each beat (default false;
                                     a nested numerator [[2, 2, 3], 8] always marks its groups and units)
    markersOf(x, role)               the markers, in time order (of one role, when given)
    clearGrid(x)                     removes every marker that has a role; named markers stay

One marker of a kind at one time: writing it again replaces it. A timesig takes
the place of a barline at the same onset, and a barline is not written where a
timesig is: bach would read two measures there.
*/
"use strict";

// Max finds a file by its name, on the search path; Node by where it is.
function need(name) {
  const places = ["", "./", "../", "../algorithmic_core_library/", "../runners/"];
  for (const place of places) {
    try {
      return require(place + name);
    } catch (e) {
      if (place === places[places.length - 1]) throw e;
    }
  }
}

const { AlgoError, isObject } = need("bachmcp.lib.base.js");

const ROLES = ["none", "tempo", "timesig", "barline", "division", "subdivision"];
// At one onset: the tempo first (bach wants it before its barline), then what opens the measure.
const ORDER = { tempo: 0, timesig: 1, barline: 1, division: 2, subdivision: 3, none: 4 };
const OPENS = (role) => role === "timesig" || role === "barline";

function isNumber(x) {
  return typeof x === "number" && Number.isFinite(x);
}

function list(x, what) {
  if (!isObject(x)) throw new AlgoError(`${what}: the first argument is the score (score(), or the source)`);
  if (!isObject(x.header)) x.header = {};
  if (!Array.isArray(x.header.markers)) x.header.markers = [];
  return x.header.markers;
}

function rank(m) {
  return ORDER[m.role] === undefined ? ORDER.none : ORDER[m.role];
}

function sort(markers) {
  const placed = markers.map((m, i) => [m, i]);
  placed.sort((a, b) => a[0].onset - b[0].onset || rank(a[0]) - rank(b[0]) || a[1] - b[1]);
  markers.splice(0, markers.length, ...placed.map((x) => x[0]));
}

/** A marker of this role at this onset, in place of the one already there. */
function put(x, what, onset, role, content, name) {
  const markers = list(x, what);
  if (!isNumber(onset)) throw new AlgoError(`${what}: onset must be a number of milliseconds, got ${JSON.stringify(onset)}`);
  const same = (m) => m.onset === onset && (m.role === role || (OPENS(role) && OPENS(m.role)));
  if (role === "barline" && markers.some((m) => m.onset === onset && m.role === "timesig")) return x;
  for (let i = markers.length - 1; i >= 0; i--) if (same(markers[i])) markers.splice(i, 1);
  const marker = { onset, name: name === undefined || name === "" ? [] : [].concat(name), role };
  if (content) marker.content = content;
  markers.push(marker);
  sort(markers);
  return x;
}

function checkTimesig(ts, what) {
  const ok = Array.isArray(ts) && ts.length === 2 && Number.isInteger(ts[1]) && ts[1] > 0 && (ts[1] & (ts[1] - 1)) === 0
    && (Array.isArray(ts[0]) ? ts[0].length > 0 && ts[0].every((n) => Number.isInteger(n) && n > 0) : Number.isInteger(ts[0]) && ts[0] > 0);
  if (!ok) throw new AlgoError(`${what}: a time signature is [numerator, denominator], e.g. [3, 4] or [[2, 2, 3], 8], got ${JSON.stringify(ts)}`);
  return JSON.parse(JSON.stringify(ts));
}

function timesig(x, onset, ts, name) {
  return put(x, "timesig", onset, "timesig", checkTimesig(ts, "timesig"), name);
}

function barline(x, onset, name) {
  return put(x, "barline", onset, "barline", null, name);
}

function division(x, onset, name) {
  return put(x, "division", onset, "division", null, name);
}

function subdivision(x, onset, name) {
  return put(x, "subdivision", onset, "subdivision", null, name);
}

function tempo(x, onset, value, figure = "1/4", name) {
  if (!isNumber(value) || value <= 0) throw new AlgoError(`tempo: the value must be a number above 0 (beats a minute), got ${JSON.stringify(value)}`);
  if (typeof figure !== "string" || !/^\d+\/\d+$/.test(figure)) throw new AlgoError(`tempo: the figure is a note value as text, e.g. "1/4" or "3/8", got ${JSON.stringify(figure)}`);
  return put(x, "tempo", onset, "tempo", [figure, value], name);
}

/**
 * `count` equal measures of `bar` ms from `start`: the time signature on the first, a barline on
 * each of the others and one that closes the last. Returns the onset of that closing barline.
 */
function grid(x, { start = 0, timesig: ts = [4, 4], bar, count = 1, beats = false } = {}) {
  ts = checkTimesig(ts, "grid");
  if (!isNumber(start)) throw new AlgoError("grid: start must be a number of milliseconds");
  if (!isNumber(bar) || bar <= 0) throw new AlgoError(`grid: bar is how long one measure lasts, in milliseconds (above 0), got ${JSON.stringify(bar)}`);
  if (!Number.isInteger(count) || count < 1) throw new AlgoError(`grid: count is a whole number of measures (1 or more), got ${JSON.stringify(count)}`);
  const groups = Array.isArray(ts[0]) ? ts[0] : null;
  const units = groups ? groups.reduce((a, b) => a + b, 0) : ts[0];
  for (let i = 0; i < count; i++) {
    const at = start + i * bar;
    if (i === 0) timesig(x, at, ts);
    else barline(x, at);
    if (groups) {  // each group a beat, each unit inside it a subdivision
      let unit = 0;
      groups.forEach((size) => {
        for (let k = 0; k < size; k++, unit++) {
          if (unit === 0) continue;
          (k === 0 ? division : subdivision)(x, at + (unit * bar) / units);
        }
      });
    } else if (beats) {
      for (let b = 1; b < units; b++) division(x, at + (b * bar) / units);
    }
  }
  const end = start + count * bar;
  barline(x, end);
  return end;
}

function markersOf(x, role) {
  const markers = isObject(x) && isObject(x.header) && Array.isArray(x.header.markers) ? x.header.markers.slice() : [];
  sort(markers);
  return role === undefined ? markers : markers.filter((m) => m.role === role);
}

function clearGrid(x) {
  const markers = list(x, "clearGrid");
  for (let i = markers.length - 1; i >= 0; i--) if (markers[i].role && markers[i].role !== "none") markers.splice(i, 1);
  return x;
}

module.exports = { timesig, barline, division, subdivision, tempo, grid, markersOf, clearGrid, ROLES };
