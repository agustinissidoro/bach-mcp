// bach.mcp.algo (v8) and bach.mcp.translate (v8), run on a stand-in for Max.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const vm = require("vm");
const { load, readDict } = require("./maxmock.js");

const ALGO = `// one line
const params = {
  times: { type: "slider", range: [1, 64], value: 4 },
  register: { type: "range", range: [3600, 9600], value: [6000, 7200] },
  mode: { type: "menu", options: ["up", "down"] },
  seed: { type: "seed", value: 1 },
};
function generate(p, input) {
  const s = score();
  const v = s.voice("Flute");
  for (let i = 0; i < p.times; i++) {
    const k = p.mode === "up" ? i : p.times - 1 - i;
    v.note(i * 100, lerp(p.register[0], p.register[1], k / Math.max(1, p.times - 1)), 100);
  }
  if (input) for (const voice of input.voices) s.voices.push(voice);
  return s;
}
`;

function tempFile(text) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "bachmcp-"));
  const file = path.join(dir, "test_algo.js");
  fs.writeFileSync(file, text);
  return file;
}

function last(out, index, selector) {
  for (let i = out.length - 1; i >= 0; i--) {
    if (out[i][0] === index && (selector === undefined || out[i][1] === selector)) return out[i];
  }
  return null;
}

function scoreOut(m) {
  const msg = last(m.out, 0, "dictionary");
  return msg ? readDict(msg[2]) : null;
}

test("load: spec to the panel, score out, loaded to the status outlet", () => {
  const m = load("bach.mcp.algo.js");
  m.send("setname", "algo");
  m.send("load", tempFile(ALGO));
  const spec = JSON.parse(last(m.out, 1, "spec")[2]);
  assert.equal(spec.title, "test_algo");
  assert.deepEqual(spec.params.map((p) => [p.name, p.type]), [["times", "slider"], ["register", "range"], ["mode", "menu"], ["seed", "seed"]]);
  assert.deepEqual(last(m.out, 2), [2, "loaded", "algo", "test_algo.js", 4, last(m.out, 2)[5]]);
  const score = scoreOut(m);
  assert.deepEqual(score.voices[0].chords.map((c) => c.notes[0].pitch), [6000, 6400, 6800, 7200]);
  assert.equal(last(m.out, 1, "status")[2], "ok");
});

test("a parameter message updates the panel and runs again (debounced)", () => {
  const m = load("bach.mcp.algo.js");
  m.send("load", tempFile(ALGO));
  const before = m.out.length;
  m.send("times", 2.6);
  m.send("mode", "down");
  assert.deepEqual(last(m.out, 1, "set"), [1, "set", "mode", "down"]);
  assert.deepEqual(m.out.slice(before).filter((o) => o[1] === "set")[0], [1, "set", "times", 3]);
  assert.equal(m.out.slice(before).filter((o) => o[0] === 0).length, 0, "nothing runs before the task fires");
  m.flush();
  assert.deepEqual(scoreOut(m).voices[0].chords.map((c) => c.notes[0].pitch), [7200, 6600, 6000]);
  assert.deepEqual(last(m.out, 2).slice(0, 4), [2, "done", "algo", 3]);
});

test("unknown parameters and bad values are reported, not fatal", () => {
  const m = load("bach.mcp.algo.js");
  m.send("tempo", 3);
  assert.match(last(m.out, 2)[3], /no algorithm loaded/);
  m.send("load", tempFile(ALGO));
  m.send("tempo", 3);
  assert.match(last(m.out, 2)[3], /"tempo" is not a parameter. Parameters: times, register, mode, seed/);
  m.send("mode", "sideways");
  assert.match(last(m.out, 1, "status")[3], /cannot use/);
});

