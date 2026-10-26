/*
bachmcp.lib.gather.js
---------------------
Gathering music: its chords, notes and pitches in time order, its span, a time window.

Music here (x) is any of: a score {voices}, a voice {chords}, one chord, or an array
of chords. Pitches in midicents, times in milliseconds. The chords returned are the
score's own, not copies: a transformer reads copy(source) and changes what it finds.
*/
"use strict";

function isChord(x) {
  return x !== null && typeof x === "object" && typeof x.onset === "number" && Array.isArray(x.notes);
}

/** The chords of any music, in time order (all voices together for a score). */
function chordsOf(x) {
  let out;
  if (Array.isArray(x)) out = x.flatMap((item) => (isChord(item) ? [item] : chordsOf(item)));
  else if (isChord(x)) out = [x];
  else if (x && Array.isArray(x.voices)) out = x.voices.flatMap((v) => v.chords || []);
  else if (x && Array.isArray(x.chords)) out = x.chords.slice();
  else out = [];
  return out.sort((a, b) => a.onset - b.onset);
}

/** Every note of the music, in time order then low to high: {pitch, onset, dur, end, vel, note, chord}. */
function notesOf(x) {
  const out = [];
  for (const chord of chordsOf(x)) {
    for (const note of chord.notes) {
      out.push({ pitch: note.pitch, onset: chord.onset, dur: note.dur, end: chord.onset + note.dur,
                 vel: note.vel, note, chord });
    }
  }
  return out.sort((a, b) => a.onset - b.onset || a.pitch - b.pitch);
}

/** Every pitch of the music, in time order. */
function pitchesOf(x) {
  return notesOf(x).map((n) => n.pitch);
}

/** When a chord stops sounding: its onset plus its longest note. */
function chordEnd(chord) {
  return chord.onset + Math.max(0, ...chord.notes.map((n) => n.dur));
}

/** [start, end] of the music in milliseconds; [0, 0] when there is none. */
function span(x) {
  const chords = chordsOf(x);
  if (!chords.length) return [0, 0];
  return [chords[0].onset, Math.max(...chords.map(chordEnd))];
}

/** The chords whose onset is in [from, to). */
function between(x, from, to) {
  return chordsOf(x).filter((c) => c.onset >= from && c.onset < to);
}

/** The chords sounding at time t (started, not yet ended). */
function sounding(x, t) {
  return chordsOf(x).filter((c) => c.onset <= t && t < chordEnd(c));
}

module.exports = { chordsOf, notesOf, pitchesOf, chordEnd, span, between, sounding };
