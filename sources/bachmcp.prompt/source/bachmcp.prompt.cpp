/*
bachmcp.prompt — a chat-style prompt box (UI external).

Click it and type. Enter sends; Shift+Enter is a new line. Resize it freely;
text taller than the box scrolls (wheel, or drag the bar). autoheight 1: the
box also grows downwards past the height you gave it, up to maxheight, and
comes back to that height after sending.

Out: "prompt <text>": the whole text as ONE symbol, commas, semicolons, quotes
and new lines included, so Max sends one message whatever is typed
(prepend_prompt_label 0: the symbol alone). Empty prompts are not sent. After
sending, the text stays, dimmed (sentcolor), and the box ignores keys until you
click in it again.

Keys: characters, Backspace, Delete, arrows (Alt: by word, Cmd: line start/end,
Up/Down: by line), Shift+arrows select, Cmd+A / C / X / V / Z (one undo step),
Escape leaves the box. Mouse: click places the caret, drag selects,
double-click selects a word.

Saving: with save_contents 1 (the default; also in the inspector) the text, and
whether it was sent, are saved with the patch and come back on reopening.
Editing marks the patch as modified.

Messages: set <text> (replace, no output), append <text>, clear, bang (send
what is typed), paste, placeholder <text>.
*/

#include "ext.h"
#include "ext_obex.h"
#include "jpatcher_api.h"
#include "jgraphics.h"

#include <string>
#include <vector>
#include <algorithm>

std::string prompt_clipboard_get();
void prompt_clipboard_set(const std::string &text);

static const double PAD = 8.;
static const double SB = 10.;   // room kept on the right for the scroll bar

struct t_line { size_t start, end; };   // byte range, without the break

typedef struct _prompt {
    t_jbox      j_box;
    void       *outlet;
    void       *blink_clock;
    std::string *text;
    std::string *undo;
    std::string *last;                  // the text when last marked dirty
    size_t      caret;                  // byte index
    size_t      anchor;                 // selection's other end (== caret: none)
    char        focused;
    char        sent;                   // sent: dimmed, inactive until clicked
    char        blink_on;
    long        autoheight;
    double      maxheight;
    double      baseheight;             // the height the user gave it
    char        fitting;                // we are resizing it ourselves
    long        prepend_label;
    long        save_contents;
    double      scroll;                 // pixels scrolled down
    char        sbdrag;                 // dragging the scroll bar
    double      sbdrag_y, sbdrag_scroll;
    t_symbol   *placeholder;
    t_jrgba     bgcolor, textcolor, sentcolor, bordercolor, focuscolor, hintcolor, selcolor;
} t_prompt;

static t_class *prompt_class = nullptr;
static t_symbol *ps_prompt;

// ── UTF-8 ──────────────────────────────────────────────────────────────── //

static bool is_cont(unsigned char c) { return (c & 0xC0) == 0x80; }

static size_t prev_char(const std::string &s, size_t i)
{
    if (i == 0) return 0;
    do { i--; } while (i > 0 && is_cont((unsigned char)s[i]));
    return i;
}

static size_t next_char(const std::string &s, size_t i)
{
    if (i >= s.size()) return s.size();
    do { i++; } while (i < s.size() && is_cont((unsigned char)s[i]));
    return i;
}

static void append_utf8(std::string &s, unsigned long cp)
{
    if (cp < 0x80) s += (char)cp;
    else if (cp < 0x800) { s += (char)(0xC0 | (cp >> 6)); s += (char)(0x80 | (cp & 0x3F)); }
    else if (cp < 0x10000) { s += (char)(0xE0 | (cp >> 12)); s += (char)(0x80 | ((cp >> 6) & 0x3F)); s += (char)(0x80 | (cp & 0x3F)); }
    else { s += (char)(0xF0 | (cp >> 18)); s += (char)(0x80 | ((cp >> 12) & 0x3F)); s += (char)(0x80 | ((cp >> 6) & 0x3F)); s += (char)(0x80 | (cp & 0x3F)); }
}

static bool is_word(unsigned char c) { return c >= 0x80 || isalnum(c) || c == '_'; }

static size_t word_left(const std::string &s, size_t i)
{
    while (i > 0 && !is_word((unsigned char)s[i - 1])) i--;
    while (i > 0 && is_word((unsigned char)s[i - 1])) i--;
    return i;
}

