/*
bachmcp.gui.params.v8ui.js — the parameter panel (v8ui).

Create it as [v8ui bachmcp.gui.params.v8ui.js] (its box must not ignore clicks), or
[bachmcp.gui.params] (init/bachmcp-objectmappings.txt); a first argument is the
name (as set_name), e.g. [bachmcp.gui.params t1]. Then:
  a runner's middle outlet  ->  this inlet           (spec, set, status, source, source_mode)
  this outlet               ->  the runner's inlet   (param <name> <value...>, ...; after a spec,
                                                     sync <message...>: the values it holds, which run nothing)

The panel builds itself from the spec the runner sends when it loads a file
(bachmcp.gui.params.panel.js, with the elements of bachmcp.gui.params.elements.js),
or from a file: spec_file <path> reads the same spec from a .json (the one send_gen writes
for a synth or an fx, gen/<name>.json):
  title       set active ("set_as_active_instance": the instance Claude's tools work for), bypass;
  options     drags land on round values (alt lets one through; on a card set free, alt snaps it);
              reset all; a source's process sel. ("process_only_selection 0|1"); bypass ("bypass 0|1"), repeat; a pitch card's snap toggle ½ | ¼ | free ("snap 0|1|3"),
              a time card's 100ms | 10ms | free;
              a transformer's source: notes, write
              (write_to_playground), capture and its mode,
              non-destructive | destructive (sends "source_mode 1|0");
              a selector's: the same, and whole score | selection only (sends "dump_selection_only 0|1")
  parameters  one card each. Moving a control sends "param <name> <value...>".
              Double-click a control: back to its declared value. Click a
              pitch's value (highlighted) to show it as a name, midicents or
              MIDI (an interval: cents or semitones).
The panel resizes itself to its content (autosize 0 to stop).

It is saved with the patch (parameters, values and the file path) and shows
them again on reopening; it sends nothing then (no load to the runner). It also
works with pattr / pattrstorage: give it a scripting name to store presets.

The algorithm's one-line description comes in the spec (the // comment that opens
its file) and is drawn under the title row; one_line_description <text...> replaces
it by hand (no text removes it).

The prompt's progress: one animated icon left of the type, fed by bachmcp.server's
prompt info for this instance:
  prompt <stage> [detail...]
Stages: received, queued, starting, sent (grey), thinking (a swelling dot), writing,
calling / running <tool> (spinners), done (a check), stopped (a square): both fade
after 4 s; error (a cross) stays. prompt idle removes the icon.

set_type generator|transformer|selector: the base panel of that type before any
algorithm is loaded (title row, output and, for a transformer or a selector, the
source row); kept by clear and saved with the patch. The runner's type echo does
the same.

Other messages: reset (all parameters to their declared values), bang (send
every value), clear, autosize 0/1, set_name [name] (drawn while no algorithm is
loaded; without a name, or with none set: "No algorithm loaded.").
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
// the box's first argument: the name, as set_name
if (panel && jsarguments.length > 1 && !String(jsarguments[1]).startsWith("@")) panel.setName(jsarguments[1]);
if (!panel) post("bachmcp.gui.params: cannot load bachmcp.gui.params.panel.js; the GUI_parameters folder must be in Max's search path\n");
let autosizing = true;

setinletassist(0, "from a runner's middle outlet: spec, set, status, source, source_mode; one_line_description <text>; prompt <stage> [detail]");
setoutletassist(0, "to the runner: param <name> <value...>; capture, write_to_playground, source_mode, set_as_active_instance");

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

function build(data) {
  const kept = panel.setSpec(data);
  refresh();
  // the values this panel holds, back to the runner: sync, so that they run nothing (a load is not a run)
  emit(kept.map((m) => ["sync", ...m]));
}
build.local = 1;

function spec(text) {
  if (!panel) return;
  let data;
  try {
    data = JSON.parse(String(text));
  } catch (e) {
    post("bachmcp.gui.params: unreadable spec\n");
    return;
  }
  build(data);
}

/** The text of a file (UTF-8), or null if it cannot be opened. */
function readText(path) {
  const f = new File(path, "read");
  if (!f.isopen) return null;
  let bytes = "";
  while (f.position < f.eof) {
    const chunk = f.readbytes(Math.min(4096, f.eof - f.position));
    if (!chunk || !chunk.length) break;
    for (let i = 0; i < chunk.length; i++) bytes += String.fromCharCode(chunk[i] & 255);
  }
  f.close();
  try {
    return decodeURIComponent(escape(bytes));
  } catch (e) {
    return bytes;  // not UTF-8: as it is
  }
}
readText.local = 1;

