/*
bachmcp.server.playground.js
---------------------
Node for Max ([node.script]): makes sure a playground folder is there, with

    <path>/algorithms
    <path>/scores
    <path>/prompts
    <path>/gen
    <path>/recipes
    <path>/databases
    <path>/skills              the skill files the model's skill is built from (<name>.md)
    <path>/skills/profiles     lists of skills (<name>.json)
    <path>/skills/core-algorithmic.md
                               a copy of the package's skill (py/bach_mcp/prompt/BACH_SKILL.md)
    <path>/skills/core-electronic.md
                               a copy of the sound skill (py/bach_mcp/prompt/GEN_SKILL.md): gen~,
                               for synth and fx instances
    <path>/skills/quantizer.md
                               a copy of the quantizer skill (py/bach_mcp/prompt/QUANTIZER_SKILL.md)
    <path>/skills/profiles/minimal-algorithmic-composer.json
                               {"skills": ["core-algorithmic"]}
    <path>/skills/profiles/minimal-electronic-composer.json
                               {"skills": ["core-electronic"]}
                               profiles are made only when missing

A copy of a package skill stays in step with the package as long as the user has not
edited it: <path>/skills/.copied.json keeps a sha256 of each copy as it was made, and a
copy that still has it is replaced when the package's skill changes. An edited copy is
the user's and is never touched; deleting it brings back the package's. A copy made
before .copied.json existed is recorded once it equals the package's. The same rules
as py/bach_mcp/tools/playground.py, which the hub runs at set_playground.

    script start <path>

Whatever is missing is created, the folder itself included. The package's skills are
found from where this script is (<package>/javascript/server_utilities).

Out of the outlet, once it is done:

    "playground found at: "          everything was already there
    "playground created at" <path>   something was missing and is there now
    error <message>         it could not be made (a file in the way, no permission)

Outside Max, `node bachmcp.server.playground.js <path>` prints the same messages.
*/

"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

let Max = null;
try { Max = require("max-api"); } catch (e) { /* outside Max: print instead */ }

const FOLDERS = ["algorithms", "scores", "prompts", "gen", "recipes", "databases", "skills", path.join("skills", "profiles")];
const PROMPT = path.join(__dirname, "..", "..", "py", "bach_mcp", "prompt");
// [the package's skill, its copy in the playground], and [a profile, the skills it lists]
const CORES = [
    [path.join(PROMPT, "BACH_SKILL.md"), path.join("skills", "core-algorithmic.md")],
    [path.join(PROMPT, "GEN_SKILL.md"), path.join("skills", "core-electronic.md")],
    [path.join(PROMPT, "QUANTIZER_SKILL.md"), path.join("skills", "quantizer.md")],
];
const COPIED = path.join("skills", ".copied.json");  // {copy file name: sha256 of the copy as it was made}
const PROFILES = [
    [path.join("skills", "profiles", "minimal-algorithmic-composer.json"), ["core-algorithmic"]],
    [path.join("skills", "profiles", "minimal-electronic-composer.json"), ["core-electronic"]],
];

// Max quotes an atom with spaces in it, so a message is words; the path stays one atom.
function out(...atoms) {
    if (Max) return Max.outlet(...atoms);
    console.log(atoms.join(" "));
    return Promise.resolve();
}

// Max sends paths as "Macintosh HD:/Users/...": keep the part after the volume.
function localPath(folder) {
    const max = folder.match(/^[^/:]+:(\/.*)$/);
    return path.resolve(max ? max[1] : folder);
}

function sha256(file) {
    return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function readRecord(file) {
    try {
        const record = JSON.parse(fs.readFileSync(file, "utf8"));
        return record && typeof record === "object" && !Array.isArray(record) ? record : {};
    } catch (e) {
        return {};
    }
}

// Keys sorted, two spaces, a final newline: the same text as playground.py writes.
function writeRecord(file, record) {
    const sorted = {};
    for (const key of Object.keys(record).sort()) sorted[key] = record[key];
    return fs.promises.writeFile(file, JSON.stringify(sorted, null, 2) + "\n");
}

function isFolder(dir) {
    return fs.existsSync(dir) && fs.statSync(dir).isDirectory();
}

async function playground(folder) {
    try {
        if (!folder) throw new Error("use: script start <path>");
        const root = localPath(folder);
        const dirs = [root, ...FOLDERS.map(name => path.join(root, name))];
        for (const dir of dirs) {
            if (fs.existsSync(dir) && !isFolder(dir)) throw new Error(`${dir} is a file, not a folder`);
        }
        const missing = dirs.filter(dir => !isFolder(dir));
        for (const dir of missing) await fs.promises.mkdir(dir, { recursive: true });
        let made = missing.length;
        const recordFile = path.join(root, COPIED);
        const record = readRecord(recordFile);
        const before = JSON.stringify(record);
        for (const [skill, copy] of CORES) {
            const core = path.join(root, copy);
            const key = path.basename(copy);
            if (!fs.existsSync(skill)) throw new Error(`the package's skill is not at ${skill}`);
            const shipped = sha256(skill);
            if (fs.existsSync(core)) {
                const current = sha256(core);
                if (current === shipped) { record[key] = shipped; continue; }  // in step
                if (record[key] !== current) continue;  // edited by the user, or of unknown origin: theirs
            }
            await fs.promises.copyFile(skill, core);
            record[key] = shipped;
            made++;
        }
        if (JSON.stringify(record) !== before) await writeRecord(recordFile, record);
        for (const [file, skills] of PROFILES) {
            const profile = path.join(root, file);
            if (fs.existsSync(profile)) continue;
            await fs.promises.writeFile(profile, JSON.stringify({ skills }, null, 2) + "\n");
            made++;
        }
        if (made) await out("playground created at", root);
        else await out("playground found at: ");
    } catch (e) {
        process.exitCode = 1;
        await out("error", ...e.message.split(" "));
    }
}

playground(process.argv.slice(2).join(" "));
