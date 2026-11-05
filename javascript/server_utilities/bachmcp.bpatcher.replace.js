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