static size_t word_right(const std::string &s, size_t i)
{
    while (i < s.size() && !is_word((unsigned char)s[i])) i++;
    while (i < s.size() && is_word((unsigned char)s[i])) i++;
    return i;
}

// ── Layout ─────────────────────────────────────────────────────────────── //

static t_jfont *prompt_font(t_prompt *x)
{
    return jfont_create(jbox_get_fontname((t_object *)x)->s_name, JGRAPHICS_FONT_SLANT_NORMAL,
                        JGRAPHICS_FONT_WEIGHT_NORMAL, jbox_get_fontsize((t_object *)x));
}

static double measure(t_jfont *f, const std::string &s, size_t a, size_t b)
{
    if (b <= a) return 0.;
    std::string part = s.substr(a, b - a);
    double w, h;
    jfont_text_measure(f, part.c_str(), &w, &h);
    return w;
}

// Lines that fit the width: paragraphs broken at spaces (anywhere, for a long word).
static std::vector<t_line> wrap(t_jfont *f, const std::string &s, double width)
{
    std::vector<t_line> lines;
    double max = std::max(10., width - 2 * PAD);
    size_t start = 0;
    while (true) {
        size_t nl = s.find('\n', start);
        size_t end = nl == std::string::npos ? s.size() : nl;
        size_t a = start;
        while (measure(f, s, a, end) > max) {
            // the longest prefix that fits: binary search on bytes, snapped to characters
            size_t lo = a, hi = end;
            while (hi - lo > 1) {
                size_t mid = lo + (hi - lo) / 2;
                while (mid > lo && is_cont((unsigned char)s[mid])) mid--;
                if (mid == lo) { lo = next_char(s, lo); if (lo >= hi) break; continue; }
                if (measure(f, s, a, mid) > max) hi = mid; else lo = mid;
            }
            size_t cut = lo;
            if (cut <= a) cut = next_char(s, a);
            size_t sp = s.rfind(' ', cut - 1);
            if (sp != std::string::npos && sp >= a && sp + 1 > a && sp + 1 < end && sp + 1 <= cut) cut = sp + 1;
            lines.push_back({a, cut});
            a = cut;
        }
        lines.push_back({a, end});
        if (nl == std::string::npos) break;
        start = nl + 1;
    }
    return lines;
}

static double line_height(t_jfont *f)
{
    t_jgraphics_font_extents e;
    jfont_extents(f, &e);
    return e.ascent + e.descent + 3.;
}

static size_t line_of(const std::vector<t_line> &lines, size_t pos)
{
    for (size_t i = 0; i < lines.size(); i++) {
        bool last = i + 1 == lines.size() || lines[i + 1].start > lines[i].end;   // hard break follows
        if (pos >= lines[i].start && (pos < lines[i].end || (pos == lines[i].end && last) || i + 1 == lines.size()))
            return i;
    }
    return lines.size() - 1;
}

// The byte index on a line nearest to an x position.
static size_t index_at(t_jfont *f, const std::string &s, const t_line &ln, double px)
{
    size_t best = ln.start;
    double bestd = 1e9;
    for (size_t i = ln.start;; i = next_char(s, i)) {
        double d = fabs(PAD + measure(f, s, ln.start, i) - px);
        if (d < bestd) { bestd = d; best = i; }
        if (i >= ln.end) break;
    }
    return best;
}

// Content and visible heights, for a box of rect r.
static void heights(t_prompt *x, const t_rect &r, double &content, double &visible)
{
    t_jfont *f = prompt_font(x);
    content = 2 * PAD + wrap(f, *x->text, r.width - SB).size() * line_height(f);
    jfont_destroy(f);
    visible = r.height;
}

static void clamp_scroll(t_prompt *x, const t_rect &r)
{
    double content, visible;
    heights(x, r, content, visible);
    x->scroll = std::max(0., std::min(x->scroll, content - visible));
}

// Grow (or shrink) downwards to the text, up to maxheight; the top stays.
static void prompt_fit(t_prompt *x)
{
    if (!x->autoheight) return;
    t_object *box = (t_object *)x;
    t_rect r;
    jbox_get_patching_rect(box, &r);
    t_jfont *f = prompt_font(x);
    double lh = line_height(f);
    jfont_destroy(f);
    double content, visible;
    heights(x, r, content, visible);
    double need = ceil(std::max(x->baseheight, std::min(content, std::max(x->maxheight, x->baseheight))));
    x->fitting = 1;
    if (fabs(r.height - need) > 0.5) {
        r.height = need;
        jbox_set_patching_rect(box, &r);
    }
    t_rect pr;
    jbox_get_presentation_rect(box, &pr);
    if (fabs(pr.height - need) > 0.5) {
        pr.height = need;
        jbox_set_presentation_rect(box, &pr);
    }
    x->fitting = 0;
}

