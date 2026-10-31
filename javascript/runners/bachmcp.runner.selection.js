/*
bachmcp.runner.selection.js
---------------------------
The selection, as the selector and the transformer runners share it. A score
says which of its notes are selected in a slot named "selected" (1 selected, 0
not), declared in its slotinfo; the selector writes that slot in the roll, the
runners read it (process_only_selection 1). Notes are addressed as bach addresses
them: [voice, chord, note], 1-based.

    SLOT_NAME                        "selected"
    selectionSlot(score)             the number of the slot named "selected", or null
    isSelected(note, slot)           the note's flag in that slot is 1
    split(score, slot)               {picked, rest, map}: two scores, the selected notes and the others;
                                     map: "v c n" in picked -> that note's address in score
    merge(rest, result)              the notes of both in one score, chords in onset order
    only(score, addresses, slot)     a score of the notes at those addresses, the slot declared and each flagged 1
    mark(score, addresses, slot)     the whole score, the slot declared and every note flagged 1 or 0
    allAddresses(score)              every note's address
    bracket(list)                    an llll as Max atoms: [[1, 2, 3]] -> "[", "[", 1, 2, 3, "]", "]"
*/
"use strict";

const SLOT_NAME = "selected";

function copy(x) {
  return JSON.parse(JSON.stringify(x));
}

function selectionSlot(score) {
  const info = (score && score.header && score.header.slotinfo) || {};
  for (const key of Object.keys(info)) {
    const name = info[key] && info[key].name;
    if ((Array.isArray(name) ? name[0] : name) === SLOT_NAME) return Number(key);
  }
  return null;
}

function isSelected(note, slot) {
  const content = note && note.slots && note.slots[String(slot)];
  return Number(Array.isArray(content) ? content[0] : content) === 1;
}

/** The score cut in two by the slot: same header and voices, the notes shared out (empty chords dropped). */
function split(score, slot) {
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
        if (!isSelected(n, slot)) return;
        map[`${vi + 1} ${pv.chords.length + 1} ${yes.length + 1}`] = [vi + 1, ci + 1, ni + 1];
        yes.push(n);
      });
      const no = notes.filter((n) => !isSelected(n, slot));
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

/** The notes at those addresses, in a score with the source's header and voices; flagged 1 in `slot` if given. */
function only(score, addresses, slot) {
  if (!slot) {
    const keep = new Set(addresses.map((a) => a.join(" ")));
    const out = copy(score);
    out.voices.forEach((v, vi) => {
      v.chords = ((v && v.chords) || []).map((c, ci) => {
        c.notes = (c.notes || []).filter((n, ni) => keep.has(`${vi + 1} ${ci + 1} ${ni + 1}`));
        return c;
      }).filter((c) => c.notes.length);
    });
    return out;
  }
  // declared and flagged as mark does, then only the notes flagged 1
  const out = mark(score, addresses, slot);
  for (const v of out.voices) {
    if (!v) continue;
    v.chords = (v.chords || []).map((c) => Object.assign(c, { notes: (c.notes || []).filter((n) => isSelected(n, slot)) }))
      .filter((c) => c.notes.length);
  }
  return out;
}

/** The slot's slotinfo (named "selected", an int 0..1) and every note's flag: 1 at those addresses, else 0. */
function mark(score, addresses, slot) {
  const keep = new Set(addresses.map((a) => a.join(" ")));
  const out = copy(score);
  out.header = out.header || {};
  out.header.slotinfo = out.header.slotinfo || {};
  out.header.slotinfo[String(slot)] = Object.assign(out.header.slotinfo[String(slot)] || {},
    { name: [SLOT_NAME], type: ["int"], range: [0, 1], default: [0] });
  out.voices.forEach((v, vi) => ((v && v.chords) || []).forEach((c, ci) => ((c && c.notes) || []).forEach((n, ni) => {
    n.slots = Object.assign(n.slots || {}, { [String(slot)]: [keep.has(`${vi + 1} ${ci + 1} ${ni + 1}`) ? 1 : 0] });
  })));
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

module.exports = { SLOT_NAME, selectionSlot, isSelected, split, merge, only, mark, allAddresses, bracket };
