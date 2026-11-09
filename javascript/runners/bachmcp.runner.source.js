/*
bachmcp.runner.source.js
------------------------
The source: the score a transformer changes or a selector picks in, as both
types share it (bachmcp.runner.type.transformer.js, .selector.js). It arrives
at the inlet as `dictionary <name>` (from a roll through
bachmcp.translate @out json, or from another runner), in bachjson-complete,
and lives only in memory.

Every run that needs it goes: "dump" out of outlet 1 (BACH) to ask the roll
for its score, the score comes in, the run works on it. While the runner waits
it is "processing" (<name> processing 1, then 0, out of outlet 4); changes
meanwhile are kept, and the score that comes in runs with the latest values.
If nothing comes in within 3 seconds: <name> timeout 1, then processing 0.
What happens depends on the source mode:

  source_mode 1   non-destructive (default). Only the first run asks for the
                  score: it becomes the source, held, and every later run
                  starts again from it, without a dump. capture asks for a new
                  one. An input that arrives unasked becomes the source only
                  when there is none yet.
  source_mode 0   destructive. Every run asks for the score, so it works on
                  what the roll holds now. An input that arrives unasked is
                  kept as the source but never run on by itself (no loop
                  through a roll).

process_only_selection 1: the run sees only the selected notes (flag 16 on the
note or its chord, bachmcp.runner.selection.js); what the type does with the
others is its own (a transformer puts them back, a selector maps its picks
back to the whole score).

source_mode and process_only_selection are the engine's (engine.state.destructive,
.selectedOnly): every runner takes them, whatever its type, so this module only
reads them.

    const source = createSource(engine, {onNewSource})
    source.state         {score, from, open, processing}
    source.hooks         request, stale, setting, bypassed, deleted: for the type
    source.messages      dictionary, input, capture
*/
"use strict";

const PROCESSING_TIMEOUT_MS = 3000;

function countNotes(score) {
  let n = 0;
  for (const v of (score && score.voices) || []) for (const c of (v && v.chords) || []) n += ((c && c.notes) || []).length;
  return n;
}

function createSource(engine, options = {}) {
  const { OUT, max } = engine;
  const s = {
    score: null,
    from: "",              // "inlet"
    open: false,           // capture: the next input becomes the source
    processing: false,     // a dump went out, the score has not come in yet
  };

  /** No score answered the dump: stop waiting, so that the next change asks again. */
  const timeout = new max.Task(() => {
    if (!s.processing) return;
    engine.status("timeout", 1);
    setProcessing(false);
  });

  function setProcessing(on) {
    if (on) timeout.schedule(PROCESSING_TIMEOUT_MS);
    else timeout.cancel();
    if (s.processing === on) return;
    s.processing = on;
    engine.status("processing", on ? 1 : 0);
  }

  /** A run waits for the score: "dump" to the roll; the input that answers it becomes the source and runs. */
  function askForScore() {
    if (s.processing) return;  // already asked: the score runs with the latest values
    setProcessing(true);
    max.outlet(OUT.BACH, "dump");
  }

  function info() {
    return s.score ? { notes: countNotes(s.score), from: s.from } : { notes: 0, from: "" };
  }

  // The source's notes to the panel: commented out for now (too much information).
  function tellPanelSource() {
    // const i = info();
    // engine.tellPanel("source", i.notes, i.from || "none");
  }

  // ── Hooks, for the type ───────────────────────────────────────────────── //

  const destructive = () => engine.state.destructive;

  const hooks = {
    request() {
      if (s.score && !destructive()) return false;  // non-destructive: the held source
      askForScore();
      return true;
    },
    stale: destructive,                              // the roll may hold something else now
    setting(name) {
      if (name === "source_mode") setProcessing(false);
    },
    // spec: () => ({ source: info() }),  // commented out for now: the panel does not show the source
    bypassed(on) {
      if (on) setProcessing(false);
    },
    deleted(replaced) {
      if (replaced) setProcessing(false);  // the type changed while it waited: processing 0, as it said 1
      else timeout.cancel();               // the object goes: nothing more is said
    },
  };

  // ── Messages ──────────────────────────────────────────────────────────── //

  function input(what, name) {
    if (what === "clear") {
      s.score = null;
      s.from = "";
      engine.state.changed = true;
      tellPanelSource();
      return;
    }
    if (what !== "dictionary") return engine.refuse("input takes clear (or dictionary <name>, its old form)");
    let score;
    try {
      score = JSON.parse(new max.Dict(String(name)).stringify());
    } catch (e) {
      return engine.refuse(`cannot read the input dictionary ${name}`);
    }
    if (engine.state.bypass) return engine.passThrough(name);
    const asked = s.processing;
    const first = !s.score || s.open;
    if (!destructive() && !first && !asked) return;  // the source stays until capture
    if (destructive() || first) {
      s.score = score;
      s.from = "inlet";
      engine.state.changed = true;
      if (options.onNewSource) options.onNewSource(score);
      tellPanelSource();
    }
    s.open = false;
    setProcessing(false);
    if (asked) return engine.process();                               // the answer to a dump: run on it
    if (!destructive() && engine.state.autorun) engine.schedule();     // a first source, unasked
    // destructive and unasked: kept, run on by the next change or bang (no loop through a roll)
  }

  /** Ask the roll for its score; the next input becomes the source, in either mode. */
  function capture() {
    s.open = true;
    engine.tellPanel("status", "ok", "the next score at the inlet becomes the source");
    max.outlet(OUT.BACH, "dump");
  }

  const messages = {
    dictionary: (name) => input("dictionary", name),  // a score in
    input,                                            // input clear: forget the source; input dictionary <name>: the old form
    capture,
  };

  return { state: s, hooks, messages, info };
}

module.exports = { createSource, countNotes };