// Scroll so the caret's line is in view.
static void show_caret(t_prompt *x)
{
    t_rect r;
    jbox_get_patching_rect((t_object *)x, &r);
    t_jfont *f = prompt_font(x);
    std::vector<t_line> lines = wrap(f, *x->text, r.width - SB);
    double lh = line_height(f);
    jfont_destroy(f);
    double top = PAD + line_of(lines, x->caret) * lh;
    if (top - PAD < x->scroll) x->scroll = top - PAD;
    if (top + lh + PAD > x->scroll + r.height) x->scroll = top + lh + PAD - r.height;
    clamp_scroll(x, r);
}

static void prompt_dirty(t_prompt *x)
{
    if (!x->save_contents) return;
    t_object *patcher = jbox_get_patcher((t_object *)x);
    if (patcher) jpatcher_set_dirty(patcher, 1);
}

static void prompt_changed(t_prompt *x)
{
    if (*x->text != *x->last) { *x->last = *x->text; prompt_dirty(x); }   // caret moves don't count
    x->sent = 0;                        // any edit makes it live again
    x->blink_on = 1;
    if (x->focused) clock_delay(x->blink_clock, 500);
    prompt_fit(x);
    show_caret(x);
    jbox_redraw((t_jbox *)x);
}

// ── Editing ────────────────────────────────────────────────────────────── //

static bool has_sel(t_prompt *x) { return x->caret != x->anchor; }

static void sel_range(t_prompt *x, size_t &a, size_t &b)
{
    a = std::min(x->caret, x->anchor);
    b = std::max(x->caret, x->anchor);
}

static void keep_undo(t_prompt *x) { *x->undo = *x->text; }

static void delete_sel(t_prompt *x)
{
    size_t a, b;
    sel_range(x, a, b);
    x->text->erase(a, b - a);
    x->caret = x->anchor = a;
}

static void insert(t_prompt *x, const std::string &s)
{
    if (has_sel(x)) delete_sel(x);
    x->text->insert(x->caret, s);
    x->caret += s.size();
    x->anchor = x->caret;
}

static std::string clean(const std::string &s)
{
    std::string out;
    for (size_t i = 0; i < s.size(); i++) {
        if (s[i] == '\r') { out += '\n'; if (i + 1 < s.size() && s[i + 1] == '\n') i++; }
        else if (s[i] == '\t') out += ' ';
        else out += s[i];
    }
    return out;
}

static std::string atoms_text(long argc, t_atom *argv)
{
    std::string s;
    for (long i = 0; i < argc; i++) {
        if (i) s += ' ';
        if (atom_gettype(argv + i) == A_SYM) s += atom_getsym(argv + i)->s_name;
        else {
            char *buf = nullptr;
            long len = 0;
            atom_gettext(1, argv + i, &len, &buf, 0);
            if (buf) { s += buf; sysmem_freeptr(buf); }
        }
    }
    return s;
}

// ── Messages ───────────────────────────────────────────────────────────── //

void prompt_bang(t_prompt *x)
{
    std::string s = *x->text;
    size_t a = s.find_first_not_of(" \n");
    if (a == std::string::npos) return;
    size_t b = s.find_last_not_of(" \n");
    s = s.substr(a, b - a + 1);
    x->sent = 1;
    prompt_dirty(x);
    x->anchor = x->caret;
    clock_unset(x->blink_clock);
    jbox_redraw((t_jbox *)x);
    if (x->prepend_label) {
        t_atom av;
        atom_setsym(&av, gensym(s.c_str()));
        outlet_anything(x->outlet, ps_prompt, 1, &av);
    }
    else outlet_anything(x->outlet, gensym(s.c_str()), 0, nullptr);
}

void prompt_set(t_prompt *x, t_symbol *s, long argc, t_atom *argv)
{
    *x->text = clean(atoms_text(argc, argv));
    x->caret = x->anchor = x->text->size();
    prompt_changed(x);
}

void prompt_append(t_prompt *x, t_symbol *s, long argc, t_atom *argv)
{
    keep_undo(x);
    insert(x, clean(atoms_text(argc, argv)));
    prompt_changed(x);
}

