/*
bachmcp.filechecker.js
---------------------
Node for Max ([node.script]): says whether a path exists (a file or a folder).

    script start <path>
    script start <path> <path> ...

Out of the outlet, one message for each path, in the order given:

    <path> 1                it exists
    <path> 0                it does not

The path comes out as it came in, as one atom. Paths are absolute: /Users/...,
~/..., or as Max writes them, "Macintosh HD:/Users/...". A path with spaces may arrive
in pieces (a message is split at its spaces): a piece that does not begin a path is
put back onto the one before it. A path that arrives as one atom is taken as it is.

Outside Max, `node bachmcp.filechecker.js <path> ...` prints the same messages.
*/

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

let Max = null;
try { Max = require("max-api"); } catch (e) { /* outside Max: print instead */ }

const VOLUME = /^[^/:]+:\//;  // HD:/Users/...  (the end of "Macintosh HD:/Users/...")

function out(...atoms) {
    if (Max) return Max.outlet(...atoms);
    console.log(atoms.join(" "));
    return Promise.resolve();
}

// The words of the message as paths. A word with a space in it arrived whole: it is a path.
// Any other word begins a path if it starts with / or ~, if it is the name of a Max volume
// (itself, or the word before the piece with ":/"), or if the path before it arrived whole.
function paths(words) {
    const found = [];  // {text, whole}
    words.forEach((word, i) => {
        const last = found[found.length - 1];
        const whole = word.includes(" ");
        const open = last && !last.whole && !last.text.includes("/");  // a volume's name still being read
        const next = words[i + 1] || "";
        const begins = whole || !last || last.whole || word.startsWith("/") || word.startsWith("~") ||
                       (!open && (VOLUME.test(word) || (!word.includes("/") && !next.includes(" ") && VOLUME.test(next))));
        if (begins) found.push({ text: word, whole });
        else last.text += " " + word;
    });
    return found.map(file => file.text);
}

// Max sends paths as "Macintosh HD:/Users/...": keep the part after the volume.
function localPath(file) {
    const max = file.match(/^[^/:]+:(\/.*)$/);
    const local = max ? max[1] : file;
    return path.resolve(local.startsWith("~") ? path.join(os.homedir(), local.slice(1)) : local);
}

async function check(words) {
    for (const file of paths(words)) {
        await out(file, fs.existsSync(localPath(file)) ? 1 : 0);
    out("done");
    }
}

check(process.argv.slice(2).filter(word => word !== ""));
