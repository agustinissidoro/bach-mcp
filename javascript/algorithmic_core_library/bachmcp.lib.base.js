/*
bachmcp.lib.base.js
-------------------
What every file of the library leans on: the error an algorithm's author reads,
and two checks. Not in scope in an algorithm file.
*/
"use strict";

class AlgoError extends Error {
  constructor(message, line) {
    super(message);
    this.name = "AlgoError";
    this.line = line || null;
  }
}

function isObject(x) {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

function isNumber(x) {
  return typeof x === "number" && Number.isFinite(x);
}

module.exports = { AlgoError, isObject, isNumber };