void prompt_clear(t_prompt *x)
{
    keep_undo(x);
    x->text->clear();
    x->caret = x->anchor = 0;
    prompt_changed(x);
}

void prompt_paste(t_prompt *x)
{
    std::string s = clean(prompt_clipboard_get());
    if (s.empty()) return;
    keep_undo(x);
    insert(x, s);
    prompt_changed(x);
}

void prompt_placeholder(t_prompt *x, t_symbol *s, long argc, t_atom *argv)
{
    x->placeholder = gensym(atoms_text(argc, argv).c_str());
    jbox_redraw((t_jbox *)x);
}

// ── Keys ───────────────────────────────────────────────────────────────── //

static void line_move(t_prompt *x, int dir, size_t &to)
{
    t_rect r;
    jbox_get_patching_rect((t_object *)x, &r);
    t_jfont *f = prompt_font(x);
    std::vector<t_line> lines = wrap(f, *x->text, r.width - SB);
    size_t li = line_of(lines, x->caret);
    if ((dir < 0 && li == 0) || (dir > 0 && li + 1 >= lines.size())) to = dir < 0 ? 0 : x->text->size();
    else {
        double px = PAD + measure(f, *x->text, lines[li].start, x->caret);
        to = index_at(f, *x->text, lines[li + dir], px);
    }
    jfont_destroy(f);
}

long prompt_key(t_prompt *x, t_object *patcherview, long keycode, long modifiers, long textcharacter)
{
    if (!x->focused) return 0;
    if (x->sent) return 1;              // inactive until clicked
    const std::string &s = *x->text;
    bool shift = modifiers & eShiftKey;
    bool cmd = modifiers & eCommandKey;
    bool alt = modifiers & eAltKey;
    size_t to = x->caret;

    switch (keycode) {
    case JKEY_RETURN:
        if (shift) { keep_undo(x); insert(x, "\n"); prompt_changed(x); }
        else prompt_bang(x);
        return 1;
    case JKEY_ESC:
        x->focused = 0;
        x->anchor = x->caret;
        jbox_redraw((t_jbox *)x);
        return 1;
    case JKEY_BACKSPACE:
    case JKEY_DELETE: {
        keep_undo(x);
        if (!has_sel(x)) {
            bool back = keycode == JKEY_BACKSPACE;
            if (back) x->anchor = cmd ? 0 : alt ? word_left(s, x->caret) : prev_char(s, x->caret);
            else x->anchor = cmd ? s.size() : alt ? word_right(s, x->caret) : next_char(s, x->caret);
        }
        delete_sel(x);
        prompt_changed(x);
        return 1;
    }
    case JKEY_LEFTARROW:
        if (has_sel(x) && !shift) to = std::min(x->caret, x->anchor);
        else to = cmd ? 0 : alt ? word_left(s, x->caret) : prev_char(s, x->caret);
        break;
    case JKEY_RIGHTARROW:
        if (has_sel(x) && !shift) to = std::max(x->caret, x->anchor);
        else to = cmd ? s.size() : alt ? word_right(s, x->caret) : next_char(s, x->caret);
        break;
    case JKEY_UPARROW: if (cmd) to = 0; else line_move(x, -1, to); break;
    case JKEY_DOWNARROW: if (cmd) to = s.size(); else line_move(x, 1, to); break;
    case JKEY_HOME: to = 0; break;
    case JKEY_END: to = s.size(); break;
    default: {
        if (cmd) {
            long c = tolower((int)(textcharacter ? textcharacter : keycode));
            size_t a, b;
            sel_range(x, a, b);
            switch (c) {
            case 'a': x->anchor = 0; x->caret = s.size(); prompt_changed(x); return 1;
            case 'c': if (has_sel(x)) prompt_clipboard_set(s.substr(a, b - a)); else prompt_clipboard_set(s); return 1;
            case 'x':
                if (!has_sel(x)) { x->anchor = 0; x->caret = s.size(); sel_range(x, a, b); }
                prompt_clipboard_set(s.substr(a, b - a));
                keep_undo(x); delete_sel(x); prompt_changed(x);
                return 1;
            case 'v': prompt_paste(x); return 1;
            case 'z': { std::string t = *x->text; *x->text = *x->undo; *x->undo = t;
                        x->caret = x->anchor = x->text->size(); prompt_changed(x); return 1; }
            default: return 0;          // other shortcuts go on to Max
            }
        }
        if (textcharacter >= 32 && textcharacter != 127) {
            std::string ch;
            append_utf8(ch, (unsigned long)textcharacter);
            keep_undo(x);
            insert(x, ch);
            prompt_changed(x);
            return 1;
        }
        return 0;
    }
    }
    x->caret = to;
    if (!shift) x->anchor = to;
    prompt_changed(x);
    return 1;
}

