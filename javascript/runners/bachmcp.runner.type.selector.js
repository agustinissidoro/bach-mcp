/*
bachmcp.runner.type.selector.js
-------------------------------
The selector type: an algorithm that picks notes of a score, a file that
defines `function select(source, p) { ... }` and returns the notes it picks
(the note objects of `source`, or their addresses [voice, chord, note],
1-based). Its source is bachmcp.runner.source.js. Selections are not
cumulative: each run replaces the previous one (involutive is ignored for now).

A run sends:
  outlet 0   the score, the selection written in bach's flags: bit 16 set on
             the `flag` of every selected note, cleared on the other notes and
             on every chord (other bits kept), so that a runner with
             process_only_selection 1 works on it:
               dump_selection_only 1  (default) only the selected notes
               dump_selection_only 0  the whole source
  outlet 1   then, to bach: clearselection, sel note [v c n] ...
             ("sel note", singular: bach's "sel notes" selects every note, whatever follows)

process_only_selection 1: it picks only among the notes already selected; its
picks are addressed in the whole score.

A selector may also write markers: what it puts in source.header.markers (the
library's timesig, barline, division ...) replaces the roll's markers:
  outlet 1   clearmarkers, addmarker <onset> [names] <role> [content] ...
and is in the score of outlet 0. The roll is read again at every run, so the
markers a run added are taken out of the next run's source: each run starts
from the roll's own markers, like the selection, and a run that writes none
removes the ones before.

Messages of its own: dump_selection (the selected notes as a score, out of
outlet 0), clear_selection. Its settings, dump_selection_only and involutive,
are the engine's (every runner takes them).
*/
"use strict";

// Max finds a file by its name, on the search path; Node by where it is.
function need(name) {
  const places = ["", "./", "../", "../runners/"];
  for (const place of places) {
    try {
      return require(place + name);
    } catch (e) {
      if (place === places[places.length - 1]) throw e;
    }
  }
}

const { createSource } = need("bachmcp.runner.source.js");
const sel = need("bachmcp.runner.selection.js");

function create(engine) {
  const { OUT, max } = engine;
  const selection = {
    map: null,           // process_only_selection: address in what the algorithm got -> in the source
    tracked: new Set(),  // "v c n" of what this runner selected
    commands: [],        // the last messages to bach, for repeat
    base: [],            // the markers of the source the last run got: the roll's own
    added: [],           // the markers the last run added to them, as JSON texts
    markers: null,       // the roll's markers after the last run, when a run has written any
  };

  /** The score without the markers the last run added: what the roll had by itself. */
  function ownMarkers(score) {
    const out = Object.assign({}, score);
    const all = score.header && Array.isArray(score.header.markers) ? score.header.markers : [];
    selection.base = all.filter((m) => !selection.added.includes(JSON.stringify(m)));
    if (all.length) out.header = Object.assign({}, score.header, { markers: selection.base });
    return out;
  }

  /** The run's markers in place of the roll's (null: it wrote none; then the ones a run added before go). */
  function applyMarkers(markers) {
    if (!markers && !selection.added.length) return [];
    const next = markers || selection.base;
    const before = selection.base.map((m) => JSON.stringify(m));
    selection.added = next.map((m) => JSON.stringify(m)).filter((m) => !before.includes(m));
    selection.markers = next;
    return [["clearmarkers"]].concat(next.map((m) => {
      const names = Array.isArray(m.name) ? m.name : (m.name === undefined ? [] : [m.name]);
      const content = Array.isArray(m.content) && m.content.length ? ["[", ...sel.bracket(m.content), "]"] : [];
      return ["addmarker", m.onset, "[", ...names, "]", m.role || "none", ...content];
    }));
  }
  const source = createSource(engine, {
    // a new source: forget what it no longer has
    onNewSource(score) {
      const present = new Set(sel.allAddresses(score).map((a) => a.join(" ")));
      for (const key of [...selection.tracked]) if (!present.has(key)) selection.tracked.delete(key);
    },
  });

  function trackedAddresses() {
    return [...selection.tracked].map((k) => k.split(" ").map(Number));
  }

  /** The score with every note flagged, out of outlet 0 (see dump_selection_only). */
  function sendMarked() {
    const score = source.state.score;
    if (!score) return;
    const make = engine.state.selectionOnly ? sel.only : sel.mark;
    const out = make(score, trackedAddresses());
    if (selection.markers) out.header = Object.assign({}, out.header, { markers: selection.markers });
    engine.sendScore(out);
  }

  function sendCommands() {
    for (const c of selection.commands) max.outlet(OUT.BACH, ...c);
  }

  /** The run's notes replace the selection: the score out, then clearselection and sel. */
  function apply(addresses, markers) {
    selection.tracked = new Set(addresses.map((a) => a.join(" ")));
    selection.commands = applyMarkers(markers).concat([["clearselection"]]);
    if (addresses.length) selection.commands.push(["sel", "note", ...sel.bracket(addresses)]);
    sendMarked();
    sendCommands();
  }

  const messages = Object.assign({}, source.messages, {
    dump_selection() {
      if (!source.state.score) return engine.refuse("dump_selection: there is no source yet");
      engine.sendScore(sel.only(source.state.score, trackedAddresses()));
      engine.state.changed = true;  // the last score sent is not a run's output any more
    },
    /** Nothing selected any more: the score (empty, or the source with no flag 16), then clearselection. */
    clear_selection() {
      selection.tracked.clear();
      selection.commands = [["clearselection"]];
      sendMarked();
      sendCommands();
      engine.state.changed = true;  // a bang selects again
    },
  });

  return Object.assign({}, source.hooks, {
    name: "selector",
    needs: "function select(source, p) { ... }",
    messages,
    source() {
      selection.map = null;
      const s = source.state;
      if (!s.score) return s.score;
      const score = ownMarkers(s.score);
      if (!engine.state.selectedOnly) return score;
      const parts = sel.split(score);
      selection.map = parts.map;
      return parts.picked;
    },
    ran(result) {
      const map = selection.map;
      apply(map ? result.selection.map((a) => map[a.join(" ")]) : result.selection, result.markers);
    },
    repeated: sendCommands,
  });
}

module.exports = { create };
