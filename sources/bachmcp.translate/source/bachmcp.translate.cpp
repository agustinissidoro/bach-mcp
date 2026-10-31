/*
bachmcp.translate.cpp
---------------------
[bachmcp.translate @from <format> @to <format>]: a score from one format to
another. One inlet; the left outlet sends scores, the right one reports
"readwrite done". The formats:

    json   bachjson-complete, as a Max dictionary: "dictionary <name>"
    llll   bach.roll's gathered syntax as a native bach llll
    t      the same as text (bach's "t" outlet format; Max's message limit applies)

Defaults: @from llll @to json @transparent 1. Every direction works, json -> json and llll -> llll
included (they pass through the translation and come out checked and in
bach's order).

In:  a native llll or a text llll (@from llll or t), or "dictionary <name>" (@from json).
Out: the llll in the chosen form, or "dictionary <name>": the dictionary this
     object owns, filled again at every output.

@merge_onset_chords 1: in each voice, the notes of every chord with the same
onset go out as one chord (the first one's, then the others' notes, in
order); 0 (default): chords as they came. It applies to every output: the
outlet, read and readwrite.

@transparent 1 (default): any other message (not a native llll, not
"dictionary <name>") goes out of the outlet unchanged. With @from t every
message is a text llll, so nothing is echoed. @transparent 0: only lllls and
dictionaries are taken; anything else is refused with an error.

read <path> and readwrite <in> [<out>] translate files: see Files below.

It is built from bach's own sources, unchanged, and reads and writes native
lllls through the bach package that Max has loaded (the same version).
*/

#include "foundation/llllobj.h"
#include "ext_common.h"
#include "ext_globalsymbol.h"
#include "ext_dictobj.h"

#include "foundation/llll_files.h"

#include <cmath>
#include <string>

#include "bachmcp.translate.convert.h"

typedef struct _translate {
    struct llllobj_object n_ob;
    t_symbol *from;             // json | llll | t
    t_symbol *to;               // json | llll | t
    long transparent;           // echo what is not an llll or a dictionary
    long force_json_as_txt;     // readwrite: JSON into .txt names
    long merge_onset_chords;    // chords with the same onset in a voice become one
    t_symbol *dict_name;        // the dictionary sent out
    t_dictionary *dict;
} t_translate;

static t_class *translate_class;
static t_symbol *ps_json, *ps_llll, *ps_t;

// ── Formats ─────────────────────────────────────────────────────────────── //

static bool valid_format(t_symbol *s)
{
    return s == ps_json || s == ps_llll || s == ps_t;
}

static t_max_err translate_setformat(t_translate *x, t_symbol **field, const char *name, long ac, t_atom *av)
{
    t_symbol *s = (ac && atom_gettype(av) == A_SYM) ? atom_getsym(av) : NULL;
    if (!valid_format(s)) {
        object_error((t_object *)x, "@%s must be json, llll or t", name);
        return MAX_ERR_GENERIC;
    }
    *field = s;
    return MAX_ERR_NONE;
}

static t_max_err translate_setfrom(t_translate *x, void *attr, long ac, t_atom *av)
{
    return translate_setformat(x, &x->from, "from", ac, av);
}

static t_max_err translate_setto(t_translate *x, void *attr, long ac, t_atom *av)
{
    t_max_err err = translate_setformat(x, &x->to, "to", ac, av);
    if (!err && x->n_ob.l_out)  // the llll outlet: native or text
        x->n_ob.l_out[0].b_type = (x->to == ps_t) ? LLLL_O_TEXT : LLLL_O_NATIVE;
    return err;
}

// ── Output ──────────────────────────────────────────────────────────────── //