// ── Mouse and focus ────────────────────────────────────────────────────── //

static size_t hit(t_prompt *x, t_object *patcherview, t_pt pt)
{
    t_rect r;
    jbox_get_rect_for_view((t_object *)x, patcherview, &r);
    t_jfont *f = prompt_font(x);
    std::vector<t_line> lines = wrap(f, *x->text, r.width - SB);
    double lh = line_height(f);
    long li = (long)floor((pt.y + x->scroll - PAD) / lh);
    li = std::max(0L, std::min(li, (long)lines.size() - 1));
    size_t i = index_at(f, *x->text, lines[li], pt.x);
    jfont_destroy(f);
    return i;
}

void prompt_mousedown(t_prompt *x, t_object *patcherview, t_pt pt, long modifiers)
{
    jbox_grabfocus((t_jbox *)x);
    x->focused = 1;
    x->sent = 0;
    t_rect r;
    jbox_get_rect_for_view((t_object *)x, patcherview, &r);
    double content, visible;
    heights(x, r, content, visible);
    x->sbdrag = 0;
    if (content > visible && pt.x >= r.width - SB) {
        // on the bar: a click off the thumb jumps there, then drag
        double th = std::max(16., visible * visible / content);
        double ty = (visible - th) * x->scroll / (content - visible);
        if (pt.y < ty || pt.y > ty + th)
            x->scroll = (pt.y - th / 2) / (visible - th) * (content - visible);
        clamp_scroll(x, r);
        x->sbdrag = 1;
        x->sbdrag_y = pt.y;
        x->sbdrag_scroll = x->scroll;
        jbox_redraw((t_jbox *)x);
        return;
    }
    size_t i = hit(x, patcherview, pt);
    x->caret = i;
    if (!(modifiers & eShiftKey)) x->anchor = i;
    prompt_changed(x);
}

void prompt_mousedrag(t_prompt *x, t_object *patcherview, t_pt pt, long modifiers)
{
    if (x->sbdrag) {
        t_rect r;
        jbox_get_rect_for_view((t_object *)x, patcherview, &r);
        double content, visible;
        heights(x, r, content, visible);
        double th = std::max(16., visible * visible / content);
        if (visible > th) x->scroll = x->sbdrag_scroll + (pt.y - x->sbdrag_y) * (content - visible) / (visible - th);
        clamp_scroll(x, r);
        jbox_redraw((t_jbox *)x);
        return;
    }
    x->caret = hit(x, patcherview, pt);
    prompt_changed(x);
}

void prompt_mouseup(t_prompt *x, t_object *patcherview, t_pt pt, long modifiers)
{
    x->sbdrag = 0;
}

void prompt_mousewheel(t_prompt *x, t_object *patcherview, t_pt pt, long modifiers, double x_inc, double y_inc)
{
    t_rect r;
    jbox_get_rect_for_view((t_object *)x, patcherview, &r);
    x->scroll -= y_inc * 40.;
    clamp_scroll(x, r);
    jbox_redraw((t_jbox *)x);
}

void prompt_mousedoubleclick(t_prompt *x, t_object *patcherview, t_pt pt, long modifiers)
{
    const std::string &s = *x->text;
    size_t i = hit(x, patcherview, pt);
    size_t a = i, b = i;
    while (a > 0 && is_word((unsigned char)s[a - 1])) a--;
    while (b < s.size() && is_word((unsigned char)s[b])) b++;
    x->anchor = a;
    x->caret = b;
    prompt_changed(x);
}

long prompt_focusgained(t_prompt *x, t_object *patcherview)
{
    x->focused = 1;
    prompt_changed(x);
    return 0;
}

long prompt_focuslost(t_prompt *x, t_object *patcherview)
{
    x->focused = 0;
    x->anchor = x->caret;
    clock_unset(x->blink_clock);
    jbox_redraw((t_jbox *)x);
    return 0;
}

