/*
bachmcp.lib.numbers.js
----------------------
Numbers and shapes: interpolation, ranges, sequences, breakpoint functions.
*/
"use strict";

const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const rescale = (x, inLo, inHi, outLo, outHi) =>
  inHi === inLo ? outLo : outLo + ((x - inLo) * (outHi - outLo)) / (inHi - inLo);

function wrap(x, lo, hi) {
  const span = hi - lo;
  return span <= 0 ? lo : lo + ((((x - lo) % span) + span) % span);
}

/** Reflect x back into [lo, hi], like a ball between two walls. */
function fold(x, lo, hi) {
  const span = hi - lo;
  if (span <= 0) return lo;
  const t = wrap(x - lo, 0, 2 * span);
  return lo + (t > span ? 2 * span - t : t);
}

/** The nearest multiple of grid (plus offset). */
const snap = (x, grid, offset = 0) => (grid > 0 ? offset + Math.round((x - offset) / grid) * grid : x);

/** [start, start + step, ...], n values. */
function seq(n, start = 0, step = 1) {
  return Array.from({ length: Math.max(0, Math.floor(n)) }, (_, i) => start + i * step);
}

/** n values from a to b, both included. */
function linspace(a, b, n) {
  n = Math.max(0, Math.floor(n));
  if (n === 1) return [a];
  return Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1));
}

const sum = (list) => list.reduce((a, b) => a + b, 0);

/** Running starts from a list of durations: [start, start + d0, start + d0 + d1, ...]. */
function accumulate(durations, start = 0) {
  const out = [];
  let t = start;
  for (const d of durations) {
    out.push(t);
    t += d;
  }
  return out;
}

/** A breakpoint function: env([[x, y], ...])(x), linear between points, flat outside. */
function env(points) {
  const pts = points.map((p) => [Number(p[0]), Number(p[1])]).sort((a, b) => a[0] - b[0]);
  const f = (x) => {
    if (!pts.length) return 0;
    if (x <= pts[0][0]) return pts[0][1];
    for (let i = 1; i < pts.length; i++) {
      if (x <= pts[i][0]) {
        const [x0, y0] = pts[i - 1];
        const [x1, y1] = pts[i];
        return x1 === x0 ? y1 : y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
      }
    }
    return pts[pts.length - 1][1];
  };
  f.points = pts;
  return f;
}

/** Bend t in 0..1: k = 0 straight, k > 0 starts slow (exponential), k < 0 starts fast. */
function warp(t, k) {
  if (!k) return t;
  return (Math.exp(k * t) - 1) / (Math.exp(k) - 1);
}

module.exports = { lerp, clamp, rescale, wrap, fold, snap, seq, linspace, sum, accumulate, env, warp };
