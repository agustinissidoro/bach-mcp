/*
bachmcp.runner.type.generator.js
--------------------------------
The generator type: an algorithm that makes music from nothing, a file that
defines `function produce(p) { ... }`. It needs no source. A score at the
inlet passes through while bypassed and is ignored otherwise. Everything else is the engine's (bachmcp.runner.engine.js).
*/
"use strict";

function create(engine) {
  return {
    name: "generator",
    needs: "function produce(p) { ... }",
    messages: {
      dictionary(name) {
        if (engine.state.bypass) engine.passThrough(name);
      },
      input(what, name) {  // the old form of dictionary <name>
        if (engine.state.bypass && what === "dictionary") engine.passThrough(name);
      },
    },
  };
}

module.exports = { create };
