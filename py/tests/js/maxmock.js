/*
A small stand-in for Max's JavaScript environment, enough to run the bach.mcp
scripts (v8 and jsui) in Node: outlets, post, Dict, Task, File, messagename,
mgraphics and box. Tasks run only when the test calls flush().
*/
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const JS_DIR = path.join(__dirname, "..", "..", "..", "max", "bach-mcp", "javascript");

const dicts = new Map();
let dictCounter = 0;

class Dict {
  constructor(name) {
    this.name = name || `u${++dictCounter}`;
    if (!dicts.has(this.name)) dicts.set(this.name, {});
  }
  parse(text) {
    dicts.set(this.name, JSON.parse(text));
  }
  stringify() {
    return JSON.stringify(dicts.get(this.name));
  }
  clear() {
    dicts.set(this.name, {});
  }
}

function makeFileClass() {
  return class File {
    constructor(file) {
      try {
        this.bytes = Array.from(fs.readFileSync(file));
        this.isopen = true;
      } catch (e) {
        this.bytes = [];
        this.isopen = false;
      }
      this.position = 0;
      this.eof = this.bytes.length;
    }
    readbytes(n) {
      const out = this.bytes.slice(this.position, this.position + n);
      this.position += out.length;
      return out;
    }
    close() {
      this.isopen = false;
    }
  };
}

function makeMgraphics(width, height) {
  const calls = [];
  const g = {
    size: [width, height],
    calls,
    redraws: 0,
    init() {},
    redraw() {
      g.redraws += 1;
    },
    text_measure(text) {
      return [String(text).length * 6, 12];
    },
  };
  for (const name of ["set_source_rgba", "rectangle", "rectangle_rounded", "fill", "fill_preserve", "stroke",
    "move_to", "line_to", "arc", "close_path", "set_line_width", "select_font_face", "set_font_size", "show_text"]) {
    g[name] = (...args) => {
      for (const a of args) {
        if (typeof a === "number" && !Number.isFinite(a)) throw new Error(`${name} got ${a}`);
      }
      calls.push([name, ...args]);
    };
  }
  return g;
}

/**
 * require() as jsui's legacy engine does it: the module sees `exports` but no `module`.
 * Scripts for jsui (bach.mcp.params.js) are loaded with this one.
 */
function legacyRequire(name) {
  const file = path.join(JS_DIR, path.basename(name));
  const exports = {};
  const ctx = { exports, post() {} };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(file, "utf8"), ctx, { filename: path.basename(name) });
  return exports;
}

/**
 * Load a Max script. Returns {ctx, out, posts, send, flush, embedded}.
 * out: every outlet call as [index, ...atoms]. send(selector, ...args) delivers a message.
 */
function load(script, options = {}) {
  const out = [];
  const posts = [];
  const embedded = [];
  const tasks = [];
  const ctx = {
    autowatch: 0, inlets: 1, outlets: 1, messagename: "", jsarguments: [script],
    box: { rect: [0, 0, options.width || 300, options.height || 100] },
    console,
    post: (...a) => posts.push(a.join(" ")),
    error: (...a) => posts.push("error: " + a.join(" ")),
    outlet: (i, ...a) => out.push([i, ...(a.length === 1 && Array.isArray(a[0]) ? a[0] : a)]),
    setinletassist() {},
    setoutletassist() {},
    embedmessage: (...a) => embedded.push(a),
    arrayfromargs: (args) => Array.prototype.slice.call(args),
    Dict,
    File: makeFileClass(),
    Task: class Task {
      constructor(fn) {
        this.fn = fn;
        this.interval = 0;
        this.state = "idle";
        tasks.push(this);
      }
      schedule() {
        this.state = "once";
      }
      repeat() {
        this.state = "repeat";
      }
      cancel() {
        this.state = "idle";
      }
    },
    require: options.legacy ? legacyRequire : (name) => require(path.join(JS_DIR, path.basename(name))),
    mgraphics: makeMgraphics(options.width || 300, options.height || 100),
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(JS_DIR, script), "utf8"), ctx, { filename: script });

  function send(selector, ...args) {
    ctx.messagename = selector;
    const fn = ctx[selector];
    if (typeof fn === "function" && !fn.local && !["anything"].includes(selector)) return fn(...args);
    if (typeof ctx.anything === "function") return ctx.anything(...args);
    throw new Error(`no handler for ${selector}`);
  }

  /** Run the tasks that are due: scheduled ones once; repeating ones once per call when repeat is true. */
  function flush(repeat = false) {
    for (const t of tasks) {
      if (t.state === "once") {
        t.state = "idle";
        t.fn();
      } else if (repeat && t.state === "repeat") {
        t.fn();
      }
    }
  }

  return { ctx, out, posts, embedded, send, flush, dicts };
}

function readDict(name) {
  return dicts.get(name);
}

module.exports = { load, readDict, legacyRequire, JS_DIR, Dict };
