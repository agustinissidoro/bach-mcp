/*
bachmcp.runner.type.transformer.js
----------------------------------
The transformer type: an algorithm that changes music already there, a file
that defines `function transform(source, p) { ... }`. Its source is
bachmcp.runner.source.js. The runner never feeds its own result back: what it
transforms is always a score that came in at the inlet, so that anything
(another algorithm, a hand edit in a roll) can act on the music between two
transformations. write_to_playground writes the result, not the source.

process_only_selection 1: the algorithm gets a score of the selected notes
only. With dump_replacesel 1 (default) its result goes out alone, without
header, as "addchords replacesel dictionary <name>": bach.roll replaces its
selection with it (the new notes stay selected, so the next run works on them).
With dump_replacesel 0 the other notes are put back unchanged around it and the
whole score goes out.
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
  const source = createSource(engine);
  let rest = null;  // process_only_selection 1: the notes left out of the run, put back after it
  let replacing = false;  // the last output was the result alone, for addchords replacesel

  return Object.assign({}, source.hooks, {
    name: "transformer",
    needs: "function transform(source, p) { ... }",
    messages: source.messages,
    source() {
      rest = null;
      const s = source.state;
      if (!engine.state.selectedOnly || !s.score) return s.score;
      const parts = sel.split(s.score);
      rest = parts.rest;
      return parts.picked;
    },
    output(score) {
      replacing = Boolean(rest) && engine.state.replaceSel;
      if (replacing) return { voices: score.voices || [] };  // addchords takes no header
      return rest ? sel.merge(rest, score) : score;
    },
    prefix: () => (replacing ? ["addchords", "replacesel"] : null),
  });
}

module.exports = { create };
