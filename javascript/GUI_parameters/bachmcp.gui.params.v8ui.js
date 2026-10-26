/*
bachmcp.gui.params.v8ui.js — the parameter panel (v8ui).

Create it as [v8ui bachmcp.gui.params.v8ui.js] (its box must not ignore clicks), then:
  a runner's middle outlet  ->  this inlet           (spec, set, status, source, source_mode)
  this outlet               ->  the runner's inlet   (param <name> <value...>, load <path>, ...)

The panel builds itself from the spec the runner sends when it loads a file
(bachmcp.gui.params.panel.js, with the elements of bachmcp.gui.params.elements.js):
  options     snap (drags land on round values; alt inverts it while dragging),
              reset all; a transformer's source: notes, write
              (write_to_playground), capture (capture_source) and its mode,
              non-destructive | destructive (sends "source_mode 1|0")
  parameters  one card each. Moving a control sends "param <name> <value...>".
              Double-click a control: back to its declared value. Click a
              pitch's value (highlighted) to show it as a name, midicents or
              MIDI (an interval: cents or semitones).
The panel resizes itself to its content (autosize 0 to stop).

It is saved with the patch (parameters, values and the file path), and on
reopening it asks the runner to load the file again with those values. It also
works with pattr / pattrstorage: give it a scripting name to store presets.

Other messages: reset (all parameters to their declared values), bang (send
every value), clear, autosize 0/1.
*/

autowatch = 1;
inlets = 1;
outlets = 1;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

const gui = (() => {
  try {
    return require("bachmcp.gui.params.panel.js");
  } catch (e) {
    return null;
  }
})();

var panel = gui && gui.Panel ? new gui.Panel() : null;
if (!panel) post("bachmcp.gui.params: cannot load bachmcp.gui.params.panel.js; the GUI_parameters folder must be in Max's search path\n");
let autosizing = true;
const reloader = new Task(askForFile, this);

setinletassist(0, "from a runner's middle outlet: spec, set, status, source, source_mode");
setoutletassist(0, "to the runner: param <name> <value...>; capture_source, write_to_playground, source_mode, load");

function emit(messages) {
  for (const m of messages) outlet(0, m);
}
emit.local = 1;

function fitHeight() {
  if (!autosizing || !panel) return;
  const need = Math.ceil(panel.layout(mgraphics.size[0]));
  const r = box.rect;
  if (r && Math.abs((r[3] - r[1]) - need) > 0.5) box.rect = [r[0], r[1], r[2], r[1] + need];
}
fitHeight.local = 1;

function refresh() {
  fitHeight();
  mgraphics.redraw();
}
refresh.local = 1;

// ── From the runner ────────────────────────────────────────────────────── //

function spec(text) {
  if (!panel) return;
  let data;
  try {
    data = JSON.parse(String(text));
  } catch (e) {
    post("bachmcp.gui.params: unreadable spec\n");
    return;
  }
  const kept = panel.setSpec(data);
  refresh();
  emit(kept);
}

function set(name, ...atoms) {
  if (panel && panel.setValue(String(name), atoms)) mgraphics.redraw();
}

function source(notes, from) {
  if (!panel) return;
  panel.setSource(notes, from);
  mgraphics.redraw();
}

// the runner's request for a score (capture_source), meant for the roll beside the panel
function dump() {}

function source_mode(flag) {
  if (panel && panel.setSourceMode(flag)) mgraphics.redraw();
}

function status(kind, ...text) {
  if (!panel) return;
  panel.setStatus(kind, text.join(" "));
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
  if (panel) emit(panel.allMessages());
}

function autosize(on) {
  autosizing = Boolean(on);
  refresh();
}

// ── Drawing and the mouse ───────────────────────────────────────────────── //

function paint() {
  const [w, h] = mgraphics.size;
  if (panel) {
    panel.paint(mgraphics, w, h);
    return;
  }
  mgraphics.set_source_rgba(0.11, 0.115, 0.125, 1);
  mgraphics.rectangle(0, 0, w, h);
  mgraphics.fill();
  mgraphics.set_source_rgba(0.96, 0.4, 0.34, 1);
  mgraphics.select_font_face("Arial");
  mgraphics.set_font_size(11);
  mgraphics.move_to(8, 18);
  mgraphics.show_text("bachmcp.gui.params.panel.js not found (see the Max console)");
}

function onresize() {
  if (panel) panel.places = null;
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

function onidle(x, y) {
  if (panel && panel.mouseMove(x, y)) mgraphics.redraw();
}
onidle.local = 1;

function onidleout() {
  if (panel && panel.mouseMove(null)) mgraphics.redraw();
}
onidleout.local = 1;

// ── Saved with the patch ────────────────────────────────────────────────── //

function save() {
  if (!panel) return;
  if (panel.items.length || panel.path) embedmessage("restore", JSON.stringify(panel.snapshot()));
}

function restore(text) {
  if (!panel) return;
  let snapshot;
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

function setvalueof(...flat) {
  if (!panel) return;
  emit(panel.setFlatValues(flat));
  mgraphics.redraw();
}
