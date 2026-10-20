/*
bach.mcp.score.js
-----------------
JSON score <-> bach.roll llll, for Max (v8) and Node. A port of
py/bach_mcp/translate.py: same rules, same output, same error messages (tests
compare the two on the same scores).

The JSON score is bach.roll's gathered syntax with named fields:
    {"voices": [{"name", "clef", "chords": [{"onset", "dyn", "art", "text", "lyric",
                                              "notes": [{"pitch", "dur", "vel", "gliss", "head"}]}]}],
     "markers": [{"onset", "name"}]}
Units, always: onset and dur in milliseconds, pitch in midicents (6000 = middle C).
*/
"use strict";

const DEFAULT_VELOCITY = 80;
const MAX_NOTES = 20000;
const MAX_CENTS = 12700;

const CLEFS = [
  "G", "F", "FG", "FGG", "FFG", "FFGG", "G8va", "G15ma", "G8vb", "G15mb",
  "F8va", "F15ma", "F8vb", "F15mb", "Soprano", "Mezzo", "Alto", "Tenor",
  "Barytone", "Percussion", "None",
];
const CLEF_ALIASES = { treble: "G", bass: "F", piano: "FG", grand: "FG", baritone: "Barytone" };

const DYNAMIC_VELOCITY = {
  ppppp: 8, pppp: 15, ppp: 25, pp: 40, p: 55, mp: 70,
  mf: 85, f: 100, ff: 112, fff: 120, ffff: 127, fffff: 127,
  sfz: 115, sffz: 120, sf: 110, fz: 110, rf: 105, rfz: 105, o: 1,
};

// [JSON name, bach name, other spellings accepted on input or found in a dump]
const ARTICULATION_TABLE = [
  ["staccato", "staccato", "stacc"],
  ["staccatissimo", "staccatissimo", "staccmo"],
  ["accent", "accent", "acc"],
  ["tenuto", "portato", "port por ten"],
  ["marcato", "martellato", "mart"],
  ["fermata", "fermata", "ferm corona"],
  ["trill", "trill", "tr"],
  ["trill#", "trill#", "tr#"],
  ["trillb", "trillb", "trb"],
  ["trillx", "trillx", "trx"],
  ["trillbb", "trillbb", "trbb"],
  ["tremolo", "tremolo3", "trem trem3"],
  ["tremolo2", "tremolo2", "trem2"],
  ["tremolo1", "tremolo1", "trem1"],
  ["upbow", "upbowing", "ubow"],
  ["downbow", "downbowing", "dbow"],
  ["harmonic", "harmonic", "harm"],
  ["gruppetto", "gruppetto", "grupp turn"],
  ["mordent", "upmordent", "umord mord"],
  ["downmordent", "downmordent", "dmord"],
  ["doublemordent", "doublemordent", "mmord"],
  ["lefthandpizzicato", "lefthandpizzicato", "lhpizz lhpiz"],
  ["accentstaccato", "accentstaccato", "accstacc staccatoaccent staccacc"],
  ["accenttenuto", "accentportato", "accport portatoaccent portacc poracc accpor"],
  ["tenutostaccato", "portatostaccato", "portstacc staccatoportato staccport porstacc staccpor"],
  ["marcatostaccato", "martellatostaccato", "martstacc staccatomartellato staccmart"],
];
const ARTICULATIONS = {};       // any accepted spelling -> bach name
const ARTICULATION_NAMES = {};  // any bach spelling -> JSON name
for (const [json, bach, others] of ARTICULATION_TABLE) {
  for (const key of [json, bach, ...others.split(" ")]) {
    ARTICULATIONS[key] = bach;
    ARTICULATION_NAMES[key] = json;
  }
}

const NOTEHEADS = [
  "default", "doublewhole", "whole", "white", "black", "diamond", "cross", "plus",
  "none", "accent", "blacksquare", "whitesquare", "square", "blacktriangle",
  "whitetriangle", "triangle", "blackrhombus", "whiterhombus", "rhombus",
];
const NOTEHEAD_ALIASES = {
  normal: "default", half: "white", quarter: "black", x: "cross",
  diam: "diamond", harmonic: "diamond", invisible: "none", hidden: "none",
  blacksq: "blacksquare", bsquare: "blacksquare",
  whitesq: "whitesquare", wsquare: "whitesquare",
  blacktri: "blacktriangle", btri: "blacktriangle", btriangle: "blacktriangle",
  whitetri: "whitetriangle", wtri: "whitetriangle", wtriangle: "whitetriangle",
  blackrh: "blackrhombus", brhombus: "blackrhombus",
  whiterh: "whiterhombus", wrhombus: "whiterhombus",
};

