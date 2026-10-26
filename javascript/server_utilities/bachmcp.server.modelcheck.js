/*
bachmcp.modelcheck.js
---------------------
Node for Max ([node.script]): says whether a model is there.

    script start <model> <model folder>

<model> is a full path (/Users/.../Qwen3-8B-4bit, ~/..., or Max's "Macintosh HD:/...")
or a name in <model folder>: a folder (MLX, or GGUF) or a single .gguf file, with or
without the ".gguf". It counts as found only when it holds a model, as config.py sees it:
.safetensors weights (MLX), or a .gguf file or a folder with one (GGUF).

Out of the outlet:

    using <model> at <path>
    <model> not found

Outside Max, `node bachmcp.modelcheck.js <model> <model folder>` prints the same messages.
*/

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

let Max = null;
try { Max = require("max-api"); } catch (e) { /* outside Max: print instead */ }

// Max quotes an atom with spaces in it, so a message is words; the model stays one atom.
function out(...atoms) {
    if (Max) return Max.outlet(...atoms);
    console.log(atoms.join(" "));
    return Promise.resolve();
}

// Max sends paths as "Macintosh HD:/Users/...": keep the part after the volume.
function localPath(text) {
    const max = text.match(/^[^/:]+:(\/.*)$/);
    if (max) return max[1];
    return text.startsWith("~") ? path.join(os.homedir(), text.slice(1)) : text;
}

function isFullPath(text) {
    return /^[^/:]+:\//.test(text) || text.startsWith("/") || text.startsWith("~");
}

// "mlx", "gguf" or "" (not a model), as model_format in py/bach_mcp/config.py.
function modelFormat(where) {
    if (!fs.existsSync(where)) return "";
    if (fs.statSync(where).isFile()) return /\.gguf$/i.test(where) ? "gguf" : "";
    const names = fs.readdirSync(where);
    if (names.some(n => n.endsWith(".safetensors"))) return "mlx";
    if (names.some(n => /\.gguf$/i.test(n))) return "gguf";
    return "";
}

// Where the model is, or "" when there is none. The disk may ignore case, so the path is
// written as it is on disk ("Qwen3.8-27B-4bit"), not as it was asked for.
function findModel(model, folder) {
    const real = where => fs.realpathSync.native(where);
    if (isFullPath(model)) {
        const where = localPath(model);
        return modelFormat(where) ? real(where) : "";
    }
    if (!folder) return "";
    const where = path.join(path.resolve(localPath(folder)), model);
    if (modelFormat(where)) return real(where);
    if (modelFormat(where + ".gguf")) return real(where + ".gguf");
    return "";
}

const [model, ...folder] = process.argv.slice(2);
const where = model ? findModel(model, folder.join(" ")) : "";
if (!model) out("error", "use:", "script", "start", "<model>", "<model", "folder>");
else if (where) out("using", model, "at", where);
else out(model, "not", "found");
