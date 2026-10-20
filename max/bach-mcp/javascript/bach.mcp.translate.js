/*
bach.mcp.translate.js — JSON score <-> bach.roll (v8). Lives inside the
bach.mcp.translate abstraction, whose attributes set the direction:

  @in json   accepts  dictionary <name>  (or  json <text>)
  @in bach   accepts  a bach.roll llll in text form: roll [...] [...], or a dump
             through [bach.portal @out t]
  @out bach  sends    the messages for bach.roll: tonedivision, then roll (or addchords with @add 1)
  @out json  sends    dictionary <name>

Defaults: @in json @out bach.
*/
"use strict";

autowatch = 1;
inlets = 1;
outlets = 1;

const S = (function () {
  try {
    return require("bach.mcp.score.js");
  } catch (e) {
    return require("./bach.mcp.score.js");
  }
})();

const mode = { in: "json", out: "bach" };
let addMode = false;
const outDict = new Dict();

try {
  setinletassist(0, "@in json: dictionary <name>   @in bach: roll [...] llll");
  setoutletassist(0, "@out bach: messages for bach.roll   @out json: dictionary <name>");
} catch (e) {
  // assist strings are optional
}

function fail(message) {
  post(`bach.mcp.translate: error: ${message}\n`);
}

function dictionary(name) {
  if (mode.in !== "json") return fail("received a dictionary but @in is bach; set @in json");
  let score;
  try {
    score = JSON.parse(new Dict(String(name)).stringify());
  } catch (e) {
    return fail(`cannot read dictionary ${name}`);
  }
  fromJson(score);
}

function json(...parts) {
  if (mode.in !== "json") return fail("received json but @in is bach; set @in json");
  let score;
  try {
    score = JSON.parse(parts.join(" "));
  } catch (e) {
    return fail(`not valid JSON: ${e.message}`);
  }
  fromJson(score);
}

function list(...atoms) {
  fromBach(atoms);
}

function done() {
  // end of patcherargs' attribute list
}

function anything(...args) {
  const selector = messagename;
  if (selector === "in" || selector === "out") {
    const value = String(args[0]);
    if (value !== "json" && value !== "bach") return fail(`@${selector} must be json or bach`);
    mode[selector] = value;
  } else if (selector === "add") {
    addMode = Boolean(Number(args[0]));
  } else if (selector === "bach.llll") {
    fail("received a native llll: put [bach.portal @out t] between bach.roll and bach.mcp.translate");
  } else {
    fromBach([selector].concat(args));
  }
}

function fromBach(atoms) {
  if (mode.in !== "bach") return fail("received an llll but @in is json; set @in bach");
  let score;
  try {
    score = S.llllToScore(atoms);
  } catch (e) {
    return fail(`cannot read the llll: ${e.message}`);
  }
  output(score);
}

function fromJson(score) {
  output(score);
}

function output(score) {
  let canonical;
  try {
    canonical = S.normalizeScore(score);
  } catch (e) {
    return fail(e.message);
  }
  if (mode.out === "json") {
    outDict.clear();
    outDict.parse(JSON.stringify(score));
    outlet(0, "dictionary", outDict.name);
    return;
  }
  for (const message of S.scoreMessagesChunked(canonical, addMode)) {
    outlet(0, S.toAtoms(message));
  }
}