void prompt_blink(t_prompt *x)
{
    if (!x->focused) return;
    x->blink_on = !x->blink_on;
    jbox_redraw((t_jbox *)x);
    clock_delay(x->blink_clock, 500);
}

// ── Drawing ────────────────────────────────────────────────────────────── //

void prompt_paint(t_prompt *x, t_object *patcherview)
{
    t_rect r;
    jbox_get_rect_for_view((t_object *)x, patcherview, &r);
    t_jgraphics *g = (t_jgraphics *)patcherview_get_jgraphics(patcherview);
    const std::string &s = *x->text;

    jgraphics_rectangle_rounded(g, 0.5, 0.5, r.width - 1, r.height - 1, 8, 8);
    jgraphics_set_source_jrgba(g, &x->bgcolor);
    jgraphics_fill_preserve(g);
    jgraphics_set_source_jrgba(g, x->focused && !x->sent ? &x->focuscolor : &x->bordercolor);
    jgraphics_set_line_width(g, 1);
    jgraphics_stroke(g);

    t_jfont *f = prompt_font(x);
    jgraphics_select_jfont(g, f);
    std::vector<t_line> lines = wrap(f, s, r.width - SB);
    double lh = line_height(f), asc;
    { t_jgraphics_font_extents e; jfont_extents(f, &e); asc = e.ascent; }
    clamp_scroll(x, r);
    double content = 2 * PAD + lines.size() * lh, visible = r.height;

    jgraphics_save(g);
    jgraphics_clip(g, 1, 1, r.width - 2, r.height - 2);
    jgraphics_translate(g, 0, -x->scroll);

    // selection
    if (has_sel(x)) {
        size_t a, b;
        sel_range(x, a, b);
        jgraphics_set_source_jrgba(g, &x->selcolor);
        for (size_t i = 0; i < lines.size(); i++) {
            size_t la = std::max(a, lines[i].start), lb = std::min(b, lines[i].end);
            if (la > lb || (la == lb && !(b > lines[i].end && a <= lines[i].end))) continue;
            double x0 = PAD + measure(f, s, lines[i].start, la);
            double x1 = PAD + measure(f, s, lines[i].start, lb) + (b > lines[i].end ? 4 : 0);
            jgraphics_rectangle(g, x0, PAD + i * lh, x1 - x0, lh);
            jgraphics_fill(g);
        }
    }

    if (s.empty() && x->placeholder != gensym("")) {
        jgraphics_set_source_jrgba(g, &x->hintcolor);
        jgraphics_move_to(g, PAD, PAD + asc + 1);
        jgraphics_show_text(g, x->placeholder->s_name);
    }
    jgraphics_set_source_jrgba(g, x->sent ? &x->sentcolor : &x->textcolor);
    for (size_t i = 0; i < lines.size(); i++) {
        std::string part = s.substr(lines[i].start, lines[i].end - lines[i].start);
        jgraphics_move_to(g, PAD, PAD + i * lh + asc + 1);
        jgraphics_show_text(g, part.c_str());
    }

    if (x->focused && !x->sent && x->blink_on) {
        size_t li = line_of(lines, x->caret);
        double cx = floor(PAD + measure(f, s, lines[li].start, x->caret)) + 0.5;
        jgraphics_set_source_jrgba(g, &x->textcolor);
        jgraphics_move_to(g, cx, PAD + li * lh + 1);
        jgraphics_line_to(g, cx, PAD + (li + 1) * lh - 1);
        jgraphics_stroke(g);
    }
    jgraphics_restore(g);

    // scroll bar
    if (content > visible + 0.5) {
        double th = std::max(16., visible * visible / content);
        double ty = (visible - th) * x->scroll / (content - visible);
        jgraphics_rectangle_rounded(g, r.width - SB + 2, ty + 3, SB - 5, th - 6, 3, 3);
        jgraphics_set_source_jrgba(g, &x->bordercolor);
        jgraphics_fill(g);
    }
    jfont_destroy(f);
}

// ── Life ───────────────────────────────────────────────────────────────── //

void prompt_jsave(t_prompt *x, t_dictionary *d)
{
    if (!x->save_contents) return;
    dictionary_appendstring(d, gensym("prompt_text"), x->text->c_str());
    dictionary_appendlong(d, gensym("prompt_sent"), x->sent);
}

void prompt_assist(t_prompt *x, void *b, long m, long a, char *s)
{
    if (m == ASSIST_INLET) snprintf(s, 512, "set, append, clear, bang, paste, placeholder");
    else snprintf(s, 512, "prompt <text>: the whole text as one symbol, on Enter");
}