// Slots that every new bach.roll links to notation by default.
const SLOT_DYNAMICS = 20, SLOT_LYRICS = 21, SLOT_ARTICULATIONS = 22, SLOT_NOTEHEAD = 23, SLOT_ANNOTATION = 24;
const SLOT_NAMES = {
  dynamics: SLOT_DYNAMICS, lyrics: SLOT_LYRICS, articulations: SLOT_ARTICULATIONS,
  notehead: SLOT_NOTEHEAD, noteheads: SLOT_NOTEHEAD, annotation: SLOT_ANNOTATION,
};

// Forgiving key aliases: small models drift between these spellings.
const CHORD_ALIASES = {
  t: "onset", time: "onset", start: "onset", onset_ms: "onset",
  dynamic: "dyn", dynamics: "dyn",
  articulation: "art", articulations: "art",
  annotation: "text", lyrics: "lyric",
};
const NOTE_ALIASES = {
  cents: "pitch", midicents: "pitch",
  duration: "dur", length: "dur", duration_ms: "dur",
  velocity: "vel",
  glissando: "gliss", breakpoints: "gliss",
  notehead: "head",
};
const CHORD_KEYS = ["onset", "notes", "dyn", "art", "text", "lyric"];
const NOTE_KEYS = ["pitch", "dur", "vel", "gliss", "head"];

class ScoreError extends Error {
  constructor(message) {
    super(message);
    this.name = "ScoreError";
  }
}

// ── Numbers and text ────────────────────────────────────────────────────── //

function isNumber(x) {
  return typeof x === "number" && Number.isFinite(x);
}

function fmt(x) {
  if (Number.isInteger(x)) return String(x === 0 ? 0 : x);
  const s = x.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  return s === "-0" ? "0" : s;
}

function tidy(x, digits = 3) {
  const r = Number(Number(x).toFixed(digits));
  return r === 0 ? 0 : r;
}

function repr(value) {
  if (typeof value === "string") return `'${value}'`;
  if (value === null || value === undefined) return "None";
  if (value === true) return "True";
  if (value === false) return "False";
  if (typeof value === "number") return String(value);
  try {
    return JSON.stringify(value);
  } catch (e) {
    return String(value);
  }
}

// ── JSON -> canonical score ─────────────────────────────────────────────── //

function num(value, what, where, minimum) {
  if (typeof value === "string") {
    const t = value.trim();
    if (t !== "" && !Number.isNaN(Number(t))) value = Number(t);
  }
  if (!isNumber(value)) {
    throw new ScoreError(`${where}: "${what}" must be a number, got ${repr(value)}`);
  }
  if (minimum !== undefined && value < minimum) {
    throw new ScoreError(`${where}: "${what}" must be >= ${fmt(minimum)}, got ${value}`);
  }
  return value;
}

function pitchOf(value, where) {
  let cents;
  try {
    cents = num(value, "pitch", where);
  } catch (e) {
    throw new ScoreError(
      `${where}: invalid pitch ${repr(value)}. Pitch is a number in midicents: ` +
      "6000 = middle C, 100 = one semitone"
    );
  }
  if (cents >= 0 && cents <= 127) {
    throw new ScoreError(
      `${where}: pitch ${fmt(cents)} looks like a MIDI note number. Pitch is in midicents: ` +
      `6000 = middle C, 100 = one semitone (MIDI ${fmt(cents)} is ${fmt(cents * 100)})`
    );
  }
  if (!(cents >= 0 && cents <= MAX_CENTS)) {
    throw new ScoreError(`${where}: pitch ${fmt(cents)} is out of range (midicents, 0-${MAX_CENTS}; 6000 = middle C)`);
  }
  return tidy(cents);
}

// bach's plain dynamics syntax: markings, hairpins (< > << >> = _), the empty mark |,
// free words ("cresc", "sub."), positions 0..1 and breakpoint anchors (@1).
const DYN_HAIRPINS = ["<", ">", "<<", ">>", "=", "_"];
const DYN_TOKEN = /<<|>>|[<>=_|]|@-?\d+|\d*\.\d+|\d+|[A-Za-z][A-Za-z.]*/g;
const DYN_WORD = /^(?:[A-Za-z][A-Za-z.]*|\|)$/;

function dynamicOf(value, where) {
  const s = String(value).split(/\s+/).filter(Boolean).join(" ");
  if (!s || s.replace(DYN_TOKEN, "").trim()) {
    throw new ScoreError(
      `${where}: invalid dynamic ${repr(value)}. Use pp p mp mf f ff sfz, ` +
      "optionally followed by < (crescendo) or > (diminuendo), e.g. \"p<\""
    );
  }
  return s;
}