static void translate_output_roll(t_translate *x, t_llll *roll)
{
    t_llll *merged = x->merge_onset_chords ? merge_onset_chords(roll) : NULL;
    if (merged)
        roll = merged;
    if (x->to == ps_json) {
        roll_to_dictionary(roll, x->dict, (t_object *)x);
        t_atom a;
        atom_setsym(&a, x->dict_name);
        llllobj_outlet_anything((t_object *)x, LLLL_OBJ_VANILLA, 0, _sym_dictionary, 1, &a);
    } else {
        llllobj_outlet_llll((t_object *)x, LLLL_OBJ_VANILLA, 0, roll);
    }
    if (merged)
        llll_free(merged);
}

// What is not a score goes out as it came (@transparent 1)
static void translate_echo(t_translate *x, t_symbol *msg, long ac, t_atom *av)
{
    void *out = x->n_ob.l_out[0].b_outlet;
    if (msg == _sym_bang && ac == 0)
        outlet_bang(out);
    else if (msg == _sym_int && ac == 1)
        outlet_int(out, atom_getlong(av));
    else if (msg == _sym_float && ac == 1)
        outlet_float(out, atom_getfloat(av));
    else if (msg == _sym_list)
        outlet_list(out, NULL, (short)ac, av);
    else
        outlet_anything(out, msg, (short)ac, av);
}

// ── Input ───────────────────────────────────────────────────────────────── //

static void translate_dictionary(t_translate *x, t_symbol *name)
{
    if (x->from != ps_json) {
        object_error((t_object *)x, "received a dictionary but @from is %s: set @from json", x->from->s_name);
        return;
    }
    t_dictionary *d = dictobj_findregistered_retain(name);
    if (!d) {
        object_error((t_object *)x, "no dictionary named %s", name->s_name);
        return;
    }
    t_llll *roll = dictionary_to_roll(d, (t_object *)x);
    dictobj_release(d);
    translate_output_roll(x, roll);
    llll_free(roll);
}

static void translate_anything(t_translate *x, t_symbol *msg, long ac, t_atom *av)
{
    if (msg == _sym_dictionary && ac == 1 && atom_gettype(av) == A_SYM) {
        translate_dictionary(x, atom_getsym(av));
        return;
    }
    // with @from t any message is a text llll; otherwise only a native one is
    if (x->from != ps_t && msg != LLLL_NATIVE_MSG) {
        if (x->transparent)
            translate_echo(x, msg, ac, av);
        else
            object_error((t_object *)x, "@from %s takes %s (@transparent 0)", x->from->s_name,
                         x->from == ps_json ? "\"dictionary <name>\"" : "native lllls");
        return;
    }
    if (x->from == ps_json) {
        object_error((t_object *)x, "@from json takes \"dictionary <name>\"");
        return;
    }
    t_llll *roll = llllobj_parse_llll((t_object *)x, LLLL_OBJ_VANILLA, msg, ac, av, LLLL_PARSE_RETAIN);
    if (!roll) {
        object_error((t_object *)x, "the llll could not be read");
        return;
    }
    translate_output_roll(x, roll);
    llll_free(roll);
}

static void translate_bang(t_translate *x)
{
    translate_anything(x, _sym_bang, 0, NULL);
}

static void translate_int(t_translate *x, t_atom_long v)
{
    t_atom a;
    atom_setlong(&a, v);
    translate_anything(x, _sym_int, 1, &a);
}

static void translate_float(t_translate *x, double v)
{
    t_atom a;
    atom_setfloat(&a, v);
    translate_anything(x, _sym_float, 1, &a);
}

static void translate_assist(t_translate *x, void *b, long m, long a, char *s)
{
    if (m == ASSIST_OUTLET && a == 1)
        snprintf(s, 256, "readwrite done");
    else if (m == ASSIST_INLET)
        snprintf(s, 256, "@from %s: %s", x->from->s_name, x->from == ps_json ? "dictionary <name>" : "llll (gathered syntax)");
    else
        snprintf(s, 256, "@to %s: %s", x->to->s_name, x->to == ps_json ? "dictionary <name>" : "llll (gathered syntax)");
}

static void translate_inletinfo(t_translate *x, void *b, long a, char *t)
{
    *t = 0;
}

