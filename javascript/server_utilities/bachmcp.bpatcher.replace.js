/*
bachmcp.bpatcher.replace.js — an abstraction that turns into a bpatcher.

A package mapping (max definesubstitution) can make a name a bpatcher, but
cannot pass what is typed after the name into @args. So the name is an
abstraction instead (bachmcp.transformer.maxpat), where typed arguments arrive
as usual, holding:

  [patcherargs] -> [v8 bachmcp.bpatcher.replace.js <patcher> <width> <height>]

On load the script puts a bpatcher of <patcher> where the abstraction's box
is, with the box's arguments as @args, and deletes the box:

  [bachmcp.transformer t1]  ->  [bpatcher @name bachmcp.bpatcher.transformer @args t1]

The parent patcher then saves the bpatcher, so this happens once. Opened on its
own (not inside a patcher), the abstraction does nothing.
*/

autowatch = 1;
inlets = 1;
outlets = 0;

const target = String(jsarguments[1] || "");
const width = Number(jsarguments[2]) || 128;
const height = Number(jsarguments[3]) || 128;
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

function replace(args) {
  const box = me.box;
  const parent = me.parentpatcher;
  if (!box || !parent || !target) return;
  const [left, top] = box.rect;
  const words = ["@name", target];
  if (args.length) words.push("@args", ...args);
  const bp = parent.newdefault(left, top, "bpatcher", ...words);
  if (bp) bp.rect = [left, top, left + width, top + height];
  parent.remove(box);
}
replace.local = 1;
