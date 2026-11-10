/*
bachmcp.server.playground.js
---------------------
Node for Max ([node.script]): makes sure a playground folder is there, with

    <path>/algorithms
    <path>/scores
    <path>/prompts
    <path>/gen
    <path>/skills              the skill files the model's skill is built from (<name>.md)
    <path>/skills/profiles     lists of skills (<name>.json)
    <path>/skills/core-algorithmic.md
                               a copy of the package's skill (py/bach_mcp/prompt/BACH_SKILL.md)
    <path>/skills/core-electronic.md
                               a copy of the sound skill (py/bach_mcp/prompt/GEN_SKILL.md): gen~,
                               for synth and fx instances
    <path>/skills/profiles/minimal-algorithmic-composer.json
                               {"skills": ["core-algorithmic"]}
    <path>/skills/profiles/minimal-electronic-composer.json
                               {"skills": ["core-electronic"]}
                               all made only when missing: once there, they are the user's to edit

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

const fs = require("fs");
const path = require("path");

let Max = null;
try { Max = require("max-api"); } catch (e) { /* outside Max: print instead */ }

const FOLDERS = ["algorithms", "scores", "prompts", "gen", "skills", path.join("skills", "profiles")];
const PROMPT = path.join(__dirname, "..", "..", "py", "bach_mcp", "prompt");
// [the package's skill, its copy in the playground], and [a profile, the skills it lists]
const CORES = [
    [path.join(PROMPT, "BACH_SKILL.md"), path.join("skills", "core-algorithmic.md")],
    [path.join(PROMPT, "GEN_SKILL.md"), path.join("skills", "core-electronic.md")],
];
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
        for (const [skill, copy] of CORES) {
            const core = path.join(root, copy);
            if (fs.existsSync(core)) continue;
            if (!fs.existsSync(skill)) throw new Error(`the package's skill is not at ${skill}`);
            await fs.promises.copyFile(skill, core);
            made++;
        }
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