// ── Files ───────────────────────────────────────────────────────────────── //
//
// read <path>                 the file, translated, out of the left outlet (@to)
// readwrite <in> [<out>]      the file, translated, into another file; then
//                             "readwrite done" out of the right outlet
//
// A file is JSON when its first character is "{", whatever its extension;
// anything else is read as bach text (or bach's old native format). Without
// <out> the result goes next to <in> with the same name: a JSON file becomes
// <name>.txt (bach text), a bach file becomes <name>.json. <out> ending in
// .json is written as JSON, any other as bach text. @force_json_as_txt 1
// writes JSON into .txt names instead: without <out>, <name>.txt (so a bach
// .txt file is replaced by its JSON).

extern char *llll_add_trailing_zero(t_hatom *h, long maxdecimals);  // bach's llll_files.c

struct t_source {
    bool json;                      // what the file held
    char dir[MAX_PATH_CHARS];       // its folder, absolute, with no trailing slash
    char stem[MAX_PATH_CHARS];      // its name without the extension
};

// The file as a new llll in gathered syntax, or NULL (reported)
static t_llll *translate_readfile(t_translate *x, t_symbol *name, t_source *src)
{
    char filename[MAX_PATH_CHARS];
    char full[MAX_PATH_CHARS];
    short path;
    t_fourcc type, types[] = {'TEXT', 'JSON'};
    filename[0] = 0;
    bach_openfile_for_read((t_object *)x, name, &path, types, 2, &type, filename);
    if (!filename[0]) {
        if (name && name != gensym(""))
            object_error((t_object *)x, "file not found: %s", name->s_name);
        return NULL;
    }
    t_filehandle fh;
    if (path_opensysfile(filename, path, &fh, READ_PERM)) {
        object_error((t_object *)x, "can't open %s", filename);
        return NULL;
    }
    t_ptr_size size;
    sysfile_geteof(fh, &size);
    char *buf = (char *)sysmem_newptr(size + 2);
    sysfile_read(fh, &size, buf);
    sysfile_close(fh);
    buf[size] = 0;

    if (src) {
        path_toabsolutesystempath(path, filename, full);
        char *slash = strrchr(full, '/');
        const char *base = slash ? slash + 1 : full;
        if (slash)
            *slash = 0;
        strncpy_zero(src->dir, slash ? full : "", MAX_PATH_CHARS);
        strncpy_zero(src->stem, base, MAX_PATH_CHARS);
        char *dot = strrchr(src->stem, '.');
        if (dot && dot != src->stem)
            *dot = 0;
    }

    const char *c = buf;
    while (*c && isspace((unsigned char)*c))
        c++;
    bool json = (*c == '{');
    if (src)
        src->json = json;

    t_llll *roll = NULL;
    if (json) {
        t_dictionary *d = NULL;
        char err[256];
        err[0] = 0;
        if (dictobj_dictionaryfromstring(&d, buf, 1, err) || !d)
            object_error((t_object *)x, "%s is not valid JSON%s%s", filename, err[0] ? ": " : "", err);
        else {
            roll = dictionary_to_roll(d, (t_object *)x);
            object_free(d);
        }
    } else {
        roll = llll_readbuffer((t_object *)x, 0, buf, size);  // needs the 2 spare bytes
        if (!roll)
            object_error((t_object *)x, "%s could not be read as an llll", filename);
    }
    sysmem_freeptr(buf);
    return roll;
}

// Readable JSON: two-space indents, arrays of plain values on one line

static void json_text(std::string &s, const char *txt)
{
    s += '"';
    for (const char *c = txt; *c; c++) {
        switch (*c) {
            case '"':  s += "\\\""; break;
            case '\\': s += "\\\\"; break;
            case '\n': s += "\\n"; break;
            case '\r': s += "\\r"; break;
            case '\t': s += "\\t"; break;
            default:
                if ((unsigned char)*c < 0x20) {
                    char u[8];
                    snprintf(u, sizeof(u), "\\u%04x", *c);
                    s += u;
                } else
                    s += *c;
        }
    }
    s += '"';
}

