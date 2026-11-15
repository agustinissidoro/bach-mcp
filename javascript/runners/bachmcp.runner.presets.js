/*
bachmcp.runner.presets.js
-------------------------
An algorithm's presets: kept in its own file, after the code, as one declaration
the runner writes and rewrites (the panel stores them; the model never does):

    // Presets: stored from the panel (preset <n> save). Not part of the algorithm.
    const presets = {
      "1": { "times": 4, "mode": "up" },
      "3": { "times": 12, "mode": "down" }
    };

Slots are 1 to 10; values are by parameter name, as the algorithm sees
them (a curve as its points), so that a preset never lands on another
parameter. A new version of the file without the block has no presets.

    normalize(raw)           what the file declares -> {slot: {name: value}} (bad entries dropped)
    slots(presets)           the stored slots, sorted
    withPresets(code, p)     the file's text with this block in place of the old one (or appended,
                             or removed when there is nothing to keep)
*/
"use strict";

const COMMENT = "// Presets: stored from the panel (preset <n> save). Not part of the algorithm.";
const MAX_SLOT = 10;

function isPlainObject(x) {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

/** {slot: {name: value}} from what the file declares: slots 1..MAX_SLOT, each an object; anything else dropped. */
function normalize(raw) {
  const out = {};
  if (!isPlainObject(raw)) return out;
  for (const key of Object.keys(raw)) {
    const n = Number(key);
    if (!(Number.isInteger(n) && n >= 1 && n <= MAX_SLOT) || !isPlainObject(raw[key])) continue;
    out[n] = JSON.parse(JSON.stringify(raw[key]));
  }
  return out;
}

function slots(presets) {
  return Object.keys(presets || {}).map(Number).sort((a, b) => a - b);
}

/** The declaration, one slot per line. */
function format(presets) {
  const lines = slots(presets).map((n) => `  "${n}": ${JSON.stringify(presets[n])}`);
  return `${COMMENT}\nconst presets = {\n${lines.join(",\n")}\n};\n`;
}

/**
 * Where `const presets = {...};` is in the code: [start, end) of the declaration (with the
 * comment line above it when it is ours), or null. Strings and comments inside are skipped
 * when matching the braces.
 */
function findBlock(code) {
  const m = /^[ \t]*(?:const|let|var)[ \t]+presets[ \t]*=[ \t]*\{/m.exec(code);
  if (!m) return null;
  let i = m.index + m[0].length;
  let depth = 1;
  while (i < code.length && depth > 0) {
    const c = code[i];
    if (c === '"' || c === "'" || c === "`") {
      for (i++; i < code.length && code[i] !== c; i++) if (code[i] === "\\") i++;
    } else if (c === "/" && code[i + 1] === "/") {
      while (i < code.length && code[i] !== "\n") i++;
    } else if (c === "/" && code[i + 1] === "*") {
      i = code.indexOf("*/", i + 2);
      if (i < 0) return null;
      i++;
    } else if (c === "{") {
      depth++;
    } else if (c === "}") {
      depth--;
    }
    i++;
  }
  if (depth > 0) return null;
  let end = i;
  while (end < code.length && (code[end] === " " || code[end] === "\t")) end++;
  if (code[end] === ";") end++;
  if (code[end] === "\n") end++;
  let start = m.index;
  const before = code.slice(0, start);
  if (before.endsWith(COMMENT + "\n")) start -= COMMENT.length + 1;
  return [start, end];
}

/** The code with these presets: the block replaced, appended at the end, or taken out when empty. */
function withPresets(code, presets) {
  const text = String(code);
  const block = slots(presets).length ? format(presets) : "";
  const at = findBlock(text);
  if (at) return text.slice(0, at[0]) + block + text.slice(at[1]);
  if (!block) return text;
  return text.replace(/\s*$/, "\n") + "\n" + block;
}

module.exports = { normalize, slots, withPresets, MAX_SLOT };