/** Velocity implied by the first marking of a dynamic, or null if it has none. */
function dynamicVelocity(dyn) {
  const m = /[A-Za-z]+/.exec(dyn);
  const mark = m ? m[0].toLowerCase() : "";
  if (Object.prototype.hasOwnProperty.call(DYNAMIC_VELOCITY, mark)) return DYNAMIC_VELOCITY[mark];
  if (mark.startsWith("sf")) return DYNAMIC_VELOCITY.sf;
  const lead = /^(f+|p+)/.exec(mark); // "fp", "ffmp": the attack counts
  if (lead && /^[fpm]+$/.test(mark)) {
    const run = lead[0];
    return Object.prototype.hasOwnProperty.call(DYNAMIC_VELOCITY, run)
      ? DYNAMIC_VELOCITY[run]
      : (run[0] === "f" ? 127 : 8);
  }
  return null;
}

function articulationsOf(value, where) {
  const items = Array.isArray(value) ? value : String(value).replace(/,/g, " ").split(/\s+/).filter(Boolean);
  const out = [];
  for (const item of items) {
    const key = String(item).trim().toLowerCase();
    if (!Object.prototype.hasOwnProperty.call(ARTICULATIONS, key)) {
      const allowed = "staccato staccatissimo accent tenuto marcato fermata trill tremolo " +
        "upbow downbow harmonic mordent gruppetto";
      throw new ScoreError(`${where}: unknown articulation ${repr(item)}. Allowed: ${allowed}`);
    }
    if (!out.includes(ARTICULATIONS[key])) out.push(ARTICULATIONS[key]);
  }
  return out;
}

/** gliss -> bach breakpoints [[x, delta_cents, slope]] ending at x = 1. */
function glissOf(value, where) {
  if (isNumber(value)) return [[1, value, 0]];
  if (Array.isArray(value) && value.length) {
    const points = [];
    let valid = true;
    for (const p of value) {
      if (!(Array.isArray(p) && (p.length === 2 || p.length === 3))) {
        valid = false;
        break;
      }
      const slope = p.length === 3 ? num(p[2], "gliss slope", where) : 0;
      points.push([num(p[0], "gliss position", where, 0), num(p[1], "gliss midicents", where),
        Math.max(-1, Math.min(1, slope))]);
    }
    if (valid) {
      points.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
      if (points[points.length - 1][0] !== 1) {
        throw new ScoreError(`${where}: the last gliss point must be at position 1 (the end of the note)`);
      }
      return points.filter((p) => p[0] > 0);
    }
  }
  throw new ScoreError(
    `${where}: "gliss" must be a number of midicents (e.g. 200 or -1200) or a list of ` +
    "[position 0..1, midicents] points ending at position 1"
  );
}