static void json_float(std::string &s, double v)
{
    if (!std::isfinite(v)) {
        s += "null";
        return;
    }
    char num[40];
    snprintf(num, sizeof(num), "%.15g", v);
    if (strtod(num, NULL) != v)
        snprintf(num, sizeof(num), "%.17g", v);
    s += num;
    if (!strpbrk(num, ".eEn"))
        s += ".0";  // stays a float when read back
}

static void json_value(std::string &s, t_atom *a, int depth);

static void json_newline(std::string &s, int depth)
{
    s += '\n';
    s.append(depth * 2, ' ');
}

static bool json_plain(t_atom *a)
{
    if (atom_gettype(a) != A_OBJ)
        return true;
    t_symbol *cls = object_classname(atom_getobj(a));
    return cls == _sym_string;
}

static void json_dictionary(std::string &s, t_dictionary *d, int depth)
{
    long n = 0;
    t_symbol **keys = NULL;
    dictionary_getkeys(d, &n, &keys);
    if (!n) {
        s += "{}";
        return;
    }
    s += '{';
    for (long i = 0; i < n; i++) {
        t_atom a;
        dictionary_getatom(d, keys[i], &a);
        json_newline(s, depth + 1);
        json_text(s, keys[i]->s_name);
        s += ": ";
        json_value(s, &a, depth + 1);
        if (i < n - 1)
            s += ',';
    }
    json_newline(s, depth);
    s += '}';
    dictionary_freekeys(d, n, keys);
}

static void json_array(std::string &s, long ac, t_atom *av, int depth)
{
    bool flat = true;
    for (long i = 0; i < ac && flat; i++)
        flat = json_plain(av + i);
    s += '[';
    for (long i = 0; i < ac; i++) {
        if (flat) {
            if (i)
                s += ", ";
        } else
            json_newline(s, depth + 1);
        json_value(s, av + i, depth + 1);
        if (!flat && i < ac - 1)
            s += ',';
    }
    if (!flat && ac)
        json_newline(s, depth);
    s += ']';
}

static void json_value(std::string &s, t_atom *a, int depth)
{
    switch (atom_gettype(a)) {
        case A_LONG: s += std::to_string((long long)atom_getlong(a)); break;
        case A_FLOAT: json_float(s, atom_getfloat(a)); break;
        case A_SYM: json_text(s, atom_getsym(a)->s_name); break;
        case A_OBJ: {
            t_object *o = (t_object *)atom_getobj(a);
            t_symbol *cls = object_classname(o);
            if (cls == _sym_dictionary)
                json_dictionary(s, (t_dictionary *)o, depth);
            else if (cls == _sym_atomarray) {
                long ac = 0;
                t_atom *av = NULL;
                atomarray_getatoms((t_atomarray *)o, &ac, &av);
                json_array(s, ac, av, depth);
            } else if (cls == _sym_string)
                json_text(s, string_getptr((t_string *)o));
            else
                s += "null";
            break;
        }
        default: s += "null";
    }
}

static bool translate_writefile(t_translate *x, const char *dir, const char *name, const char *txt, t_ptr_size len)
{
    short path = 0;
    char found[MAX_PATH_CHARS];
    if (dir[0] && path_frompathname(dir, &path, found)) {
        object_error((t_object *)x, "no folder %s", dir);
        return false;
    }
    if (!dir[0])
        path = path_getdefault();
    t_filehandle fh = 0;
    if (path_createsysfile(name, path, 'TEXT', &fh) || !fh) {
        object_error((t_object *)x, "can't write %s/%s", dir, name);
        return false;
    }
    sysfile_seteof(fh, 0);
    t_max_err err = sysfile_write(fh, &len, txt);
    sysfile_close(fh);
    if (err)
        object_error((t_object *)x, "error writing %s/%s", dir, name);
    return !err;
}

static bool ends_with(const char *s, const char *ext)
{
    size_t n = strlen(s), e = strlen(ext);
    return n >= e && !strcasecmp(s + n - e, ext);
}

