/*
bachmcp.download.js
-------------------
Node for Max ([node.script]): puts a model in a folder, one subfolder per model,
as py/bach_mcp/utilities/download.py does.

    script start download <model> <folder>
    script start model_catalog <folder>

<model> can be named four ways:

    qwen3-8b                                   a name from <folder>/catalog.toml
    mlx-community/Qwen3-8B-4bit                a Hugging Face repo (":QUANT" for one GGUF quantization)
    https://huggingface.co/<user>/<repo>[/blob/main/<file>]   a Hugging Face page, or one file in it
    https://<anywhere>/<file>                  a direct link to a file

Out of the outlet:

    catalog <name> <size>                 one per model in <folder>/catalog.toml (model_catalog)
    downloading <model> <size> <time>     once it has begun (size and time when they can be known)
    progress <model> <percent> <done> <time left>   every 5 minutes while it downloads
    done <model> <path>
    interrupted <model> <reason>          stopped, or the connection failed once it had begun
    error <message>                       before anything was downloaded

While it runs, `stop` (or `script stop`) interrupts it. A download that stops can be
started again: it goes on where it was. Outside Max, `node bachmcp.download.js download
<model> <folder>` (or `model_catalog <folder>`) prints the same messages. HF_TOKEN in the environment opens gated repos.
*/

"use strict";

const fs = require("fs");
const path = require("path");
const { Readable, Transform } = require("stream");
const { pipeline } = require("stream/promises");

let Max = null;
try { Max = require("max-api"); } catch (e) { /* outside Max: print instead */ }

const DEFAULT_QUANT = "Q4_K_M";   // what llama-server also picks when a GGUF repo names no quantization
const MEASURE_MS = 3000;          // how long to watch the speed before saying how long it will take
const PROGRESS_MS = 5 * 60 * 1000;  // how often to say how far it is
const HF_URL = /^https?:\/\/(?:www\.)?(?:huggingface\.co|hf\.co)\/([^/\s]+\/[^/\s]+?)(?:\/(?:blob|resolve|tree)\/[^/\s]+\/?(\S*))?\/?$/;

let job = null;   // the download running: { spec, controller, stopped, promise }

// Max quotes an atom with spaces in it ("16.1 GB"), so each word goes out as its own atom;
// one() keeps a text whole (a path).
function one(text) {
    return { whole: String(text) };
}

function out(...atoms) {
    atoms = atoms.flatMap(a => a && a.whole !== undefined ? [a.whole] : String(a).split(" ").filter(Boolean));
    if (Max) return Max.outlet(...atoms);
    console.log(atoms.join(" "));
    return Promise.resolve();
}


// ── The catalogue: models known by name ─────────────────────────────────── //

function loadCatalog(folder) {
    const file = path.join(folder, "catalog.toml");
    if (!fs.existsSync(file)) return {};
    const catalog = {};
    let entry = null;
    for (const raw of fs.readFileSync(file, "utf8").split("\n")) {
        const line = raw.trim();
        if (!line || line.startsWith("#")) continue;
        const header = line.match(/^\[\s*"?([^"\]]+?)"?\s*\]/);
        if (header) {
            entry = catalog[header[1].toLowerCase()] = { name: header[1] };
            continue;
        }
        const kv = line.match(/^([\w-]+)\s*=\s*(.+)$/);
        if (!entry || !kv) continue;
        const text = kv[2].match(/^"((?:[^"\\]|\\.)*)"/);
        entry[kv[1]] = text ? JSON.parse(`"${text[1]}"`) : parseFloat(kv[2]);
    }
    return catalog;
}


// ── Naming a model, and what its download fetches ───────────────────────── //

function parse(spec, catalog) {
    let text = spec.trim().replace(/^"|"$/g, "");
    const entry = catalog[text.toLowerCase()];
    if (entry && entry.repo) text = entry.repo;
    const hf = text.match(HF_URL);
    if (hf) return { repo: hf[1], file: hf[2] || null };
    if (/^https?:\/\//.test(text)) return { url: text };
    const [repo, quant] = text.split(":");
    if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) {
        throw new Error(`${spec}: not in catalog.toml, not a Hugging Face repo (user/repo[:QUANT]) and not a link`);
    }
    return { repo, quant: quant || null };
}

