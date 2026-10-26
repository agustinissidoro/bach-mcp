// bach.config.js: edit bachmcp.toml from Max, before Bach starts. For [node.script bach.config.js].
//
//   script start <path>        start with the file already set (the arguments of "script start")
//   config_file_path <path>    the bachmcp.toml to edit (Max path or plain path)
//   set <field> <value...>     e.g.  set temperature 0.5   set model qwen3.8-27b   (or section.key)
//
// Outlet: "config_file_path <path>", "set <field> <value...>" when written, "error <text>" otherwise.
// Only the value changes; comments stay. The field must be in the file and the value of the same kind.
"use strict";

const fs = require("fs");
const path = require("path");

// A setting's line: indent, key, " = ", value (a "text", a [list] or a word), the rest (a comment).
const QUOTED = String.raw`"(?:[^"\\]|\\.)*"`;
const LINE = new RegExp(String.raw`^(\s*)(\w+)(\s*=\s*)(` + QUOTED + String.raw`|\[[^\]]*\]|[^\s#]+)(.*)$`);
const HEADER = new RegExp(String.raw`^\s*\[([^\]]+)\]`);

function systemPath(p) {
  // "Macintosh HD:/Users/me/x" -> "/Users/me/x"
  const s = String(p).trim();
  const colon = s.indexOf(":/");
  return colon > 0 && !s.slice(0, colon).includes("/") ? s.slice(colon + 1) : s;
}

function fields(text) {
  // { "section.key": line number }
  const out = {};
  let section = "";
  text.split("\n").forEach((line, i) => {
    const h = line.match(HEADER);
    if (h && !line.match(LINE)) {
      section = h[1].trim();
      return;
    }
    const m = line.match(LINE);
    if (m && section) out[section + "." + m[2]] = i;
  });
  return out;
}

function kind(raw) {
  if (raw.startsWith('"')) return "text";
  if (raw.startsWith("[")) return "list";
  if (raw === "true" || raw === "false") return "true/false";
  return "number";
}

function quote(s) {
  return '"' + String(s).split("\\").join("\\\\").split('"').join('\\"') + '"';
}

function format(raw, values, field) {
  const k = kind(raw);
  if (k === "text") return quote(values.join(" "));
  if (k === "list") return "[" + values.map(quote).join(", ") + "]";
  if (values.length !== 1) throw new Error(field + " takes one value (" + k + ")");
  const v = String(values[0]);
  if (k === "true/false") {
    if (["1", "true", "on", "yes"].includes(v.toLowerCase())) return "true";
    if (["0", "false", "off", "no"].includes(v.toLowerCase())) return "false";
    throw new Error(field + " takes true/false (or 1/0), not " + v);
  }
  const n = Number(v);
  if (v.trim() === "" || !Number.isFinite(n)) throw new Error(field + " takes a number, not " + v);
  if (!raw.includes(".") && !Number.isInteger(n)) throw new Error(field + " takes a whole number, not " + v);
  return String(n);
}

function resolve(text, field) {
  // "temperature" -> "generation.temperature"; "section.key" as it is. Throws if unknown or ambiguous.
  const all = fields(text);
  if (field in all) return field;
  const matches = Object.keys(all).filter((k) => k.split(".").pop() === field);
  if (matches.length === 1) return matches[0];
  if (matches.length > 1) throw new Error(field + " is in several sections: say which, " + matches.join(" or "));
  throw new Error("no setting " + field + " in the file");
}

function setValue(text, field, values) {
  // text with field (a key, or section.key) set to values; throws an Error saying why it cannot
  field = resolve(text, field);
  const at = fields(text)[field];
  const lines = text.split("\n");
  const m = lines[at].match(LINE);
  const before = m[1] + m[2] + m[3] + format(m[4], values, field);
  const comment = m[5].match(/^(\s*)(#.*)$/);
  if (comment) {
    const column = (m[1] + m[2] + m[3] + m[4]).length + comment[1].length; // where the # was
    lines[at] = before + " ".repeat(Math.max(1, column - before.length)) + comment[2];
  } else {
    lines[at] = before + m[5];
  }
  return lines.join("\n");
}

function valueAtoms(text, field) {
  // the value as it now reads in the file, as atoms for Max
  field = resolve(text, field);
  const raw = text.split("\n")[fields(text)[field]].match(LINE)[4];
  const k = kind(raw);
  if (k === "text") return [JSON.parse(raw)];
  if (k === "list") return JSON.parse(raw);
  if (k === "true/false") return [raw === "true" ? 1 : 0];
  return [Number(raw)];
}

module.exports = { systemPath, fields, resolve, setValue, valueAtoms };

// In Max: [node.script] loads this file as the one named in SCRIPT_PATH (it is not Node's main
// module there). The tests only require the functions above.
const realPath = (p) => { try { return fs.realpathSync(p); } catch (e) { return path.resolve(p); } };
const inMax = Boolean(process.env.SCRIPT_PATH) && realPath(process.env.SCRIPT_PATH) === realPath(__filename);
if (inMax) {
  const maxApi = require("max-api");
  let file = "";

  const useFile = (words) => {
    const p = systemPath(words.join(" "));
    if (!fs.existsSync(p)) return maxApi.outlet("error", "no file " + p);
    file = p;
    maxApi.outlet("config_file_path", file);
  };
  maxApi.addHandler("config_file_path", (...words) => useFile(words));

  maxApi.addHandler("set", (field, ...values) => {
    if (!file) return maxApi.outlet("error", "no file yet: send config_file_path <path> first");
    if (!field) return maxApi.outlet("error", "set needs a field and a value, e.g. set temperature 0.5");
    try {
      const text = setValue(fs.readFileSync(file, "utf8"), String(field), values.map(String));
      const tmp = path.join(path.dirname(file), "." + path.basename(file) + ".tmp");
      fs.writeFileSync(tmp, text, "utf8");
      fs.renameSync(tmp, file); // whole or not at all
      maxApi.outlet("set", String(field), ...valueAtoms(text, String(field)));
    } catch (e) {
      maxApi.outlet("error", e.message);
    }
  });

  // "script start <path>": Node for Max passes those words as the process's arguments
  // (also "script start config_file_path <path>": the message name is then left out)
  const startArgs = process.argv.slice(2).join(" ").replace(/^\s*config_file_path\s+/, "").trim();
  if (startArgs) useFile([startArgs]);

  //maxApi.post("bach.config.js ready: send config_file_path <path>, then set <field> <value>");
}
