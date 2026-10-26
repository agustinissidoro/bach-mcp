/*
bachmcp.lib.build.js
--------------------
Making and handling scores, written directly in bachjson-complete
(bachjson-syntax-specification.md): what an algorithm builds is already the
score every object passes on, with nothing translated afterwards.

    const s = score();                      {header: {voicenames: []}, voices: []}
    const v = s.voice("Flute");             a voice, made on first use; its name in header.voicenames
    v.note(onset, pitch, dur, fields)       a chord of one note
    v.chord(onset, [pitch, ...], dur, fields)
    s.marker(onset, "A")                    a marker in header.markers

`fields` are the note's own bachjson-complete fields, given to every note of
the chord: vel (default 80), slots (by number: {20: ["p"], 22: ["staccato"]}),
breakpoints, name, flag. A pitch may also be a whole note object
{pitch, dur, vel, slots, ...}. note() and chord() return the chord, so its
notes can still be changed. copy() and eachNote() serve transformers.
*/
"use strict";

// Max finds a file by its name, on the search path; Node by where it is.
function need(name) {
  const places = ["", "./", "../", "../algorithmic_core_library/", "../runners/"];
  for (const place of places) {
    try {
      return require(place + name);
    } catch (e) {
      if (place === places[places.length - 1]) throw e;
    }
  }
}

const { isObject } = need("bachmcp.lib.base.js");

const DEFAULT_VELOCITY = 80;

/** One voice of the score: {chords, flag}, with methods to write into it. */
class Voice {
  constructor() {
    this.chords = [];
    this.flag = 0;
  }

  /** A chord of one note. Returns the chord. */
  note(onset, pitch, dur, fields) {
    return this.chord(onset, [pitch], dur, fields);
  }

  /** A chord: pitches is a list of midicents, or of note objects {pitch, dur, vel, slots, ...}. Returns the chord. */
  chord(onset, pitches, dur, fields) {
    const notes = pitches.map((p) => Object.assign({ pitch: p, dur, vel: DEFAULT_VELOCITY },
                                                   isObject(p) ? Object.assign({}, fields, p) : fields));
    for (const n of notes) {
      if (isObject(n.slots)) n.slots = JSON.parse(JSON.stringify(n.slots));  // each note its own slots
      if (n.flag === undefined) n.flag = 0;
    }
    const chord = { onset, notes, flag: 0 };
    this.chords.push(chord);
    return chord;
  }

  /** When the last note of this voice stops sounding, in milliseconds. */
  get end() {
    let end = 0;
    for (const c of this.chords) for (const n of c.notes) end = Math.max(end, c.onset + n.dur);
    return end;
  }
}

/** A score in bachjson-complete: {header, voices}. */
class Score {
  constructor() {
    this.header = { voicenames: [] };
    this.voices = [];
  }

  /** The voice with this name, made on first use. Voices appear top to bottom in creation order. */
  voice(name, clef) {
    const i = this.header.voicenames.findIndex((names) => names[0] === name);
    if (i >= 0) return this.voices[i];
    const v = new Voice();
    this.voices.push(v);
    this.header.voicenames.push(name === undefined || name === "" ? [] : [name]);
    if (clef || this.header.clefs) {
      this.header.clefs = this.header.clefs || this.voices.slice(0, -1).map(() => "G");
      this.header.clefs.push(clef || "G");
    }
    return v;
  }

  /** A marker at onset ms. */
  marker(onset, name, role = "none") {
    if (!this.header.markers) this.header.markers = [];
    this.header.markers.push({ onset, name: [name], role });
    return this;
  }

  get end() {
    return Math.max(0, ...this.voices.map((v) => v.end));
  }
}

function score() {
  return new Score();
}

/** A deep copy of a score, a voice, a chord or any JSON value. */
function copy(x) {
  return x === undefined ? undefined : JSON.parse(JSON.stringify(x));
}

/** Call fn(note, chord, voice) for every note of a score. */
function eachNote(target, fn) {
  for (const voice of target.voices || []) {
    for (const chord of voice.chords || []) {
      for (const note of chord.notes || []) fn(note, chord, voice);
    }
  }
  return target;
}

module.exports = { score, Score, Voice, copy, eachNote };
