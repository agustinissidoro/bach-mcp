/*
bachmcp.bpatcher.replace.js
---------------------------
Inside a small abstraction (bachmcp.transformer, .selector, .generator): replaces
that abstraction's box, once the patch has loaded, with a bpatcher of the real
thing, at the same place.

    [v8 bachmcp.bpatcher.replace.js <bpatcher file> <width> <height> [fixed args...]]
    [patcherargs] -> its inlet

The typed arguments become the bpatcher's @args. Fixed arguments, if any, come
right after the first typed one (the instance's name), so that it stays #1:

    [v8 bachmcp.bpatcher.replace.js bachmcp.bpatcher.algorithm 288 365 transformer]
    [bachmcp.transformer t1]  ->  [bpatcher @name bachmcp.bpatcher.algorithm @args t1 transformer]

With fixed arguments a name is needed (without it the first fixed one would be
taken as the name): a box without one says so in the Max console and stays.
*/
autowatch = 1;
inlets = 1;
outlets = 0;

const target = String(jsarguments[1] || "");
const width = Number(jsarguments[2]) || 128;
const height = Number(jsarguments[3]) || 128;
const fixed = Array.from(jsarguments).slice(4);  // after the name, e.g. the type
const me = this.patcher;
let done = false;

// patcherargs: its arguments as a list (or one word), nothing typed: bang
function bang() { later([]); }
function list(...args) { later(args); }
function anything(...args) { later([messagename, ...args]); }

function later(args) {
  if (done) return;
  done = true;
  // the box cannot be deleted while it is loading
  const task = new Task(() => replace(args), this);
  task.schedule(0);
}
later.local = 1;

/** The bpatcher's @args: the typed ones, the fixed ones right after the first (the name). */
function argsFor(args) {
  if (!fixed.length) return args;
  return [args[0], ...fixed, ...args.slice(1)];
}
argsFor.local = 1;

function replace(args) {
  const box = me.box;
  const parent = me.parentpatcher;
  if (!box || !parent || !target) return;
  if (fixed.length && !args.length) {
    error(`bachmcp.${fixed[0]}: give the instance a name, e.g. [bachmcp.${fixed[0]} t1]\n`);
    return;
  }
  const [left, top] = box.rect;
  const words = ["@name", target];
  const given = argsFor(args);
  if (given.length) words.push("@args", ...given);
  const bp = parent.newdefault(left, top, "bpatcher", ...words);
  if (bp) bp.rect = [left, top, left + width, top + height];
  parent.remove(box);
}
replace.local = 1;