function cleanName(name) {
  return String(name).trim().replace(/[^\p{L}\p{N}_#.+-]+/gu, "_").replace(/^_+|_+$/g, "");
}

/** Free text for a text slot: drop what would break an llll or a Max message. */
function cleanText(value) {
  return String(value).replace(/[^\p{L}\p{N}_ .+\-#!?'/:%&*=<>~^]/gu, " ").split(/\s+/).filter(Boolean).join(" ");
}

// Usual clef per instrument, matched on the voice name when no clef is given.
const INSTRUMENT_CLEFS = [
  ["FG", ["piano", "harp", "celesta", "organ", "harpsichord", "marimba", "accordion", "keyboard"]],
  ["Alto", ["viola"]],
  ["F", ["cello", "violoncello", "bass", "bassoon", "trombone", "tuba", "timpani", "baritone"]],
  ["Percussion", ["percussion", "drum", "cymbal", "woodblock"]],
  ["G", ["violin", "flute", "piccolo", "oboe", "clarinet", "trumpet", "horn", "soprano",
    "alto", "vibraphone", "glockenspiel", "xylophone", "guitar"]],
];

function clefForName(name) {
  const key = name.toLowerCase();
  for (const [clef, words] of INSTRUMENT_CLEFS) {
    if (words.some((w) => key.includes(w))) return clef;
  }
  return "";
}

function autoClef(cents) {
  if (!cents.length) return "G";
  const lo = Math.min(...cents), hi = Math.max(...cents);
  if (lo < 4800 && hi > 7200) return "FG";
  const sorted = cents.slice().sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)] >= 5700 ? "G" : "F";
}

/** Apply key aliases and reject keys that do not belong at this level. */
function keysOf(raw, aliases, allowed, elsewhere, where, kind) {
  const item = {};
  for (const [k, v] of Object.entries(raw)) item[Object.prototype.hasOwnProperty.call(aliases, k) ? aliases[k] : k] = v;
  for (const key of Object.keys(item)) {
    if (allowed.includes(key)) continue;
    if (elsewhere.includes(key)) {
      const owner = kind === "chord" ? "note" : "chord";
      const place = kind === "chord" ? "inside \"notes\"" : "next to \"onset\"";
      throw new ScoreError(`${where}: "${key}" belongs to the ${owner}, not to the ${kind}. Put it ${place}`);
    }
    throw new ScoreError(`${where}: unknown key "${key}". A ${kind} has: ${allowed.join(", ")}`);
  }
  return item;
}

function isObject(x) {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

function given(x) {
  return x !== undefined && x !== null;
}

function noteOf(raw, where) {
  if (!isObject(raw)) throw new ScoreError(`${where}: must be an object like {"pitch": 6000, "dur": 500}`);
  const n = keysOf(raw, NOTE_ALIASES, NOTE_KEYS, CHORD_KEYS.concat(Object.keys(CHORD_ALIASES)), where, "note");
  if (!given(n.pitch)) throw new ScoreError(`${where}: "pitch" is required, in midicents (6000 = middle C)`);
  if (!given(n.dur)) throw new ScoreError(`${where}: "dur" is required: the duration in milliseconds`);
  const note = { pitch: pitchOf(n.pitch, where) };
  note.dur = num(n.dur, "dur", where);
  if (note.dur <= 0) throw new ScoreError(`${where}: "dur" must be > 0 (milliseconds), got ${fmt(note.dur)}`);
  // null = filled from the prevailing dynamic once the chords are in time order.
  note.vel = given(n.vel) ? Math.min(127, Math.max(1, Math.round(num(n.vel, "vel", where)))) : null;
  if (given(n.gliss) && n.gliss !== 0 && !(Array.isArray(n.gliss) && !n.gliss.length)) {
    note.gliss = glissOf(n.gliss, where);
  }
  if (n.head) {
    let head = String(n.head).trim().toLowerCase();
    head = NOTEHEAD_ALIASES[head] || head;
    if (!NOTEHEADS.includes(head)) {
      throw new ScoreError(`${where}: unknown notehead ${repr(n.head)}. Allowed: ${NOTEHEADS.join(" ")}`);
    }
    if (head !== "default") note.head = head;
  }
  return note;
}

function chordOf(raw, where) {
  const example = "{\"onset\": 0, \"notes\": [{\"pitch\": 6000, \"dur\": 500}]}";
  if (!isObject(raw)) throw new ScoreError(`${where}: must be an object like ${example}`);
  const c = keysOf(raw, CHORD_ALIASES, CHORD_KEYS, NOTE_KEYS.concat(Object.keys(NOTE_ALIASES)), where, "chord");
  if (!given(c.onset)) throw new ScoreError(`${where}: "onset" is required: when the chord starts, in milliseconds`);
  const chord = { onset: num(c.onset, "onset", where, 0) };
  if (c.dyn) chord.dyn = dynamicOf(c.dyn, where);
  if (c.art && !(Array.isArray(c.art) && !c.art.length)) chord.art = articulationsOf(c.art, where);
  for (const key of ["text", "lyric"]) {
    if (c[key] && cleanText(c[key])) chord[key] = cleanText(c[key]);
  }
  const notes = c.notes;
  if (!Array.isArray(notes) || !notes.length) {
    throw new ScoreError(`${where}: "notes" must be a non-empty list, like ${example}`);
  }
  chord.notes = notes.map((n, i) => noteOf(n, `${where}, note ${i + 1}`));
  return chord;
}

/**
 * Validate a JSON score and return it in canonical form: chords in time order,
 * every note with a velocity, every voice with a clef, articulations as bach names.
 */
function normalizeScore(score) {
  const example = "{\"voices\": [{\"name\": \"Flute\", \"chords\": [{\"onset\": 0, \"notes\": [{\"pitch\": 6000, \"dur\": 500}]}]}]}";
  if (isObject(score) && isObject(score.score)) score = score.score;
  if (!isObject(score)) throw new ScoreError(`score must be a JSON object like ${example}`);
  const voicesIn = score.voices;
  if (!Array.isArray(voicesIn) || !voicesIn.length) {
    throw new ScoreError(`score needs "voices": a non-empty list, like ${example}`);
  }

  let total = 0;
  const voices = [];
  voicesIn.forEach((v, index) => {
    const vi = index + 1;
    if (!isObject(v)) throw new ScoreError(`voice ${vi}: must be an object like {"name": "Flute", "chords": [...]}`);
    if (!("chords" in v) && "notes" in v) {
      throw new ScoreError(
        `voice ${vi}: a voice holds "chords", and each chord holds its notes: ` +
        "{\"onset\": 0, \"notes\": [{\"pitch\": 6000, \"dur\": 500}]}"
      );
    }
    const name = v.name ? cleanName(v.name) : "";
    let clef = "";
    if (v.clef) {
      const want = String(v.clef).trim();
      clef = CLEFS.find((c) => c.toLowerCase() === want.toLowerCase()) || CLEF_ALIASES[want.toLowerCase()];
      if (!clef) throw new ScoreError(`voice ${vi}: unknown clef ${repr(want)}. Allowed: ${CLEFS.join(" ")}`);
    }
    const chordsIn = "chords" in v ? v.chords : [];
    if (!Array.isArray(chordsIn)) throw new ScoreError(`voice ${vi}: "chords" must be a list`);
    const chords = chordsIn.map((c, ci) => chordOf(c, `voice ${vi}, chord ${ci + 1}`));
    chords.sort((a, b) => a.onset - b.onset);

    // A dynamic holds until the next one, so it also sets the velocity of the notes that follow it.
    let prevailing = DEFAULT_VELOCITY;
    for (const chord of chords) {
      const implied = chord.dyn ? dynamicVelocity(chord.dyn) : null;
      if (implied !== null) prevailing = implied;
      for (const note of chord.notes) {
        if (note.vel === null) note.vel = prevailing;
      }
      total += chord.notes.length;
    }
    if (total > MAX_NOTES) throw new ScoreError(`score has more than ${MAX_NOTES} notes`);
    const cents = [];
    for (const c of chords) for (const n of c.notes) cents.push(n.pitch);
    voices.push({ name, clef: clef || clefForName(name) || autoClef(cents), chords });
  });

  const markers = [];
  const markersIn = score.markers || [];
  if (!Array.isArray(markersIn)) throw new ScoreError("\"markers\" must be a list like [{\"onset\": 0, \"name\": \"A\"}]");
  markersIn.forEach((raw, index) => {
    const mi = index + 1;
    if (!isObject(raw)) throw new ScoreError(`marker ${mi}: must be an object like {"onset": 0, "name": "A"}`);
    const m = {};
    for (const [k, val] of Object.entries(raw)) m[CHORD_ALIASES[k] || k] = val;
    if (!given(m.onset)) throw new ScoreError(`marker ${mi}: "onset" is required, in milliseconds`);
    const label = given(m.name) ? m.name : (given(m.label) ? m.label : "");
    markers.push({ onset: num(m.onset, "onset", `marker ${mi}`, 0), name: cleanName(label) });
  });
  markers.sort((a, b) => a.onset - b.onset);
  return { voices, markers };
}

// ── Canonical score -> llll ─────────────────────────────────────────────── //

/** One note in gathered syntax. `chord` is given for the note that carries the chord's slots. */
function noteLlll(note, chord) {
  const parts = [fmt(note.pitch), fmt(note.dur), String(note.vel)];
  if (note.gliss && note.gliss.length) {
    const points = note.gliss.map(([x, d, s]) => `[${fmt(x)} ${fmt(d)} ${fmt(s)}]`).join(" ");
    parts.push(`[breakpoints [0 0 0] ${points}]`);
  }
  chord = chord || {};
  const slots = [];
  if (chord.dyn) slots.push(`[${SLOT_DYNAMICS} ${chord.dyn}]`);
  if (chord.lyric) slots.push(`[${SLOT_LYRICS} ${chord.lyric}]`);
  if (chord.art && chord.art.length) slots.push(`[${SLOT_ARTICULATIONS} ${chord.art.join(" ")}]`);
  if (note.head) slots.push(`[${SLOT_NOTEHEAD} ${note.head}]`);
  if (chord.text) slots.push(`[${SLOT_ANNOTATION} ${chord.text}]`);
  if (slots.length) parts.push(`[slots ${slots.join(" ")}]`);
  return `[${parts.join(" ")}]`;
}

function chordLlll(chord) {
  const notes = chord.notes.map((n, i) => noteLlll(n, i === 0 ? chord : null)).join(" ");
  return `[${fmt(chord.onset)} ${notes}]`;
}

function voiceLlll(chords) {
  const body = chords.map(chordLlll).join(" ");
  return body ? `[${body}]` : "[]";
}

function bodyLlll(score) {
  return score.voices.map((v) => voiceLlll(v.chords));
}

function headerLlll(score) {
  const markers = (score.markers || []).map((m) => `[${fmt(m.onset)} ${m.name || "nil"}]`);
  return [
    `[clefs ${score.voices.map((v) => v.clef).join(" ")}]`,
    `[voicenames ${score.voices.map((v) => v.name || "nil").join(" ")}]`,
    markers.length ? `[markers ${markers.join(" ")}]` : "[markers]",
  ];
}

/**
 * A full `roll ...` message (replaces the score). The header always states clefs,
 * voice names and markers, so nothing of the previous score survives.
 */
function scoreToLlll(score, withHeader = true) {
  const parts = ["roll"];
  if (withHeader) parts.push(...headerLlll(score));
  return parts.concat(bodyLlll(score)).join(" ");
}

/** An `addchords ...` message (adds to the score). */
function scoreToAddchords(score) {
  return "addchords " + bodyLlll(score).join(" ");
}

/** The bach `tonedivision` needed to show the score's pitches: 2 semitones, 4 quarter-tones, 8 finer. */
function requiredTonedivision(score) {
  let need = 2;
  for (const v of score.voices) {
    for (const c of v.chords) {
      for (const n of c.notes) {
        const rest = tidy(((n.pitch % 100) + 100) % 100);
        if (rest === 50) need = Math.max(need, 4);
        else if (rest) return 8;
      }
    }
  }
  return need;
}

/** Every message to send to bach.roll for this canonical score, in order. */
function scoreMessages(score, add = false) {
  const messages = [];
  const division = requiredTonedivision(score);
  if (division > 2) messages.push(`tonedivision ${division}`); // must precede the notes
  if (!add) return messages.concat([scoreToLlll(score)]);
  if (score.voices.some((v) => v.chords.length)) messages.push(scoreToAddchords(score));
  for (const m of score.markers || []) messages.push(`addmarker ${fmt(m.onset)} ${m.name}`.trimEnd());
  return messages;
}

/**
 * The same messages split so that none is longer than `maxAtoms` atoms: a long
 * score becomes a `roll` with the header and empty voices, then `addchords`
 * messages that each carry a slice of every voice.
 */
function scoreMessagesChunked(score, add = false, maxAtoms = 30000) {
  const whole = scoreMessages(score, add);
  if (whole.every((m) => countAtoms(m) <= maxAtoms)) return whole;
  const out = whole.filter((m) => m.startsWith("tonedivision"));
  if (!add) {
    out.push(["roll", ...headerLlll(score), ...score.voices.map(() => "[]")].join(" "));
  }
  const slices = score.voices.map((v) => v.chords.map(chordLlll));
  const cursor = score.voices.map(() => 0);
  while (cursor.some((c, i) => c < slices[i].length)) {
    const voices = score.voices.map(() => []);
    let atoms = 1 + 2 * voices.length;
    let progressed = false;
    for (let i = 0; i < slices.length; i++) {
      while (cursor[i] < slices[i].length) {
        const size = countAtoms(slices[i][cursor[i]]);
        if (progressed && atoms + size > maxAtoms) break;
        voices[i].push(slices[i][cursor[i]]);
        cursor[i] += 1;
        atoms += size;
        progressed = true;
      }
    }
    out.push("addchords " + voices.map((cs) => (cs.length ? `[${cs.join(" ")}]` : "[]")).join(" "));
  }
  if (add) {
    for (const m of score.markers || []) out.push(`addmarker ${fmt(m.onset)} ${m.name}`.trimEnd());
  }
  return out;
}

/** Split an llll message into Max atoms: brackets as their own symbols, numbers as numbers. */
function toAtoms(message) {
  const atoms = [];
  for (const token of message.replace(/\[/g, " [ ").replace(/\]/g, " ] ").split(/\s+/)) {
    if (!token) continue;
    atoms.push(/^-?\d+(\.\d+)?$/.test(token) ? Number(token) : token);
  }
  return atoms;
}

function countAtoms(message) {
  return message.replace(/\[/g, " [ ").replace(/\]/g, " ] ").split(/\s+/).filter(Boolean).length;
}

// ── llll -> JSON ────────────────────────────────────────────────────────── //

const TOKEN = /"[^"]*"|[\[\]()]|[^\s\[\]()]+/g;
// A note bach holds as a pitch name rather than midicents, e.g. Db5 or C5+1/16t.
// bach's octave numbers put middle C at C5.
const BACH_PITCH = /^([A-Ga-g])([#bxqd^v]*)(-?\d+)(?:([+-])(\d+)\/(\d+)t)?$/;
const PITCH_CLASS = { C: 0, D: 200, E: 400, F: 500, G: 700, A: 900, B: 1100 };
const ACCIDENTAL = { "#": 100, b: -100, x: 200, q: 50, d: -50, "^": 25, v: -25 };

/** Midicents of a bach pitch name as it may appear in a dump (C5 = middle C = 6000). */
function bachPitchToCents(token) {
  const m = BACH_PITCH.exec(token);
  if (!m) return null;
  const [, letter, accs, octave, sign, numr, den] = m;
  let cents = parseInt(octave, 10) * 1200 + PITCH_CLASS[letter.toUpperCase()];
  for (const a of accs) cents += ACCIDENTAL[a];
  if (sign) cents += (sign === "+" ? 1 : -1) * 200 * parseInt(numr, 10) / parseInt(den, 10);
  return cents;
}

function atomOf(token) {
  if (token.startsWith("\"")) return token.replace(/^"+|"+$/g, "");
  if (token.startsWith("`")) return token.slice(1); // bach's escape for symbols that look like numbers
  if (/^[+-]?\d+$/.test(token)) return parseInt(token, 10);
  if (/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(token)) return parseFloat(token);
  if (/^-?\d+\/\d+$/.test(token)) {
    const [a, b] = token.split("/");
    return parseInt(a, 10) / parseInt(b, 10);
  }
  return token;
}

/** Parse llll text (or a list of Max atoms) into nested arrays. Accepts [ ] and ( ). */
function parseLlll(text) {
  if (Array.isArray(text)) text = text.map(String).join(" ");
  const root = [];
  const stack = [root];
  for (const token of String(text).match(TOKEN) || []) {
    if (token === "[" || token === "(") {
      const fresh = [];
      stack[stack.length - 1].push(fresh);
      stack.push(fresh);
    } else if (token === "]" || token === ")") {
      if (stack.length === 1) throw new Error("unbalanced llll: unexpected closing bracket");
      stack.pop();
    } else {
      stack[stack.length - 1].push(atomOf(token));
    }
  }
  if (stack.length !== 1) throw new Error("unbalanced llll: missing closing bracket (truncated message?)");
  return root;
}

function flattenSymbols(items) {
  const out = [];
  for (const item of items) {
    if (Array.isArray(item)) out.push(...flattenSymbols(item));
    else if (item !== "nil" && item !== "null") out.push(String(item));
  }
  return out;
}

/** Join plain-syntax tokens, without spaces when that stays unambiguous ("p<", "f<fff>mp"). */
function plainDynamics(tokens) {
  let spaced = tokens.some((t) => !(DYN_WORD.test(t) || DYN_HAIRPINS.includes(t)));
  for (let i = 0; i + 1 < tokens.length && !spaced; i++) {
    spaced = DYN_WORD.test(tokens[i]) && DYN_WORD.test(tokens[i + 1]);
  }
  return tokens.join(spaced ? " " : "");
}

/** The content of a dynamics slot in bach's plain syntax, e.g. "p<" or "f<fff>mp". */
function dynamicsFromSlot(content) {
  if (!(content.length && content.every(Array.isArray))) return plainDynamics(flattenSymbols(content));
  const tokens = [];
  const items = content.filter((item) => item.length);
  items.forEach((item, index) => {
    const attach = item[0];
    const marking = item.length > 1 ? item[1] : [];
    const hairpin = item.length > 2 ? String(item[2]) : "=";
    let prefix = "";
    if (isNumber(attach)) prefix = fmt(attach);
    else if (Array.isArray(attach) && attach.length > 1 && attach[0] === "breakpoint") prefix = `@${attach[1]}`;
    else if (Array.isArray(attach) && attach.length && attach[0] === "manual") prefix = fmt(Number(attach[attach.length - 1]));
    const words = flattenSymbols(Array.isArray(marking) ? marking : [marking]);
    if (prefix) tokens.push(prefix);
    tokens.push(...(words.length ? words : (prefix ? [] : ["|"])));
    if (hairpin !== "=" || index < items.length - 1) tokens.push(hairpin);
  });
  return plainDynamics(tokens);
}

/** Breakpoints [x cents slope] -> "gliss": a number of midicents, or [[x, cents(, slope)]]. */
function glissFromBreakpoints(points) {
  points = points.filter((p) => Array.isArray(p) && p.length >= 2 && p[0] > 0);
  if (!points.some((p) => p[1] !== 0)) return null;
  const slope = (p) => (p.length > 2 && isNumber(p[2]) ? p[2] : 0);
  if (points.length === 1 && !slope(points[0])) return tidy(points[0][1]);
  return points.map((p) => [tidy(p[0], 4), tidy(p[1])].concat(slope(p) ? [tidy(slope(p), 4)] : []));
}

/** Decode one gathered-syntax chord [onset NOTE NOTE ... flag] into a JSON chord. */
function decodeChord(chord) {
  const marks = {};
  const arts = [];
  const notes = [];
  for (const item of chord.slice(1)) {
    if (!Array.isArray(item) || item.length < 3) continue;
    const [rawPitch, dur, vel] = item;
    if (!(isNumber(dur) && isNumber(vel))) continue; // a chord spec such as [name john paul]
    const cents = isNumber(rawPitch) ? rawPitch : bachPitchToCents(String(rawPitch));
    if (cents === null) continue;
    const note = { pitch: tidy(cents), dur: tidy(dur), vel: Math.trunc(vel) };
    for (const spec of item.slice(3)) {
      if (!Array.isArray(spec) || !spec.length) continue;
      if (spec[0] === "breakpoints") {
        const gliss = glissFromBreakpoints(spec.slice(1));
        if (gliss !== null) note.gliss = gliss;
      } else if (spec[0] === "slots") {
        for (const slot of spec.slice(1)) {
          if (!Array.isArray(slot) || slot.length < 2) continue;
          const sid = Object.prototype.hasOwnProperty.call(SLOT_NAMES, slot[0]) ? SLOT_NAMES[slot[0]] : slot[0];
          const content = slot.slice(1);
          if (sid === SLOT_NOTEHEAD) {
            const head = flattenSymbols(content);
            if (head.length && head[0] !== "default") note.head = NOTEHEAD_ALIASES[head[0]] || head[0];
          } else if (sid === SLOT_ARTICULATIONS) {
            for (let art of flattenSymbols(content)) {
              art = ARTICULATION_NAMES[art] || art;
              if (!arts.includes(art)) arts.push(art);
            }
          } else if (sid === SLOT_DYNAMICS) {
            if (!("dyn" in marks)) marks.dyn = dynamicsFromSlot(content);
          } else if (sid === SLOT_ANNOTATION || sid === SLOT_LYRICS) {
            const key = sid === SLOT_ANNOTATION ? "text" : "lyric";
            if (!(key in marks)) marks[key] = flattenSymbols(content).join(" ");
          }
        }
      }
    }
    notes.push(note);
  }
  if (!notes.length) return null;
  const out = { onset: tidy(chord[0]) };
  if (marks.dyn) out.dyn = marks.dyn;
  if (arts.length) out.art = arts.length === 1 ? arts[0] : arts;
  for (const k of ["text", "lyric"]) if (marks[k]) out[k] = marks[k];
  out.notes = notes;
  return out;
}

/** Decode a bach.roll dump (gathered syntax, as text or Max atoms) into a JSON score. */
function llllToScore(text) {
  let items = parseLlll(text);
  if (items.length && items[0] === "roll") items = items.slice(1);

  const header = {};
  const voicesRaw = [];
  for (const item of items) {
    if (!Array.isArray(item)) continue;
    if (item.length && typeof item[0] === "string") header[item[0]] = item.slice(1);
    else voicesRaw.push(item);
  }

  const clefs = header.clefs || [];
  const names = header.voicenames || [];
  const voices = voicesRaw.map((voice, vi) => {
    const v = { voice: vi + 1 };
    const name = names[vi];
    if (vi < names.length && !["nil", "null"].includes(name) && !(Array.isArray(name) && !name.length) && given(name)) {
      v.name = Array.isArray(name) ? name.map(String).join(" ") : String(name);
    }
    if (vi < clefs.length) v.clef = String(clefs[vi]);
    v.chords = [];
    for (const chord of voice) {
      if (Array.isArray(chord) && chord.length && isNumber(chord[0])) {
        const decoded = decodeChord(chord);
        if (decoded) v.chords.push(decoded);
      }
    }
    return v;
  });

  const score = { voices };
  const markers = [];
  for (const marker of header.markers || []) {
    if (Array.isArray(marker) && marker.length && isNumber(marker[0])) {
      markers.push({ onset: tidy(marker[0]), name: flattenSymbols(marker.slice(1, 2)).join(" ") });
    }
  }
  if (markers.length) score.markers = markers;
  return score;
}

// ── Summaries ───────────────────────────────────────────────────────────── //

function countNotes(score) {
  let n = 0;
  for (const v of score.voices) for (const c of v.chords || []) n += c.notes.length;
  return n;
}

/** One compact line per voice describing a canonical score, in bach's units. */
function summarize(score, preview = 8) {
  const lines = [];
  score.voices.forEach((v, index) => {
    const chords = v.chords;
    const label = `voice ${index + 1}` + (v.name ? ` (${v.name})` : "") + ` clef ${v.clef}`;
    if (!chords.length) {
      lines.push(`${label}: empty`);
      return;
    }
    const cents = [];
    let end = -Infinity;
    for (const c of chords) {
      for (const n of c.notes) cents.push(n.pitch);
      end = Math.max(end, c.onset + Math.max(...c.notes.map((n) => n.dur)));
    }
    const shown = chords.slice(0, preview).map((c) => `${c.notes.map((n) => fmt(n.pitch)).join("+")}@${fmt(c.onset)}`);
    const more = chords.length > preview ? ` ... +${chords.length - preview} more` : "";
    lines.push(
      `${label}: ${cents.length} notes in ${chords.length} chords, ${fmt(chords[0].onset)}-${fmt(end)} ms, ` +
      `pitch ${fmt(Math.min(...cents))}-${fmt(Math.max(...cents))}. Starts (pitch@onset): ${shown.join(" ")}${more}`
    );
  });
  if (score.markers && score.markers.length) {
    lines.push("markers: " + score.markers.map((m) => `${m.name}@${fmt(m.onset)}`).join(" "));
  }
  return lines.join("\n");
}

module.exports = {
  ScoreError,
  DEFAULT_VELOCITY, MAX_NOTES, MAX_CENTS, CLEFS, NOTEHEADS, ARTICULATIONS,
  fmt, tidy,
  normalizeScore, dynamicVelocity, clefForName, autoClef,
  scoreToLlll, scoreToAddchords, requiredTonedivision, scoreMessages, scoreMessagesChunked,
  toAtoms, countAtoms,
  parseLlll, bachPitchToCents, llllToScore,
  countNotes, summarize,
};
