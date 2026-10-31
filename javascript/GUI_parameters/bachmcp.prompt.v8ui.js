/*
bachmcp.prompt.v8ui.js — a chat-style prompt box (v8ui).

Create it as [v8ui bachmcp.prompt.v8ui.js] (its box must not ignore clicks).
Click it to focus (a caret blinks), type, Enter sends; Shift+Enter is a new line.
Click it again (or Escape) to release the focus.

Keys: v8ui gets no key events of its own, so feed it from [key]:
  [key] (all four outlets) -> [pack 0 0 0 0] -> [prepend key] -> this inlet
  (only "key <ascii> <keycode> <modifiers> <unicode>"; ignored while unfocused).
Handled: printable characters, Backspace, Delete, Left/Right, Home/End
(Cmd+Left/Right), Enter, Shift+Enter, Escape.

Out: "prompt <text>" on Enter (empty prompts are not sent); the box then clears
and grows back to one line.
Other messages: set <text> (replace, no output), append <text>, clear, bang
(send what is typed), focus 0|1, placeholder <text>.
*/

autowatch = 1;
inlets = 1;
outlets = 1;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

setinletassist(0, "key <ascii> <keycode> <modifiers> <unicode> (from [key]); set, append, clear, bang, focus");
setoutletassist(0, "prompt <text> on Enter");

const PAD = 8;
const FONT = "Lato";
const SIZE = 13;
const LINE = 18;

let text = "";
let caret = 0;
let focused = false;
let blinkOn = true;
let hint = "Type a prompt, Enter to send";

const blink = new Task(() => { blinkOn = !blinkOn; mgraphics.redraw(); });
blink.interval = 500;

// ── Lines ─────────────────────────────────────────────────────────────── //

// Wrap the text into lines that fit the width; each line keeps its start index.
function wrap(width) {
  mgraphics.select_font_face(FONT);
  mgraphics.set_font_size(SIZE);
  const lines = [];
  const max = width - 2 * PAD;
  let start = 0;
  while (true) {
    const nl = text.indexOf("\n", start);
    const end = nl < 0 ? text.length : nl;
    let s = start;
    // break the paragraph at spaces (or anywhere, for a long word)
    while (mgraphics.text_measure(text.slice(s, end))[0] > max) {
      let cut = end;
      while (cut > s + 1 && mgraphics.text_measure(text.slice(s, cut))[0] > max) cut--;
      const sp = text.lastIndexOf(" ", cut - 1);
      if (sp > s) cut = sp + 1;
      lines.push({ start: s, end: cut });
      s = cut;
    }
    lines.push({ start: s, end });
    if (nl < 0) break;
    start = nl + 1;
  }
  return lines;
}
wrap.local = 1;

function fitHeight(lines) {
  const need = Math.ceil(2 * PAD + Math.max(1, lines.length) * LINE);
  const r = box.rect;
  if (r && Math.abs((r[3] - r[1]) - need) > 0.5) box.rect = [r[0], r[1], r[2], r[1] + need];
}
fitHeight.local = 1;

function refresh() {
  blinkOn = true;
  fitHeight(wrap(mgraphics.size[0]));
  mgraphics.redraw();
}
refresh.local = 1;

// ── Drawing ───────────────────────────────────────────────────────────── //

function paint() {
  const [w, h] = mgraphics.size;
  const g = mgraphics;
  g.set_source_rgba(0.13, 0.13, 0.14, 1);
  g.rectangle_rounded(0.5, 0.5, w - 1, h - 1, 8, 8);
  g.fill_preserve();
  g.set_source_rgba(focused ? [0.45, 0.62, 0.95, 1] : [0.35, 0.35, 0.38, 1]);
  g.set_line_width(1);
  g.stroke();

  const lines = wrap(w);
  if (!text.length) {
    g.set_source_rgba(0.5, 0.5, 0.52, 1);
    g.move_to(PAD, PAD + SIZE);
    g.show_text(hint);
  }
  g.set_source_rgba(0.92, 0.92, 0.92, 1);
  lines.forEach((ln, i) => {
    g.move_to(PAD, PAD + SIZE + i * LINE);
    g.show_text(text.slice(ln.start, ln.end));
  });

  if (focused && blinkOn) {
    let row = lines.length - 1;
    for (let i = 0; i < lines.length; i++) {
      if (caret >= lines[i].start && caret <= lines[i].end) { row = i; break; }
    }
    const ln = lines[row];
    const x = PAD + g.text_measure(text.slice(ln.start, caret))[0];
    const y = PAD + row * LINE + 2;
    g.set_source_rgba(0.85, 0.85, 0.85, 1);
    g.move_to(x + 0.5, y);
    g.line_to(x + 0.5, y + LINE - 2);
    g.stroke();
  }
}

// ── Mouse ─────────────────────────────────────────────────────────────── //

function onclick() {
  focus(focused ? 0 : 1);
}

// ── Keys (from [key]) ─────────────────────────────────────────────────── //

function key(ascii, keycode, modifiers, unicode) {
  if (!focused) return;
  const shift = modifiers & 1;
  const cmd = modifiers & (2 | 16); // command / ctrl, as [key] reports them
  switch (ascii) {
    case 13: case 3:                       // Enter
      if (shift) insert("\n"); else bang();
      return;
    case 27: focus(0); return;             // Escape
    case 8: case 127:                      // Backspace (Delete on macOS)
      if (keycode === 117) { if (caret < text.length) text = text.slice(0, caret) + text.slice(caret + 1); }
      else if (caret > 0) { text = text.slice(0, caret - 1) + text.slice(caret); caret--; }
      refresh();
      return;
    case 28: caret = cmd ? 0 : Math.max(0, caret - 1); refresh(); return;            // Left
    case 29: caret = cmd ? text.length : Math.min(text.length, caret + 1); refresh(); return; // Right
    case 1: caret = 0; refresh(); return;                                           // Home
    case 4: caret = text.length; refresh(); return;                                 // End
  }
  if (cmd) return;
  const code = unicode > 0 ? unicode : ascii;
  if (code >= 32) insert(String.fromCodePoint(code));
}

function insert(s) {
  text = text.slice(0, caret) + s + text.slice(caret);
  caret += s.length;
  refresh();
}
insert.local = 1;

// ── Messages ──────────────────────────────────────────────────────────── //

function bang() {
  const t = text.trim();
  if (!t.length) return;
  outlet(0, "prompt", t);
  clear();
}

function set(...args) { text = args.join(" "); caret = text.length; refresh(); }
function append(...args) { insert(args.join(" ")); }
function clear() { text = ""; caret = 0; refresh(); }
function placeholder(...args) { hint = args.join(" "); mgraphics.redraw(); }

function focus(on) {
  focused = !!on;
  if (focused) blink.repeat(); else blink.cancel();
  blinkOn = true;
  mgraphics.redraw();
}

function onresize() { refresh(); }
