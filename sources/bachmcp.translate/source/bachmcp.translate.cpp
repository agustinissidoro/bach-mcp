/*
bachmcp.translate.cpp
---------------------
[bachmcp.translate @in <format> @out <format>]: a score from one format to
another. One inlet, one outlet. The formats:

    json   bachjson-complete, as a Max dictionary: "dictionary <name>"
    llll   bach.roll's gathered syntax as a native bach llll
    t      the same as text (bach's "t" outlet format; Max's message limit applies)

Defaults: @in llll @out json. Every direction works, json -> json and llll -> llll
included (they pass through the translation and come out checked and in
bach's order).

In:  a native llll or a text llll (@in llll or t), or "dictionary <name>" (@in json).
Out: the llll in the chosen form, or "dictionary <name>": the dictionary this
     object owns, filled again at every output.

It is built from bach's own sources, unchanged, and reads and writes native
lllls through the bach package that Max has loaded (the same version).
*/

#include "foundation/llllobj.h"
#include "ext_common.h"
#include "ext_globalsymbol.h"
#include "ext_dictobj.h"

#include "bachmcp.translate.convert.h"

typedef struct _translate {
    struct llllobj_object n_ob;
    t_symbol *in;               // json | llll | t
    t_symbol *out;              // json | llll | t
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

static t_max_err translate_setin(t_translate *x, void *attr, long ac, t_atom *av)
{
    return translate_setformat(x, &x->in, "in", ac, av);
}

static t_max_err translate_setout(t_translate *x, void *attr, long ac, t_atom *av)
{
    t_max_err err = translate_setformat(x, &x->out, "out", ac, av);
    if (!err && x->n_ob.l_out)  // the llll outlet: native or text
        x->n_ob.l_out[0].b_type = (x->out == ps_t) ? LLLL_O_TEXT : LLLL_O_NATIVE;
    return err;
}

// ── Output ──────────────────────────────────────────────────────────────── //

static void translate_output_roll(t_translate *x, t_llll *roll)
{
    if (x->out == ps_json) {
        roll_to_dictionary(roll, x->dict, (t_object *)x);
        t_atom a;
        atom_setsym(&a, x->dict_name);
        llllobj_outlet_anything((t_object *)x, LLLL_OBJ_VANILLA, 0, _sym_dictionary, 1, &a);
    } else {
        llllobj_outlet_llll((t_object *)x, LLLL_OBJ_VANILLA, 0, roll);
    }
}

// ── Input ───────────────────────────────────────────────────────────────── //

static void translate_dictionary(t_translate *x, t_symbol *name)
{
    if (x->in != ps_json) {
        object_error((t_object *)x, "received a dictionary but @in is %s: set @in json", x->in->s_name);
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
    if (x->in == ps_json) {
        object_error((t_object *)x, "@in json takes \"dictionary <name>\"");
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
    if (m == ASSIST_INLET)
        snprintf(s, 256, "@in %s: %s", x->in->s_name, x->in == ps_json ? "dictionary <name>" : "llll (gathered syntax)");
    else
        snprintf(s, 256, "@out %s: %s", x->out->s_name, x->out == ps_json ? "dictionary <name>" : "llll (gathered syntax)");
}

static void translate_inletinfo(t_translate *x, void *b, long a, char *t)
{
    *t = 0;
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
    x->in = ps_llll;
    x->out = ps_json;
    x->dict_name = symbol_unique();
    x->dict = dictobj_register(dictionary_new(), &x->dict_name);
    llllobj_obj_setup((t_llllobj_object *)x, 0, "4");
    attr_args_process(x, ac, av);
    x->n_ob.l_out[0].b_type = (x->out == ps_t) ? LLLL_O_TEXT : LLLL_O_NATIVE;
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
    class_addmethod(c, (method)translate_int, "int", A_LONG, 0);
    class_addmethod(c, (method)translate_float, "float", A_FLOAT, 0);
    class_addmethod(c, (method)translate_assist, "assist", A_CANT, 0);
    class_addmethod(c, (method)translate_inletinfo, "inletinfo", A_CANT, 0);
    bachobject_class_add_fileusage_method(c);
    llllobj_class_add_versionnumber_attr(c, LLLL_OBJ_VANILLA);

    CLASS_ATTR_SYM(c, "in", 0, t_translate, in);
    CLASS_ATTR_ACCESSORS(c, "in", NULL, translate_setin);
    CLASS_ATTR_ENUM(c, "in", 0, "json llll t");
    CLASS_ATTR_LABEL(c, "in", 0, "Input Format");
    CLASS_ATTR_BASIC(c, "in", 0);

    CLASS_ATTR_SYM(c, "out", 0, t_translate, out);
    CLASS_ATTR_ACCESSORS(c, "out", NULL, translate_setout);
    CLASS_ATTR_ENUM(c, "out", 0, "json llll t");
    CLASS_ATTR_LABEL(c, "out", 0, "Output Format");
    CLASS_ATTR_BASIC(c, "out", 0);

    class_register(CLASS_BOX, c);
    translate_class = c;
}
