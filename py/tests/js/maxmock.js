/*
A small stand-in for Max's JavaScript environment, enough to run the bach.mcp
scripts (v8 and jsui) in Node: outlets, post, Dict, Task, File, messagename,
messnamed, mgraphics and box. Tasks run only when the test calls flush().
*/
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const JS_DIR = path.join(__dirname, "..", "..", "..", "max", "bach-mcp", "javascript");

/** A file found by its name, as Max's search path finds it: in the javascript folder or a folder inside it. */
function onSearchPath(name) {
  const base = path.basename(name);
  const folders = [JS_DIR, ...fs.readdirSync(JS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory()).map((d) => path.join(JS_DIR, d.name))];
  const found = folders.map((f) => path.join(f, base)).find((f) => fs.existsSync(f));
  if (!found) throw new Error(`Max cannot find ${base}`);
  return found;
}

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
    constructor(file, access) {
      this.file = file;
      this.writing = access === "write" || access === "readwrite";
      try {
        this.bytes = Array.from(fs.readFileSync(file));
        this.isopen = true;
      } catch (e) {
        this.bytes = [];
        this.isopen = this.writing;
      }
      this.position = 0;
      this._eof = this.bytes.length;
    }
    get eof() {
      return this._eof;
    }
    set eof(n) {  // Max's File: setting eof truncates (or extends) the file
      this._eof = n;
      this.bytes.length = n;
    }
    readbytes(n) {
      const out = this.bytes.slice(this.position, Math.min(this.position + n, this._eof));
      this.position += out.length;
      return out;
    }
    writestring(text) {
      const bytes = Array.from(Buffer.from(String(text), "utf8"));
      this.bytes.splice(this.position, bytes.length, ...bytes);
      this.position += bytes.length;
      this._eof = Math.max(this._eof, this.position);
    }
    close() {
      if (this.writing && this.isopen) fs.writeFileSync(this.file, Buffer.from(this.bytes.slice(0, this._eof)));
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
 * Scripts for jsui (GUI_parameters/) are loaded with this one; a module may require others.
 */
function legacyRequire(name) {
  const file = onSearchPath(name);
  const exports = {};
  const ctx = { exports, post() {}, require: legacyRequire };
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
  const named = [];
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
    // A [send] to a named [receive]: recorded, and handed to options.receivers[name] if the test gives one.
    messnamed: (name, ...a) => {
      named.push([name, ...a]);
      if (options.receivers && options.receivers[name]) options.receivers[name](...a);
    },
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
    require: options.legacy ? legacyRequire : (name) => require(onSearchPath(name)),
    mgraphics: makeMgraphics(options.width || 300, options.height || 100),
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(onSearchPath(script), "utf8"), ctx, { filename: script });

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

  return { ctx, out, posts, embedded, named, send, flush, dicts };
}

function readDict(name) {
  return dicts.get(name);
}

module.exports = { load, readDict, legacyRequire, JS_DIR, Dict };