test("reloading keeps values of parameters that keep their name and type", () => {
  const file = tempFile(ALGO);
  const m = load("bach.mcp.algo.js");
  m.send("load", file);
  m.send("times", 8);
  m.send("register", 4800, 6000);
  m.flush();
  fs.writeFileSync(file, ALGO.replace('register: { type: "range"', 'register: { type: "slider"').replace(
    "value: [6000, 7200]", "value: 6000").replace("lerp(p.register[0], p.register[1],", "lerp(p.register, p.register + 1200,"));
  m.flush(true); // the watcher notices the change
  const spec = JSON.parse(last(m.out, 1, "spec")[2]);
  const values = Object.fromEntries(spec.params.map((p) => [p.name, p.value]));
  assert.equal(values.times, 8);
  assert.equal(values.register, 6000, "the type changed: back to the declared value");
  assert.equal(scoreOut(m).voices[0].chords.length, 8);
});

test("a broken file keeps the last good score and names the line", () => {
  const file = tempFile(ALGO);
  const m = load("bach.mcp.algo.js");
  m.send("load", file);
  const good = last(m.out, 0, "dictionary");
  fs.writeFileSync(file, ALGO.replace("const s = score();", "const s = score();\n  undefinedThing();"));
  m.send("reload");
  assert.match(last(m.out, 2)[3], /undefinedThing is not defined \(line 10\)/);
  assert.equal(last(m.out, 0, "dictionary"), good);
});

test("remote messages are acted on only by the runner they name", () => {
  const file = tempFile(ALGO);
  const a = load("bach.mcp.algo.js");
  const b = load("bach.mcp.algo.js");
  a.send("setname", "algo");
  b.send("setname", "strings");
  a.send("remote", "strings", "load", file);
  b.send("remote", "strings", "load", file);
  assert.equal(last(a.out, 1, "spec"), null);
  assert.notEqual(last(b.out, 1, "spec"), null);
  b.send("remote", "strings", "times", 2);
  b.flush();
  assert.equal(scoreOut(b).voices[0].chords.length, 2);
  b.send("done");
  assert.equal(last(b.out, 2)[1], "done");
});

test("the setname message can carry a file to load", () => {
  const m = load("bach.mcp.algo.js");
  m.send("setname", "algo", tempFile(ALGO));
  assert.equal(last(m.out, 2)[1], "loaded");
});

test("an input score reaches generate", () => {
  const m = load("bach.mcp.algo.js");
  m.send("load", tempFile(ALGO));
  const translate = load("bach.mcp.translate.js");
  translate.send("in", "bach");
  translate.send("out", "json");
  translate.send("roll", "[", "[", 0, "[", 3600, 1000, 100, "]", "]", "]");
  const dict = last(translate.out, 0, "dictionary")[2];
  m.send("input", "dictionary", dict);
  m.flush();
  const score = scoreOut(m);
  assert.equal(score.voices.length, 2);
  assert.equal(score.voices[1].chords[0].notes[0].pitch, 3600);
});

test("translate json -> bach: the messages bach.roll needs", () => {
  const t = load("bach.mcp.translate.js");
  const score = { voices: [{ name: "Violin", chords: [
    { onset: 0, dyn: "p<", notes: [{ pitch: 6950, dur: 500 }] },
    { onset: 500, art: "tenuto", notes: [{ pitch: 7000, dur: 500, gliss: [[0.5, 100], [1, -200]] }] },
  ] }] };
  const holder = new (require("./maxmock.js").Dict)("in_score");
  holder.parse(JSON.stringify(score));
  t.send("dictionary", "in_score");
  assert.deepEqual(t.out[0], [0, "tonedivision", 4]);
  const roll = t.out[1];
  assert.equal(roll[1], "roll");
  assert.equal(roll.slice(1).join(" "),
    "roll [ clefs G ] [ voicenames Violin ] [ markers ] [ [ 0 [ 6950 500 55 [ slots [ 20 p< ] ] ] ] " +
    "[ 500 [ 7000 500 55 [ breakpoints [ 0 0 0 ] [ 0.5 100 0 ] [ 1 -200 0 ] ] [ slots [ 22 portato ] ] ] ] ]");
  assert.ok(roll.includes(6950) && roll.includes(-200), "numbers leave as numbers, not symbols");
});