static void translate_doread(t_translate *x, t_symbol *s, long ac, t_atom *av)
{
    t_symbol *name = (ac && atom_gettype(av) == A_SYM) ? atom_getsym(av) : NULL;
    t_llll *roll = translate_readfile(x, name, NULL);
    if (!roll)
        return;
    translate_output_roll(x, roll);
    llll_free(roll);
}

static void translate_doreadwrite(t_translate *x, t_symbol *s, long ac, t_atom *av)
{
    t_symbol *in = (ac >= 1 && atom_gettype(av) == A_SYM) ? atom_getsym(av) : NULL;
    t_symbol *out = (ac >= 2 && atom_gettype(av + 1) == A_SYM) ? atom_getsym(av + 1) : NULL;
    if (!in) {
        object_error((t_object *)x, "readwrite takes <in path> [<out path>]");
        return;
    }
    t_source src;
    t_llll *roll = translate_readfile(x, in, &src);
    if (!roll)
        return;
    if (x->merge_onset_chords) {
        t_llll *merged = merge_onset_chords(roll);
        llll_free(roll);
        roll = merged;
    }

    // where to and in which format
    char dir[MAX_PATH_CHARS], name[MAX_PATH_CHARS];
    bool json;
    if (out) {
        const char *o = out->s_name;
        const char *slash = strrchr(o, '/');
        if (slash) {
            strncpy_zero(dir, o, MIN(MAX_PATH_CHARS, slash - o + 1));
            strncpy_zero(name, slash + 1, MAX_PATH_CHARS);
        } else {
            strncpy_zero(dir, src.dir, MAX_PATH_CHARS);
            strncpy_zero(name, o, MAX_PATH_CHARS);
        }
        json = ends_with(name, ".json") || x->force_json_as_txt;
    } else {
        strncpy_zero(dir, src.dir, MAX_PATH_CHARS);
        json = x->force_json_as_txt || !src.json;
        snprintf(name, MAX_PATH_CHARS, "%s.%s", src.stem, json && !x->force_json_as_txt ? "json" : "txt");
    }

    std::string txt;
    if (json) {
        t_dictionary *d = dictionary_new();
        roll_to_dictionary(roll, d, (t_object *)x);
        json_dictionary(txt, d, 0);
        txt += '\n';
        object_free(d);
    } else {
        char *buf = NULL;
        llll_to_text_buf_pretty(roll, &buf, 0, BACH_DEFAULT_MAXDECIMALS, 0, "\t", -1,
                                LLLL_T_NONE, LLLL_TE_SMART, LLLL_TB_SMART, llll_add_trailing_zero);  // as bach.roll writes
        txt = buf ? buf : "";
        bach_freeptr(buf);
    }
    llll_free(roll);

    if (translate_writefile(x, dir, name, txt.data(), txt.size())) {
        t_atom a;
        atom_setsym(&a, gensym("done"));
        llllobj_outlet_anything((t_object *)x, LLLL_OBJ_VANILLA, 1, gensym("readwrite"), 1, &a);
    }
}

static void translate_read(t_translate *x, t_symbol *s, long ac, t_atom *av)
{
    defer_low(x, (method)translate_doread, s, ac, av);
}

static void translate_readwrite(t_translate *x, t_symbol *s, long ac, t_atom *av)
{
    defer_low(x, (method)translate_doreadwrite, s, ac, av);
}

// ── Life ────────────────────────────────────────────────────────────────── //

static void translate_free(t_translate *x)
{
    if (x->dict)
        object_free(x->dict);  // unregisters it
    llllobj_obj_free((t_llllobj_object *)x);
}

