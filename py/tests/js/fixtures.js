// Shared by the tests of the algorithmic core library: the library itself, and a small piece of music.
"use strict";

const path = require("path");
const { JS_DIR } = require("./maxmock.js");

const LIB_DIR = path.join(JS_DIR, "algorithmic_core_library");
const lib = require(path.join(LIB_DIR, "bachmcp.lib.index.js"));
const loader = require(path.join(JS_DIR, "runners", "bachmcp.runner.loader.js"));
const paramspec = require(path.join(JS_DIR, "runners", "bachmcp.runner.paramspec.js"));

const n = (pitch, dur = 250, vel = 80) => ({ pitch, dur, vel });
const c = (onset, ...notes) => ({ onset, notes });

// Two voices: a rising phrase, a silence, the same phrase a fourth higher and faster, then something else.
function piece() {
  return {
    voices: [
      { name: "Flute", chords: [
        c(0, n(6000)), c(250, n(6200)), c(500, n(6400)), c(750, n(6700, 500)),
        c(2000, n(6500, 125)), c(2125, n(6700, 125)), c(2250, n(6900, 125)), c(2375, n(7200, 250)),
        c(4000, n(7900, 1000)), c(5000, n(7100, 1000)),
      ] },
      { name: "Cello", chords: [c(0, n(3600, 1250), n(4300, 1250)), c(2000, n(4100, 625))] },
    ],
    markers: [{ onset: 0, name: "A" }, { onset: 4000, name: "B" }],
  };
}

module.exports = { lib, loader, paramspec, LIB_DIR, n, c, piece };
