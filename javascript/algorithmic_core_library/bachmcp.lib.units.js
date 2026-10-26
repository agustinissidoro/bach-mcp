/*
bachmcp.lib.units.js
--------------------
The units of the score, and pitch names: pitch("Db4") = 6100, name(6100) = "C#4".
Pitches are in midicents (100 to a semitone, 6000 = middle C), times in milliseconds.
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

const SEMITONE = 100;
const QUARTERTONE = 50;
const OCTAVE = 1200;
const MIDDLE_C = 6000;
const SECOND = 1000;

// Not in an algorithm's scope (see bachmcp.lib.index.js): for the loader and the parameters.
const MIN_CENTS = 1200;   // C0: anything lower is a mistake, usually pitch and duration swapped
const MAX_CENTS = 12700;  // G9
const MAX_NOTES = 20000;  // the most notes a run may make: more would flood Max

/** A number without a trailing ".0", at most three decimals: 6000, 0.5, 33.333. */
function fmt(x) {
  if (Number.isInteger(x)) return String(x === 0 ? 0 : x);
  const s = x.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  return s === "-0" ? "0" : s;
}

function tidy(x, digits = 3) {
  const r = Number(Number(x).toFixed(digits));
  return r === 0 ? 0 : r;
}

// A pitch name: letter, accidental, octave (C4 = middle C = 6000), optional cent offset.
const NOTE_NAME = /^([A-G])(##|bb|#|b|x)?(-?\d+)(?:([+-]\d+(?:\.\d+)?)c?)?$/;
const NAME_CLASS = { C: 0, D: 200, E: 400, F: 500, G: 700, A: 900, B: 1100 };
const NAME_ACCIDENTAL = { "#": 100, b: -100, "##": 200, x: 200, bb: -200 };
const SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

/** Midicents of a pitch name such as "Db4", "F#5", "E4-14" or "C4+50" (C4 = middle C = 6000), or null. */
function nameToCents(text) {
  const m = NOTE_NAME.exec(String(text).trim());
  if (!m) return null;
  const [, letter, accidental, octave, offset] = m;
  return (parseInt(octave, 10) + 1) * 1200 + NAME_CLASS[letter] + (accidental ? NAME_ACCIDENTAL[accidental] : 0) +
    (offset ? parseFloat(offset) : 0);
}

/** The name of a pitch in midicents: nearest semitone with sharps, then the offset (-50, +50]. */
function centsToName(cents) {
  cents = tidy(cents);
  const semitone = Math.ceil((cents - 50) / 100);
  const offset = tidy(cents - semitone * 100);
  let name = `${SHARP_NAMES[((semitone % 12) + 12) % 12]}${Math.floor(semitone / 12) - 1}`;
  if (offset) name += `${offset > 0 ? "+" : "-"}${fmt(Math.abs(offset))}`;
  return name;
}

/** Midicents of a pitch name: pitch("Db4") = 6100, pitch("E4-14") = 6386 (C4 = middle C = 6000). */
function pitch(text) {
  const cents = nameToCents(text);
  if (cents === null) throw new AlgoError(`pitch(${JSON.stringify(text)}): a name is a letter, # or b, an octave, e.g. "Db4"; cents after it: "E4-14"`);
  return cents;
}

/** The name of a pitch in midicents: name(6100) = "C#4", name(6050) = "C4+50". */
function name(cents) {
  return centsToName(cents);
}

module.exports = {
  SEMITONE, QUARTERTONE, OCTAVE, MIDDLE_C, SECOND, pitch, name,
  MIN_CENTS, MAX_CENTS, MAX_NOTES, fmt, nameToCents, centsToName,
};