t_max_err prompt_notify(t_prompt *x, t_symbol *s, t_symbol *msg, void *sender, void *data)
{
    if (msg == gensym("attr_modified")) {
        // moving or resizing the box only repaints (refitting here fought the drag)
        t_symbol *name = (t_symbol *)object_method((t_object *)data, gensym("getname"));
        if (name == gensym("patching_rect") || name == gensym("presentation_rect")) {
            if (!x->fitting) {
                t_rect r;
                jbox_get_patching_rect((t_object *)x, &r);
                x->baseheight = r.height;
            }
        }
        else if (name == gensym("autoheight") || name == gensym("maxheight")) prompt_changed(x);
        jbox_redraw((t_jbox *)x);
    }
    return jbox_notify((t_jbox *)x, s, msg, sender, data);
}

void *prompt_new(t_symbol *s, long argc, t_atom *argv)
{
    t_dictionary *d = object_dictionaryarg(argc, argv);
    if (!d) return nullptr;
    t_prompt *x = (t_prompt *)object_alloc(prompt_class);
    long flags = JBOX_DRAWFIRSTIN | JBOX_NODRAWBOX | JBOX_DRAWINLAST | JBOX_TRANSPARENT
               | JBOX_GROWBOTH | JBOX_HILITE | JBOX_FONTATTR;
    jbox_new((t_jbox *)x, flags, argc, argv);
    x->j_box.b_firstin = (t_object *)x;
    x->text = new std::string();
    x->undo = new std::string();
    x->last = new std::string();
    x->caret = x->anchor = 0;
    x->focused = 0;
    x->sent = 0;
    x->blink_on = 1;
    x->autoheight = 0;
    x->fitting = 0;
    x->maxheight = 200.;
    x->prepend_label = 1;
    x->scroll = 0.;
    x->sbdrag = 0;
    x->placeholder = gensym("Type a prompt, Enter to send");
    x->outlet = outlet_new(x, nullptr);
    x->blink_clock = clock_new(x, (method)prompt_blink);
    x->save_contents = 1;
    attr_dictionary_process(x, d);
    const char *saved = nullptr;
    if (dictionary_getstring(d, gensym("prompt_text"), &saved) == MAX_ERR_NONE && saved) {
        *x->text = saved;
        *x->last = saved;
        x->caret = x->anchor = x->text->size();
        t_atom_long sent = 0;
        dictionary_getlong(d, gensym("prompt_sent"), &sent);
        x->sent = (char)sent;
    }
    t_rect r;
    jbox_get_patching_rect((t_object *)x, &r);
    x->baseheight = r.height;
    jbox_ready((t_jbox *)x);
    return x;
}

void prompt_free(t_prompt *x)
{
    object_free(x->blink_clock);
    delete x->text;
    delete x->undo;
    delete x->last;
    jbox_free((t_jbox *)x);
}

