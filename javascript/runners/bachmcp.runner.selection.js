/*
bachmcp.runner.selection.js
---------------------------
The selection, as the selector and the transformer runners share it. A score
says which of its notes are selected in bach's own flags: bit 16 of the `flag`
of a note or of a chord (the flag sums 1 locked, 2 muted, 4 solo, 16 selected).
A note inherits from its chord: chord flag 16, note flag 0 -> the note is
selected. The selector writes the bit on notes only (and clears it on chords),
the runners read it (process_only_selection 1). Notes are addressed as bach
addresses them: [voice, chord, note], 1-based.

    SELECTED                         16, the bit
    isSelected(note, chord)          the note's flag or its chord's has the bit
    split(score)                     {picked, rest, map}: two scores, the selected notes and the others;
                                     map: "v c n" in picked -> that note's address in score
    merge(rest, result)              the notes of both in one score, chords in onset order
    only(score, addresses)           a score of the notes at those addresses, each flagged selected
    mark(score, addresses)           the whole score, the notes at those addresses flagged selected, no other
    allAddresses(score)              every note's address
    bracket(list)                    an llll as Max atoms: [[1, 2, 3]] -> "[", "[", 1, 2, 3, "]", "]"
*/
"use strict";

const SELECTED = 16;

function copy(x) {
  return JSON.parse(JSON.stringify(x));
}

function hasBit(item) {
  return ((Number(item && item.flag) || 0) & SELECTED) !== 0;
}

function isSelected(note, chord) {
  return hasBit(note) || hasBit(chord);
}

/** The score cut in two by the flags: same header and voices, the notes shared out (empty chords dropped). */
function split(score) {
  const picked = copy(score);
  const rest = copy(score);
  const map = {};
  picked.voices = [];
  rest.voices = [];
  (score.voices || []).forEach((v, vi) => {
    const pv = Object.assign(copy(v), { chords: [] });
    const rv = Object.assign(copy(v), { chords: [] });
    ((v && v.chords) || []).forEach((c, ci) => {
      const notes = (c && c.notes) || [];
      const yes = [];
      notes.forEach((n, ni) => {
        if (!isSelected(n, c)) return;
        map[`${vi + 1} ${pv.chords.length + 1} ${yes.length + 1}`] = [vi + 1, ci + 1, ni + 1];
        yes.push(n);
      });
      const no = notes.filter((n) => !isSelected(n, c));
      if (yes.length) pv.chords.push(Object.assign(copy(c), { notes: copy(yes) }));
      if (no.length) rv.chords.push(Object.assign(copy(c), { notes: copy(no) }));
    });
    picked.voices.push(pv);
    rest.voices.push(rv);
  });
  return { picked, rest, map };
}

/** rest's notes and result's, voice by voice, chords sorted by onset (rest's first at the same onset). */
function merge(rest, result) {
  const out = copy(rest);
  if (result.header) out.header = copy(result.header);
  const n = Math.max(out.voices.length, (result.voices || []).length);
  for (let i = 0; i < n; i++) {
    const r = (result.voices || [])[i];
    if (!out.voices[i]) {
      out.voices[i] = copy(r);
      continue;
    }
    if (!r) continue;
    const chords = out.voices[i].chords.concat(copy(r.chords || []));
    out.voices[i].chords = chords
      .map((c, k) => [c, k])
      .sort((a, b) => (a[0].onset || 0) - (b[0].onset || 0) || a[1] - b[1])
      .map((x) => x[0]);
  }
  return out;
}

function allAddresses(score) {
  const out = [];
  (score.voices || []).forEach((v, vi) => ((v && v.chords) || []).forEach((c, ci) =>
    ((c && c.notes) || []).forEach((n, ni) => out.push([vi + 1, ci + 1, ni + 1]))));
  return out;
}

/** The notes at those addresses, flagged selected, in a score with the source's header and voices. */
function only(score, addresses) {
  const out = mark(score, addresses);
  for (const v of out.voices) {
    if (!v) continue;
    v.chords = (v.chords || []).map((c) => Object.assign(c, { notes: (c.notes || []).filter((n) => hasBit(n)) }))
      .filter((c) => c.notes.length);
  }
  return out;
}

/** Every note's flag: the bit set at those addresses, cleared elsewhere; cleared on every chord. Other bits kept. */
function mark(score, addresses) {
  const keep = new Set(addresses.map((a) => a.join(" ")));
  const out = copy(score);
  (out.voices || []).forEach((v, vi) => ((v && v.chords) || []).forEach((c, ci) => {
    if (!c) return;
    c.flag = (Number(c.flag) || 0) & ~SELECTED;
    (c.notes || []).forEach((n, ni) => {
      const flag = (Number(n.flag) || 0) & ~SELECTED;
      n.flag = keep.has(`${vi + 1} ${ci + 1} ${ni + 1}`) ? flag | SELECTED : flag;
    });
  }));
  return out;
}

function bracket(list) {
  const out = [];
  for (const x of list) {
    if (Array.isArray(x)) out.push("[", ...bracket(x), "]");
    else out.push(x);
  }
  return out;
}

module.exports = { SELECTED, isSelected, split, merge, only, mark, allAddresses, bracket };