/**
 * spec_file <path>: the spec read from a JSON file ({"description", "params": [...]}, as send_gen
 * writes gen/<name>.json). The path may come in pieces (a message is split at its spaces). A file
 * without a title or a path gets them from where it is: <name>.json is titled <name>.
 */
function spec_file(...pieces) {
  if (!panel) return;
  const path = pieces.join(" ");
  if (!path) return post("bachmcp.gui.params: spec_file needs the path of a .json file\n");
  const text = readText(path);
  if (text === null) return post(`bachmcp.gui.params: spec_file cannot open ${path}\n`);
  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    return post(`bachmcp.gui.params: spec_file ${path} is not JSON (${e.message})\n`);
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return post(`bachmcp.gui.params: spec_file ${path} must hold an object with "params"\n`);
  }
  if (!data.title) data.title = path.split(/[\/:]/).pop().replace(/\.json$/i, "");
  if (!data.path) data.path = path;
  build(data);
}

function set_name(name) {
  if (panel && panel.setName(name)) mgraphics.redraw();
}

function set(name, ...atoms) {
  if (panel && panel.setValue(String(name), atoms)) mgraphics.redraw();
}

// the source's notes: commented out for now (the runner does not send it, the panel does not show it)
function source() {
  // if (!panel) return;
  // panel.setSource(notes, from);
  // mgraphics.redraw();
}

// the runner's request for a score (capture), meant for the roll beside the panel
function dump() {}

function source_mode(flag) {
  if (panel && panel.setSourceMode(flag)) mgraphics.redraw();
}

function involutive(flag) {
  if (panel && panel.setInvolutive(flag)) mgraphics.redraw();
}

function process_only_selection(flag) {
  if (panel && panel.setWithinSelection(flag)) mgraphics.redraw();
}

function bypass(flag) {
  if (panel && panel.setBypass(flag)) mgraphics.redraw();
}

function snap(n) {
  if (panel && panel.setPitchSnap(n)) mgraphics.redraw();
}

function dump_selection_only(flag) {
  if (panel && panel.setSelectionOnly(flag)) mgraphics.redraw();
}

// a transformer's input_mode echo: nothing to show
function input_mode() {}

/** set_type generator|transformer|selector: the base panel of that type, before any algorithm is loaded. */
function set_type(t) {
  if (!panel) return;
  const changed = panel.setType(t);
  if (changed === null) return post(`bachmcp.gui.params: set_type is generator, transformer or selector, got ${t}\n`);
  if (changed) refresh();
}

// the runner's type echo: the same
function type(t) {
  set_type(t);
}

// the runner's auto_dump echo: nothing to show yet
function auto_dump() {}

function one_line_description(...text) {
  if (panel && panel.setDescription(text.join(" "))) refresh();
}

// ── The prompt's progress ───────────────────────────────────────────────── //

// redraws while the icon moves; stops by itself once it is still or gone
const animation = new Task(() => {
  mgraphics.redraw();
  if (!panel || !panel.promptMoving()) animation.cancel();
});
animation.interval = 50;

// prompt <stage> [detail...]
function prompt(stage, ...detail) {
  if (!panel) return;
  if (!panel.setPrompt(stage, detail.join(" "))) return;
  mgraphics.redraw();
  if (panel.promptMoving()) animation.repeat(); else animation.cancel();
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
  if (panel.items.length || panel.path || panel.type) embedmessage("restore", JSON.stringify(panel.snapshot()));
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
}

// ── pattr ───────────────────────────────────────────────────────────────── //

function getvalueof() {
  return panel ? panel.flatValues() : [];
}

function setvalueof(...flat) {
  if (!panel) return;
  emit(panel.setFlatValues(flat));
  mgraphics.redraw();
}