function ggufFiles(files, quant, repo) {
    const ggufs = files.filter(f => /\.gguf$/i.test(f.rel) && !/mmproj/i.test(f.rel));
    if (!ggufs.length) throw new Error(`${repo} has no .gguf file`);
    if (!quant && ggufs.length === 1) return ggufs;
    const wanted = (quant || DEFAULT_QUANT).toUpperCase();
    const match = new RegExp(`(?<![A-Z0-9])${wanted.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![A-Z0-9_])`);
    const chosen = ggufs.filter(f => match.test(path.basename(f.rel).toUpperCase()));
    if (!chosen.length) {
        const found = new Set(ggufs.map(f => (f.rel.toUpperCase().match(/I?Q\d[A-Z0-9_]*|F16|BF16|F32/) || [f.rel])[0]));
        throw new Error(`no ${wanted} file in ${repo}; it has: ${[...found].join(", ")}`);
    }
    return chosen;
}

async function makePlan(spec, folder, signal) {
    const where = parse(spec, loadCatalog(folder));
    if (where.url) {
        const res = await request(where.url, { method: "HEAD", signal });
        if (/text\/html/i.test(res.headers.get("content-type") || "")) {
            throw new Error(`${where.url} is a web page, not a file`);
        }
        const size = Number(res.headers.get("content-length")) || 0;
        const file = decodeURIComponent(path.basename(new URL(where.url).pathname)) || "model";
        return { name: file.replace(/\.[^.]+$/, ""), size, files: [{ url: where.url, rel: file, size }] };
    }
    const repo = where.repo;
    let files = [];
    let next = `https://huggingface.co/api/models/${repo}/tree/main?recursive=true`;
    while (next) {
        const res = await request(next, { signal });
        for (const e of await res.json()) {
            if (e.type !== "file") continue;
            const url = `https://huggingface.co/${repo}/resolve/main/${e.path.split("/").map(encodeURIComponent).join("/")}`;
            files.push({ url, rel: e.path, size: e.lfs ? e.lfs.size : e.size || 0 });
        }
        const link = (res.headers.get("link") || "").match(/<([^>]+)>;\s*rel="next"/);
        next = link ? link[1] : null;
    }
    if (where.file) {
        files = files.filter(f => f.rel === where.file);
        if (!files.length) throw new Error(`${repo} has no file ${where.file}`);
    } else if (!files.some(f => f.rel.endsWith(".safetensors"))) {
        files = ggufFiles(files, where.quant, repo);   // GGUF: one quantization; MLX: the whole repo
    }
    return { name: repo.split("/").pop(), size: files.reduce((n, f) => n + f.size, 0), files };
}


// ── Fetching ────────────────────────────────────────────────────────────── //

async function request(url, options = {}) {
    const headers = { ...options.headers };
    if (process.env.HF_TOKEN && /^https:\/\/(huggingface\.co|hf\.co)\//.test(url)) {
        headers.Authorization = `Bearer ${process.env.HF_TOKEN}`;
    }
    let res;
    try {
        res = await fetch(url, { ...options, headers });
    } catch (e) {
        if (e.name === "AbortError") throw e;
        const cause = e.cause ? e.cause.code || e.cause.message : e.message;
        throw new Error(`cannot reach ${url}: ${cause}`);
    }
    if (!res.ok && res.status !== 416) {
        const hint = res.status === 401 || res.status === 403 || res.status === 404
            ? " (not found, or private/gated: set HF_TOKEN)" : "";
        throw new Error(`${url}: ${res.status} ${res.statusText}${hint}`);
    }
    return res;
}

function sizeOn(file) {
    return fs.existsSync(file) ? fs.statSync(file).size : 0;
}

function whole(dest, file) {
    return fs.existsSync(dest) && (!file.size || sizeOn(dest) === file.size);
}

// One file into target/, going on from a part already there.
async function fetchFile(file, target, signal, onBytes) {
    const dest = path.join(target, file.rel);
    if (whole(dest, file)) return;
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    const part = dest + ".incomplete";
    const have = sizeOn(part);
    const res = await request(file.url, { headers: have ? { Range: `bytes=${have}-` } : {}, signal });
    if (res.status === 416) {   // the part was already whole
        fs.renameSync(part, dest);
        return;
    }
    if (have && res.status !== 206) onBytes(-have);   // the server starts it over
    const count = new Transform({ transform(chunk, _, done) { onBytes(chunk.length); done(null, chunk); } });
    const sink = fs.createWriteStream(part, { flags: res.status === 206 ? "a" : "w" });
    await pipeline(Readable.fromWeb(res.body), count, sink, { signal });
    fs.renameSync(part, dest);
}

