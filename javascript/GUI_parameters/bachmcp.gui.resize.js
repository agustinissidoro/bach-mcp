autowatch = 1;
outlets = 1;

var listeners = [];
var box = null;
var attrs = ["patching_rect", "presentation_rect"];

// --- startup read: delayed, retried until valid, then stops ---
var INIT_DELAY = 50;    // ms before first attempt
var RETRY_EVERY = 50;   // ms between attempts
var MAX_TRIES = 20;     // gives up after ~1 s

var tries = 0;
var initTask = new Task(tryInit, this);

function loadbang() {
    tries = 0;
    initTask.cancel();
    initTask.schedule(INIT_DELAY);
}

function tryInit() {
    if (!box) setup();
    if (!box) return;                       // not inside a bpatcher

    var rects = readRects();
    if (rects) {
        outlet(0, ["loadbang"]);
        for (var i = 0; i < attrs.length; i++) {
            outlet(0, [attrs[i]].concat(rects[i]));
        }
        return;                             // done, no more retries
    }
    if (++tries < MAX_TRIES) {
        initTask.schedule(RETRY_EVERY);
    } else {
        post("bpresize: could not read bpatcher rect at load\n");
    }
}

// returns [[x,y,w,h], [x,y,w,h]] or null if not ready yet
function readRects() {
    var out = [];
    for (var i = 0; i < attrs.length; i++) {
        var v = toArray(box.getboxattr(attrs[i]));
        if (v.length !== 4 || typeof v[0] !== "number") return null;
        out.push(v);
    }
    return out;
}

// --- listeners for live resizing (unchanged behaviour) ---
function setup() {
    listeners = [];
    box = this.patcher.box;
    if (!box) {
        post("bpresize: not inside a bpatcher/subpatcher\n");
        return;
    }
    for (var i = 0; i < attrs.length; i++) {
        listeners.push(new MaxobjListener(box, attrs[i], makeCallback(attrs[i])));
    }
}

function makeCallback(name) {
    return function (data) {
        outlet(0, [name].concat(toArray(data.value)));
    };
}

// re-query on demand
function bang() {
    if (!box) setup();
    if (!box) return;
    var rects = readRects();
    if (rects) for (var i = 0; i < attrs.length; i++)
        outlet(0, [attrs[i]].concat(rects[i]));
}

function toArray(v) {
    var a = [];
    if (v == null) return a;
    if (typeof v === "object" && typeof v.length === "number") {
        for (var i = 0; i < v.length; i++) a.push(v[i]);
    } else {
        a.push(v);
    }
    return a;
}