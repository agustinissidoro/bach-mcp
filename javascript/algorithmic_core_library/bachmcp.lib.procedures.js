/*
bachmcp.lib.procedures.js
-------------------------
Processes that unfold step by step: iteration, random walks, Markov chains,
L-systems, cellular automata, Euclidean rhythms.
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

const { AlgoError } = need("bachmcp.lib.base.js");
const { makeRandom } = need("bachmcp.lib.random.js");
const { clamp, fold, seq } = need("bachmcp.lib.numbers.js");

/** [x0, f(x0, 1), f(f(x0, 1), 2), ...], n values: a state that evolves step by step. */
function iterate(n, x0, f) {
  const out = [];
  let x = x0;
  for (let i = 0; i < n; i++) {
    out.push(x);
    x = f(x, i + 1);
  }
  return out;
}

/** A random walk of n values: each step moves by up to ±step, reflected inside [min, max]. */
function walk({ n, start, step, min, max, rng }) {
  const r = rng || makeRandom("walk");
  return iterate(n, clamp(start, min, max), (x) => fold(x + r.float(-step, step), min, max));
}

/**
 * A Markov chain of n states from `start`. table: {state: {next: weight, ...}} or
 * {state: [next, ...]} (equal weights). Stops early at a state with no way out.
 */
function markov(table, { n, start, rng }) {
  const r = rng || makeRandom("markov");
  const asValue = (key) => (key !== "" && !Number.isNaN(Number(key)) ? Number(key) : key);
  const out = [];
  let state = start;
  for (let i = 0; i < n; i++) {
    out.push(state);
    const options = table[state];
    if (!options) break;
    if (Array.isArray(options)) {
      if (!options.length) break;
      state = r.pick(options);
    } else {
      const keys = Object.keys(options);
      if (!keys.length) break;
      state = asValue(r.weighted(keys, keys.map((k) => options[k])));
    }
  }
  return out;
}

/** An L-system: rewrite every symbol of the axiom by its rule, `generations` times. Returns text. */
function rewrite(axiom, rules, generations) {
  let text = String(axiom);
  for (let g = 0; g < generations; g++) {
    let next = "";
    for (const ch of text) next += Object.prototype.hasOwnProperty.call(rules, ch) ? rules[ch] : ch;
    text = next;
    if (text.length > 100000) throw new AlgoError("rewrite() grew past 100000 symbols: use fewer generations");
  }
  return text;
}

/**
 * An elementary cellular automaton (rule 0-255). cells: the first row as 0/1 values,
 * or a width (one live cell in the middle). Returns `steps` rows, the first included.
 */
function automaton(rule, cells, steps) {
  let row = Array.isArray(cells) ? cells.map((c) => (c ? 1 : 0)) : seq(cells).map((i) => (i === Math.floor(cells / 2) ? 1 : 0));
  const rows = [];
  for (let s = 0; s < steps; s++) {
    rows.push(row);
    const w = row.length;
    row = row.map((_, i) => (rule >> ((row[(i - 1 + w) % w] << 2) | (row[i] << 1) | row[(i + 1) % w])) & 1);
  }
  return rows;
}

/** A Euclidean rhythm: `hits` onsets spread as evenly as possible over `steps`, as 1/0. */
function euclid(hits, steps, rotate = 0) {
  return seq(steps).map((i) => ((((i + rotate) * hits) % steps + steps) % steps < hits ? 1 : 0));
}

module.exports = { iterate, walk, markov, rewrite, automaton, euclid };
