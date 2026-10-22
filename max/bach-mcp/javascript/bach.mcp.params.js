/*
bach.mcp.params.js — the parameter panel (jsui; ECMAScript 5 for the legacy engine).

Create it as [jsui] with this file (or drag the file onto a jsui), then:
  bach.mcp.algo middle outlet  ->  this inlet             (spec, set, status)
  this outlet                  ->  bach.mcp.algo left inlet  (<param> <value...>, load <path>)

The panel builds itself from the spec the runner sends when it loads a file:
one element per parameter, placed automatically (see bach.mcp.gui.js). Moving
an element sends "<param> <value...>". Double-click an element: back to its
declared value. Click a pitch's value text to show it as a name, midicents or
MIDI (an interval: cents or semitones); "snap" in the title row makes drags
land on round values (alt inverts it while dragging). The panel resizes itself to its content (autosize 0 to stop).

It is saved with the patch (parameters, values and the file path), and on
reopening it asks the runner to load the file again with those values. It also
works with pattr / pattrstorage: give it a scripting name to store presets.

A transformer shows its source score in the title row, its source mode
("keep" the original, or "follow" every score at the runner's right inlet;
click to switch, sends "sourcemode keep|follow"), and a capture button that
sends "capture" to the runner (take the score now in the roll as the new
source).

Other messages: reset (all parameters to their declared values), bang (send
every value), clear, autosize 0/1.
*/

autowatch = 1;
inlets = 1;
outlets = 1;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var gui = (function () {
  try {
    return require("bach.mcp.gui.js");
  } catch (e) {
    return null;
  }
})();

var panel = gui && gui.Panel ? new gui.Panel() : null;
if (!panel) post("bach.mcp.params: cannot load bach.mcp.gui.js; it must be in Max's search path (next to this file)\n");
var autosizing = true;
var reloader = new Task(askForFile, this);

setinletassist(0, "from bach.mcp.algo middle outlet: spec, set, status, source, sourcemode");
setoutletassist(0, "to bach.mcp.algo: <param> <value...>");

function emit(messages) {
  for (var i = 0; i < messages.length; i++) outlet(0, messages[i]);
}

function fitHeight() {
  if (!autosizing || !panel) return;
  var size = mgraphics.size;
  var need = Math.ceil(panel.layout(size[0]));
  var r = box.rect;
  if (r && Math.abs((r[3] - r[1]) - need) > 0.5) box.rect = [r[0], r[1], r[2], r[1] + need];
}

function refresh() {
  fitHeight();
  mgraphics.redraw();
}

// ── From bach.mcp.algo ──────────────────────────────────────────────────── //

function spec(text) {
  if (!panel) return;
  var data;
  try {
    data = JSON.parse(String(text));
  } catch (e) {
    post("bach.mcp.params: unreadable spec\n");
    return;
  }
  var kept = panel.setSpec(data);
  refresh();
  emit(kept);
}

function set() {
  if (!panel) return;
  var a = arrayfromargs(arguments);
  if (panel.setValue(String(a[0]), a.slice(1))) mgraphics.redraw();
}

function source(notes, from) {
  if (!panel) return;
  panel.setSource(notes, from);
  mgraphics.redraw();
}

function sourcemode(mode) {
  if (panel && panel.setSourceMode(String(mode))) mgraphics.redraw();
}

function status() {
  if (!panel) return;
  var a = arrayfromargs(arguments);
  panel.setStatus(a[0], a.slice(1).join(" "));
  mgraphics.redraw();
}

// ── Other messages ──────────────────────────────────────────────────────── //

function clear() {
  if (!panel) return;
  panel.clear();
  refresh();
}

function reset() {
  if (!panel) return;
  emit(panel.resetAll());
  mgraphics.redraw();
}

function bang() {
  if (!panel) return;
  emit(panel.allMessages());
}

function autosize(on) {
  autosizing = Boolean(on);
  refresh();
}

// ── Drawing and the mouse ───────────────────────────────────────────────── //

function paint() {
  var size = mgraphics.size;
  if (panel) {
    panel.paint(mgraphics, size[0], size[1]);
    return;
  }
  mgraphics.set_source_rgba(0.14, 0.14, 0.15, 1);
  mgraphics.rectangle(0, 0, size[0], size[1]);
  mgraphics.fill();
  mgraphics.set_source_rgba(0.96, 0.4, 0.34, 1);
  mgraphics.select_font_face("Arial");
  mgraphics.set_font_size(11);
  mgraphics.move_to(8, 18);
  mgraphics.show_text("bach.mcp.gui.js not found (see the Max console)");
}

function onresize() {
  mgraphics.redraw();
}

function onclick(x, y, button, cmd, shift, capslock, option, ctrl) {
  if (!panel) return;
  emit(panel.mouseDown(x, y, { shift: Boolean(shift), alt: Boolean(option), cmd: Boolean(cmd) }));
  mgraphics.redraw();
}
onclick.local = 1;

function ondrag(x, y, button, cmd, shift, capslock, option, ctrl) {
  if (!panel) return;
  if (button) emit(panel.mouseDrag(x, y, { shift: Boolean(shift), alt: Boolean(option) }));
  else panel.mouseUp();
  mgraphics.redraw();
}
ondrag.local = 1;

function ondblclick(x, y) {
  if (!panel) return;
  emit(panel.doubleClick(x, y));
  mgraphics.redraw();
}
ondblclick.local = 1;

// ── Saved with the patch ────────────────────────────────────────────────── //

function save() {
  if (!panel) return;
  if (panel.items.length || panel.path) embedmessage("restore", JSON.stringify(panel.snapshot()));
}

function restore(text) {
  if (!panel) return;
  var snapshot;
  try {
    snapshot = JSON.parse(String(text));
  } catch (e) {
    return;
  }
  panel.restore(snapshot);
  refresh();
  // Once the patch is connected, ask the runner for the file. It answers with its
  // spec, and the panel sends back the values it kept.
  if (panel.path) reloader.schedule(250);
}

function askForFile() {
  if (panel.path) outlet(0, ["load", panel.path]);
}
askForFile.local = 1;

// ── pattr ───────────────────────────────────────────────────────────────── //

function getvalueof() {
  return panel ? panel.flatValues() : [];
}

function setvalueof() {
  if (!panel) return;
  emit(panel.setFlatValues(arrayfromargs(arguments)));
  mgraphics.redraw();
}