extern "C" C74_EXPORT void ext_main(void *r)
{
    t_class *c = class_new("bachmcp.prompt", (method)prompt_new, (method)prompt_free,
                           sizeof(t_prompt), nullptr, A_GIMME, 0);
    c->c_flags |= CLASS_FLAG_NEWDICTIONARY;
    jbox_initclass(c, JBOX_FIXWIDTH | JBOX_COLOR | JBOX_FONTATTR);

    class_addmethod(c, (method)prompt_paint, "paint", A_CANT, 0);
    class_addmethod(c, (method)prompt_key, "key", A_CANT, 0);
    class_addmethod(c, (method)prompt_mousedown, "mousedown", A_CANT, 0);
    class_addmethod(c, (method)prompt_mousedrag, "mousedrag", A_CANT, 0);
    class_addmethod(c, (method)prompt_mouseup, "mouseup", A_CANT, 0);
    class_addmethod(c, (method)prompt_mousewheel, "mousewheel", A_CANT, 0);
    class_addmethod(c, (method)prompt_mousedoubleclick, "mousedoubleclick", A_CANT, 0);
    class_addmethod(c, (method)prompt_focusgained, "focusgained", A_CANT, 0);
    class_addmethod(c, (method)prompt_focuslost, "focuslost", A_CANT, 0);
    class_addmethod(c, (method)prompt_notify, "notify", A_CANT, 0);
    class_addmethod(c, (method)prompt_jsave, "jsave", A_CANT, 0);
    class_addmethod(c, (method)prompt_assist, "assist", A_CANT, 0);
    class_addmethod(c, (method)prompt_bang, "bang", 0);
    class_addmethod(c, (method)prompt_set, "set", A_GIMME, 0);
    class_addmethod(c, (method)prompt_append, "append", A_GIMME, 0);
    class_addmethod(c, (method)prompt_clear, "clear", 0);
    class_addmethod(c, (method)prompt_paste, "paste", 0);

    CLASS_ATTR_LONG(c, "autoheight", 0, t_prompt, autoheight);
    CLASS_ATTR_STYLE_LABEL(c, "autoheight", 0, "onoff", "Grow With Text");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "autoheight", 0, "0");

    CLASS_ATTR_DOUBLE(c, "maxheight", 0, t_prompt, maxheight);
    CLASS_ATTR_LABEL(c, "maxheight", 0, "Maximum Height (grows to it, then scrolls)");
    CLASS_ATTR_FILTER_MIN(c, "maxheight", 20);
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "maxheight", 0, "400.");

    CLASS_ATTR_LONG(c, "prepend_prompt_label", 0, t_prompt, prepend_label);
    CLASS_ATTR_STYLE_LABEL(c, "prepend_prompt_label", 0, "onoff", "Prepend \"prompt\"");
    CLASS_ATTR_DEFAULT_SAVE(c, "prepend_prompt_label", 0, "1");

    CLASS_ATTR_LONG(c, "save_contents", 0, t_prompt, save_contents);
    CLASS_ATTR_STYLE_LABEL(c, "save_contents", 0, "onoff", "Save Contents With Patcher");
    CLASS_ATTR_DEFAULT_SAVE(c, "save_contents", 0, "1");

    CLASS_ATTR_RGBA(c, "bgcolor", 0, t_prompt, bgcolor);
    CLASS_ATTR_STYLE_LABEL(c, "bgcolor", 0, "rgba", "Background Color");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "bgcolor", 0, "0.13 0.13 0.14 1.");
    CLASS_ATTR_RGBA(c, "textcolor", 0, t_prompt, textcolor);
    CLASS_ATTR_STYLE_LABEL(c, "textcolor", 0, "rgba", "Text Color");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "textcolor", 0, "0.92 0.92 0.92 1.");
    CLASS_ATTR_RGBA(c, "sentcolor", 0, t_prompt, sentcolor);
    CLASS_ATTR_STYLE_LABEL(c, "sentcolor", 0, "rgba", "Sent Text Color");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "sentcolor", 0, "0.6 0.6 0.62 1.");
    CLASS_ATTR_RGBA(c, "bordercolor", 0, t_prompt, bordercolor);
    CLASS_ATTR_STYLE_LABEL(c, "bordercolor", 0, "rgba", "Border Color");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "bordercolor", 0, "0.35 0.35 0.38 1.");
    CLASS_ATTR_RGBA(c, "focuscolor", 0, t_prompt, focuscolor);
    CLASS_ATTR_STYLE_LABEL(c, "focuscolor", 0, "rgba", "Focus Border Color");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "focuscolor", 0, "0.45 0.62 0.95 1.");
    CLASS_ATTR_RGBA(c, "hintcolor", 0, t_prompt, hintcolor);
    CLASS_ATTR_STYLE_LABEL(c, "hintcolor", 0, "rgba", "Placeholder Color");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "hintcolor", 0, "0.5 0.5 0.52 1.");
    CLASS_ATTR_RGBA(c, "selcolor", 0, t_prompt, selcolor);
    CLASS_ATTR_STYLE_LABEL(c, "selcolor", 0, "rgba", "Selection Color");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "selcolor", 0, "0.3 0.42 0.7 0.6");

    CLASS_ATTR_SYM(c, "placeholder", 0, t_prompt, placeholder);
    CLASS_ATTR_LABEL(c, "placeholder", 0, "Placeholder");
    CLASS_ATTR_DEFAULT_SAVE_PAINT(c, "placeholder", 0, "\"Type a prompt, Enter to send\"");

    CLASS_ATTR_DEFAULT(c, "patching_rect", 0, "0. 0. 420. 140.");
    CLASS_ATTR_DEFAULT(c, "fontsize", 0, "13.");

    class_register(CLASS_BOX, c);
    prompt_class = c;
    ps_prompt = gensym("prompt");
}