function gigabytes(bytes) {
    return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.max(1, Math.round(bytes / 1e6))} MB`;
}

function duration(seconds) {
    if (seconds < 60) return "less than a minute";
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `about ${minutes} min`;
    return `about ${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

// Max sends paths as "Macintosh HD:/Users/...": keep the part after the volume.
function localPath(folder) {
    const max = folder.match(/^[^/:]+:(\/.*)$/);
    return path.resolve(max ? max[1] : folder);
}

async function download(spec, folder) {
    let begun = false, timer = null, ticker = null;
    try {
        if (!spec || !folder) throw new Error("use: download <model> <folder>");
        folder = localPath(folder);
        if (!fs.existsSync(folder)) throw new Error(`no folder ${folder}`);
        const plan = await makePlan(spec, folder, job.controller.signal);
        const target = path.join(folder, plan.name);
        if (plan.files.every(f => whole(path.join(target, f.rel), f))) {
            return await out("done", spec, one(target));
        }

        let done = plan.files.reduce((n, f) => {
            const dest = path.join(target, f.rel);
            return n + (whole(dest, f) ? sizeOn(dest) : sizeOn(dest + ".incomplete"));
        }, 0);
        let fresh = 0, started = 0, announced = false;
        const announce = () => {
            if (announced) return;
            announced = true;
            const atoms = ["downloading", spec];
            if (plan.size) atoms.push(gigabytes(plan.size));
            const speed = fresh / ((Date.now() - started) / 1000);
            if (plan.size && speed > 0) atoms.push(duration(Math.max(0, plan.size - done) / speed));
            out(...atoms);
        };
        let lastDone = 0, lastTime = 0;
        const progress = () => {
            const atoms = ["progress", spec];
            if (plan.size) {
                atoms.push(`${Math.floor(100 * done / plan.size)}%`, `${gigabytes(done)} of ${gigabytes(plan.size)}`);
                const speed = (done - lastDone) / ((Date.now() - lastTime) / 1000);   // over the last interval
                if (speed > 0) atoms.push(`${duration(Math.max(0, plan.size - done) / speed)} left`);
            } else {
                atoms.push(gigabytes(done));
            }
            lastDone = done;
            lastTime = Date.now();
            out(...atoms);
        };
        const onBytes = n => {
            if (!begun) {
                begun = true;
                started = Date.now();
                timer = setTimeout(announce, MEASURE_MS);
                lastDone = done;
                lastTime = started;
                ticker = setInterval(progress, PROGRESS_MS);
            }
            fresh += Math.max(0, n);
            done += n;
        };

        for (const file of plan.files) await fetchFile(file, target, job.controller.signal, onBytes);
        announce();   // when it was over before the speed could be measured
        await out("done", spec, one(target));
    } catch (e) {
        process.exitCode = 1;
        if (job.stopped) await out("interrupted", spec, job.stopped);
        else if (begun) await out("interrupted", spec, e.message);
        else await out("error", e.message);
    } finally {
        clearTimeout(timer);
        clearInterval(ticker);
    }
}

async function listCatalog(folder) {
    if (!folder) return out("error", "use: model_catalog <folder>");
    folder = localPath(folder);
    if (!fs.existsSync(path.join(folder, "catalog.toml"))) return out("error", `no catalog.toml in ${folder}`);
    for (const entry of Object.values(loadCatalog(folder))) {
        await out("catalog", entry.name, entry.size_gb ? `${entry.size_gb} GB` : "unknown size");
    }
}

function run(spec, folder) {
    if (job) return out("error", `already downloading ${job.spec}: send stop first`);
    job = { spec, controller: new AbortController(), stopped: null };
    job.promise = download(spec ? String(spec) : "", folder).finally(() => { job = null; });
    return job.promise;
}

function stop(reason) {
    if (!job) return;
    job.stopped = reason;
    job.controller.abort();
}


// ── Starting ────────────────────────────────────────────────────────────── //

for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, async () => {
        if (job) {
            const running = job.promise;
            stop("stopped");
            await running;
        }
        process.exit(process.exitCode || 0);
    });
}

if (Max) {
    Max.addHandler("download", (spec, ...folder) => run(spec, folder.join(" ")));
    Max.addHandler("stop", () => stop("stopped"));
    Max.addHandler("model_catalog", (...folder) => listCatalog(folder.join(" ")));
}

const [command, ...args] = process.argv.slice(2);
if (command === "download") run(args[0], args.slice(1).join(" "));
else if (command === "model_catalog") listCatalog(args.join(" "));
else if (command) out("error", `unknown command ${command}: use download <model> <folder> or model_catalog <folder>`);
else if (!Max) out("error", "use: download <model> <folder> or model_catalog <folder>");
