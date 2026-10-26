/*
bachmcp.playground.js
---------------------
Node for Max ([node.script]): makes sure a playground folder is there, with

    <path>/algorithms
    <path>/rolls
    <path>/prompts

    script start <path>

Whatever is missing is created, the folder itself included.

Out of the outlet, once it is done:

    exists                  everything was already there
    created <path>          something was missing and is there now
    error <message>         it could not be made (a file in the way, no permission)

Outside Max, `node bachmcp.playground.js <path>` prints the same messages.
*/

"use strict";

const fs = require("fs");
const path = require("path");

let Max = null;
try { Max = require("max-api"); } catch (e) { /* outside Max: print instead */ }

const FOLDERS = ["algorithms", "rolls", "prompts"];

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
        if (missing.length) await out("playground created at", root);
        else await out("playground found.");
    } catch (e) {
        process.exitCode = 1;
        await out("error", ...e.message.split(" "));
    }
}

playground(process.argv.slice(2).join(" "));
