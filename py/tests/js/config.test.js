// bachmcp.server.config.js: editing bachmcp.toml from Max. Run: node --test "py/tests/js/*.test.js"
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const C = require(path.join(__dirname, "..", "..", "..", "max", "bach-mcp", "javascript", "server_utilities", "bachmcp.server.config.js"));
const REAL = fs.readFileSync(path.join(__dirname, "..", "..", "..", "bachmcp.toml"), "utf8");

const TOML = `# top comment
[model]
model = ""                # the model
context_size = 65536      # tokens
extra_args = []           # flags

[generation]
temperature = 0.7         # sampling
reasoning = "off"

[chat]
docs = true               # instrument docs
`;

test("a Max path becomes a system path", () => {
  assert.strictEqual(C.systemPath("Macintosh HD:/Users/me/bach-mcp/bachmcp.toml"), "/Users/me/bach-mcp/bachmcp.toml");
  assert.strictEqual(C.systemPath("/Users/me/bachmcp.toml"), "/Users/me/bachmcp.toml");
});

test("every setting of the real bachmcp.toml is found", () => {
  const f = C.fields(REAL);
  for (const key of ["model.model", "generation.temperature", "chat.docs", "server.port", "max.send_port", "algo.node"]) {
    assert.ok(key in f, key);
  }
});

test("set changes only the value and keeps the comments", () => {
  let t = C.setValue(TOML, "generation.temperature", ["0.5"]);
  assert.ok(t.includes("temperature = 0.5         # sampling"));
  t = C.setValue(t, "model.model", ["qwen3.8-27b"]);
  assert.ok(t.includes('model = "qwen3.8-27b"     # the model'));
  t = C.setValue(t, "chat.docs", ["0"]);
  assert.ok(t.includes("docs = false              # instrument docs"));
  t = C.setValue(t, "model.extra_args", ["--prompt-cache-size", "4"]);
  assert.ok(t.includes('extra_args = ["--prompt-cache-size", "4"] # flags'));
  assert.ok(t.startsWith("# top comment\n[model]"));
  assert.deepStrictEqual(C.valueAtoms(t, "chat.docs"), [0]);
  assert.deepStrictEqual(C.valueAtoms(t, "model.model"), ["qwen3.8-27b"]);
});

test("text with spaces and quotes stays one value", () => {
  const t = C.setValue(TOML, "model.model", ["my", 'model "x"']);
  assert.deepStrictEqual(C.valueAtoms(t, "model.model"), ['my model "x"']);
});

test("mistakes are refused, and say why", () => {
  assert.throws(() => C.setValue(TOML, "generation.temprature", ["1"]), /no setting generation.temprature/);
  assert.throws(() => C.setValue(TOML, "temprature", ["1"]), /no setting temprature/);
  assert.throws(() => C.setValue(TOML, "generation.temperature", ["hot"]), /takes a number/);
  assert.throws(() => C.setValue(TOML, "model.context_size", ["0.5"]), /whole number/);
  assert.throws(() => C.setValue(TOML, "chat.docs", ["maybe"]), /true\/false/);
});

test("an empty text empties it", () => {
  const t = C.setValue(C.setValue(TOML, "model.model", ["x"]), "model.model", []);
  assert.deepStrictEqual(C.valueAtoms(t, "model.model"), [""]);
});

test("the same key name in two sections is set only where asked", () => {
  const two = TOML + '\n[other]\nmodel = "keep"\n';
  const t = C.setValue(two, "model.model", ["x"]);
  assert.ok(t.includes('[other]\nmodel = "keep"'));
  assert.throws(() => C.setValue(two, "model", ["x"]), /in several sections: say which, model.model or other.model/);
});

test("a key alone is enough when it is in one section", () => {
  let t = C.setValue(TOML, "model", ["qwen3.8-27b"]);
  t = C.setValue(t, "temperature", ["0.3"]);
  t = C.setValue(t, "docs", ["0"]);
  assert.deepStrictEqual(C.valueAtoms(t, "model"), ["qwen3.8-27b"]);
  assert.deepStrictEqual(C.valueAtoms(t, "generation.temperature"), [0.3]);
  assert.deepStrictEqual(C.valueAtoms(t, "docs"), [0]);
});

test("every key of the real file can be set by its name alone", () => {
  for (const key of Object.keys(C.fields(REAL))) assert.strictEqual(C.resolve(REAL, key.split(".").pop()), key);
});
