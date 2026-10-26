/*
bachmcp.lib.random.js
---------------------
Seeded randomness, so the same parameters always give the same score. In an
algorithm, rng("pitch") is one stream (r(), r.float, r.int, r.pick, r.weighted,
r.shuffle, r.gauss, r.chance), and Math.random is seeded as well.
*/
"use strict";

function hashString(text) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

/** A random generator (mulberry32) seeded by any number or text. r() is uniform in [0, 1). */
function makeRandom(seed) {
  let state = hashString(String(seed)) || 1;
  const next = () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const r = () => next();
  r.float = (lo = 0, hi = 1) => lo + (hi - lo) * next();
  r.int = (lo, hi) => {
    if (hi === undefined) [lo, hi] = [0, lo];
    lo = Math.ceil(lo);
    hi = Math.floor(hi);
    return lo + Math.floor(next() * (hi - lo + 1));
  };
  r.pick = (list) => list[Math.floor(next() * list.length)];
  r.weighted = (list, weights) => {
    const total = weights.reduce((a, b) => a + Math.max(0, b), 0);
    let x = next() * total;
    for (let i = 0; i < list.length; i++) {
      x -= Math.max(0, weights[i]);
      if (x < 0) return list[i];
    }
    return list[list.length - 1];
  };
  r.shuffle = (list) => {
    const out = list.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  };
  r.gauss = (mean = 0, sd = 1) => {
    const u = 1 - next();
    const v = next();
    return mean + sd * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  r.chance = (p) => next() < p;
  return r;
}

/**
 * The randomness of one run: rng(name) gives one stream per concern, all seeded by
 * state.seed, and Math.random is seeded too. The loader makes one for every run.
 */
function seeded(state) {
  const rng = (name = "main") => {
    const key = String(name);
    if (!state.streams.has(key)) state.streams.set(key, makeRandom(`${state.seed}:${key}`));
    return state.streams.get(key);
  };
  const seededMath = Object.create(Math);
  seededMath.random = () => rng("Math.random")();
  return { rng, Math: seededMath };
}

module.exports = { makeRandom, seeded };