test("translate refuses what does not match @in, and reports bad scores", () => {
  const t = load("bach.mcp.translate.js");
  t.send("roll", "[", "]");
  assert.match(t.posts.pop(), /@in is json/);
  t.send("in", "bach");
  t.send("dictionary", "x");
  assert.match(t.posts.pop(), /@in is bach/);
  t.send("bach.llll", 123);
  assert.match(t.posts.pop(), /bach.portal @out t/);
  t.send("in", "json");
  t.send("json", JSON.stringify({ voices: [{ chords: [{ onset: 0, notes: [{ pitch: 60, dur: 1 }] }] }] }));
  assert.match(t.posts.pop(), /looks like a MIDI note number/);
  t.send("in", "sideways");
  assert.match(t.posts.pop(), /must be json or bach/);
});

test("translate bach -> bach round trip, and add mode", () => {
  const t = load("bach.mcp.translate.js");
  t.send("in", "bach");
  t.send("add", 1);
  t.send("roll", "[", "clefs", "F", "]", "[", "[", 0, "[", 3600, 1000, 100, "]", "]", "]");
  assert.deepEqual(t.out[0].slice(1).join(" "), "addchords [ [ 0 [ 3600 1000 100 ] ] ]");
});

test("very long scores are sent in slices", () => {
  const S = require(path.join(require("./maxmock.js").JS_DIR, "bach.mcp.score.js"));
  const chords = [];
  for (let i = 0; i < 3000; i++) chords.push({ onset: i * 10, notes: [{ pitch: 6000 + (i % 12) * 100, dur: 10 }] });
  const canonical = S.normalizeScore({ voices: [{ name: "A", chords }, { name: "B", chords: chords.slice(0, 10) }] });
  const messages = S.scoreMessagesChunked(canonical, false, 2000);
  assert.ok(messages.length > 5);
  assert.ok(messages.every((m) => S.countAtoms(m) <= 2000));
  assert.match(messages[0], /^roll \[clefs G G\] \[voicenames A B\] \[markers\] \[\] \[\]$/);
  let total = 0;
  for (const m of messages.slice(1)) total += (m.match(/\[\d+ \[/g) || []).length;
  assert.equal(total, 3010);
  assert.deepEqual(S.scoreMessagesChunked(canonical, false), S.scoreMessages(canonical, false));
});

const TRANSFORMER = `const params = { shift: { type: "slider", range: [-1200, 1200], value: 100 } };
function transform(source, p) { const out = copy(source); eachNote(out, (n) => { n.pitch += p.shift; }); return out; }`;
const ROLL = "roll [ clefs G ] [ [ 0 [ 6000 500 100 0 ] 0 ] [ 1000 [ 6200 500 100 0 ] 0 ] 0 ]";

// bach.roll behind [r to_bach]: writetxt writes `text` to the file.
function rollWriting(text) {
  return { to_bach: (cmd, file) => { if (cmd === "writetxt") fs.writeFileSync(file, text); } };
}

function scorePitches(m) {
  return scoreOut(m).voices.map((v) => v.chords.map((c) => c.notes[0].pitch));
}

test("a transformer takes the roll as its source when it is first loaded, and keeps it", () => {
  const file = tempFile(TRANSFORMER);
  const sourceFile = file.replace(/\.js$/, ".source.txt");
  const m = load("bach.mcp.algo.js", { receivers: rollWriting(ROLL) });
  m.send("load", file);
  assert.deepEqual(m.named[0], ["to_bach", "writetxt", sourceFile]);
  assert.equal(JSON.parse(last(m.out, 1, "spec")[2]).kind, "transformer");
  m.flush(true); // the runner notices the file bach.roll wrote
  assert.deepEqual(scorePitches(m), [[6100, 6300]]);
  assert.equal(last(m.out, 2)[1], "loaded");
  assert.deepEqual(last(m.out, 1, "source"), [1, "source", 2, "file"]);
  m.send("shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[6200, 6400]], "from the original again");
  m.send("reload");
  assert.equal(m.named.length, 1, "a reload keeps the source: no new capture");
});

test("a saved source is used without asking the roll; capture takes the roll again", () => {
  const file = tempFile(TRANSFORMER);
  fs.writeFileSync(file.replace(/\.js$/, ".source.txt"), "roll [ [ 0 [ 4800 500 100 0 ] 0 ] 0 ]");
  const m = load("bach.mcp.algo.js", { receivers: rollWriting(ROLL) });
  m.send("load", file);
  assert.equal(m.named.length, 0);
  assert.deepEqual(scorePitches(m), [[4900]]);
  m.send("capture");
  m.flush(true);
  assert.deepEqual(scorePitches(m), [[6100, 6300]]);
});

test("a capture that bach.roll never answers is reported", () => {
  const m = load("bach.mcp.algo.js", { receivers: {} });
  m.send("roll", "my_roll");
  m.send("load", tempFile(TRANSFORMER));
  assert.equal(m.named[0][0], "my_roll");
  vm.runInContext("Date.now = ((real) => () => real() + 60000)(Date.now);", m.ctx); // a minute later
  m.flush(true);
  assert.match(last(m.out, 2)[3], /bach.roll did not write the score \(is it fed by \[r my_roll\]\?\)/);
});

test("a score at the right inlet is a source too; a producer needs none", () => {
  const m = load("bach.mcp.algo.js", { receivers: {} });
  m.send("load", tempFile(TRANSFORMER));
  const translate = load("bach.mcp.translate.js");
  translate.send("in", "bach");
  translate.send("out", "json");
  translate.send("roll", "[", "[", 0, "[", 3600, 1000, 100, "]", "]", "]");
  m.send("input", "dictionary", last(translate.out, 0, "dictionary")[2]);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  assert.deepEqual(last(m.out, 1, "source"), [1, "source", 1, "inlet"]);
  const p = load("bach.mcp.algo.js");
  p.send("load", tempFile(ALGO));
  assert.equal(JSON.parse(last(p.out, 1, "spec")[2]).kind, "producer");
  assert.equal(p.named.length, 0);
});

function inputFrom(m, llll) {
  const translate = load("bach.mcp.translate.js");
  translate.send("in", "bach");
  translate.send("out", "json");
  translate.send(...llll.split(" ").filter(Boolean).map((t) => (/^-?\d+(\.\d+)?$/.test(t) ? Number(t) : t)));
  m.send("input", "dictionary", last(translate.out, 0, "dictionary")[2]);
}

test("keep: the first score at the inlet becomes the source and is saved; later ones are ignored", () => {
  const file = tempFile(TRANSFORMER);
  const sourceFile = file.replace(/\.js$/, ".source.txt");
  const m = load("bach.mcp.algo.js", { receivers: {} });
  m.send("load", file);
  inputFrom(m, "roll [ [ 0 [ 3600 1000 100 ] ] ]");
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  assert.match(fs.readFileSync(sourceFile, "utf8"), /^roll /, "saved next to the algorithm");
  inputFrom(m, "roll [ [ 0 [ 4800 1000 100 ] ] ]");
  m.flush();
  m.send("shift", 200);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]], "still the original");
  const again = load("bach.mcp.algo.js", { receivers: {} });
  again.send("load", file);
  assert.equal(again.named.length, 0, "reopened: the saved source, no capture");
  assert.deepEqual(scorePitches(again), [[3700]]);
});

test("follow: every score at the inlet becomes the source; only the first one runs by itself", () => {
  const m = load("bach.mcp.algo.js", { receivers: {} });
  m.send("sourcemode", "follow");
  assert.deepEqual(last(m.out, 1, "sourcemode"), [1, "sourcemode", "follow"]);
  m.send("load", tempFile(TRANSFORMER));
  inputFrom(m, "roll [ [ 0 [ 3600 1000 100 ] ] ]");
  m.flush();
  assert.deepEqual(scorePitches(m), [[3700]]);
  const runs = m.out.filter((o) => o[0] === 0).length;
  inputFrom(m, "roll [ [ 0 [ 3700 1000 100 ] ] ]");  // the result, back from the roll
  m.flush();
  assert.equal(m.out.filter((o) => o[0] === 0).length, runs, "no run: no loop through the roll");
  assert.deepEqual(last(m.out, 1, "source"), [1, "source", 1, "inlet"]);
  m.send("shift", 100);
  m.flush();
  assert.deepEqual(scorePitches(m), [[3800]], "the next change transforms the latest score");
  m.send("sourcemode", "maybe");
  assert.match(last(m.out, 2)[3], /sourcemode is keep or follow/);
});