static void *translate_new(t_symbol *s, short ac, t_atom *av)
{
    t_translate *x = (t_translate *)object_alloc_debug(translate_class);
    if (!x) {
        error(BACH_CANT_INSTANTIATE);
        return NULL;
    }
    x->from = ps_llll;
    x->to = ps_json;
    x->transparent = 1;
    x->dict_name = symbol_unique();
    x->dict = dictobj_register(dictionary_new(), &x->dict_name);
    llllobj_obj_setup((t_llllobj_object *)x, 0, "4z");
    attr_args_process(x, ac, av);
    x->n_ob.l_out[0].b_type = (x->to == ps_t) ? LLLL_O_TEXT : LLLL_O_NATIVE;
    llllobj_set_current_version_number_and_ss((t_object *)x, LLLL_OBJ_VANILLA);
    return x;
}

void C74_EXPORT ext_main(void *moduleRef)
{
    common_symbols_init();
    llllobj_common_symbols_init();
    if (llllobj_check_version(bach_get_current_llll_version()) || llllobj_test()) {
        error("bachmcp.translate: the bach package is missing, or another version than the one it was built with");
        return;
    }
    ps_json = gensym("json");
    ps_llll = gensym("llll");
    ps_t = gensym("t");

    t_class *c = class_new("bachmcp.translate", (method)translate_new, (method)translate_free,
                           (long)sizeof(t_translate), 0L, A_GIMME, 0);
    class_addmethod(c, (method)translate_anything, "anything", A_GIMME, 0);
    class_addmethod(c, (method)translate_anything, "list", A_GIMME, 0);
    class_addmethod(c, (method)translate_bang, "bang", 0);
    class_addmethod(c, (method)translate_read, "read", A_GIMME, 0);
    class_addmethod(c, (method)translate_readwrite, "readwrite", A_GIMME, 0);
    class_addmethod(c, (method)translate_int, "int", A_LONG, 0);
    class_addmethod(c, (method)translate_float, "float", A_FLOAT, 0);
    class_addmethod(c, (method)translate_assist, "assist", A_CANT, 0);
    class_addmethod(c, (method)translate_inletinfo, "inletinfo", A_CANT, 0);
    bachobject_class_add_fileusage_method(c);
    llllobj_class_add_versionnumber_attr(c, LLLL_OBJ_VANILLA);

    CLASS_ATTR_SYM(c, "from", 0, t_translate, from);
    CLASS_ATTR_ACCESSORS(c, "from", NULL, translate_setfrom);
    CLASS_ATTR_ENUM(c, "from", 0, "json llll t");
    CLASS_ATTR_LABEL(c, "from", 0, "Input Format");
    CLASS_ATTR_BASIC(c, "from", 0);

    CLASS_ATTR_SYM(c, "to", 0, t_translate, to);
    CLASS_ATTR_ACCESSORS(c, "to", NULL, translate_setto);
    CLASS_ATTR_ENUM(c, "to", 0, "json llll t");
    CLASS_ATTR_LABEL(c, "to", 0, "Output Format");
    CLASS_ATTR_BASIC(c, "to", 0);

    CLASS_ATTR_LONG(c, "transparent", 0, t_translate, transparent);
    CLASS_ATTR_STYLE_LABEL(c, "transparent", 0, "onoff", "Pass Other Messages Through");
    CLASS_ATTR_FILTER_CLIP(c, "transparent", 0, 1);
    CLASS_ATTR_BASIC(c, "transparent", 0);

    CLASS_ATTR_LONG(c, "force_json_as_txt", 0, t_translate, force_json_as_txt);
    CLASS_ATTR_STYLE_LABEL(c, "force_json_as_txt", 0, "onoff", "Write JSON Into .txt Files");
    CLASS_ATTR_FILTER_CLIP(c, "force_json_as_txt", 0, 1);

    CLASS_ATTR_LONG(c, "merge_onset_chords", 0, t_translate, merge_onset_chords);
    CLASS_ATTR_STYLE_LABEL(c, "merge_onset_chords", 0, "onoff", "One Chord Per Onset In Each Voice");
    CLASS_ATTR_FILTER_CLIP(c, "merge_onset_chords", 0, 1);

    class_register(CLASS_BOX, c);
    translate_class = c;
}
