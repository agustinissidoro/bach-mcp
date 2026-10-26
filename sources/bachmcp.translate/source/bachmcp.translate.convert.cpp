/*
bachmcp.translate.convert.cpp
-----------------------------
bach.roll's gathered syntax <-> bachjson-complete. See the header file, and
bachjson-syntax-specification.md for the declaration.

What bach writes (bach source, mains/roll/roll.c and commons/notation/):

    roll HEADER… VOICE…
    HEADER  [slotinfo …] [commands …] [clefs …] [keys …] [voicenames …] [voicespacing …]
            [hidevoices …] [groups …] [markers …] [stafflines …] [midichannels …]
            [articulationinfo …] [noteheadinfo …] [numparts …] [loop …]
    VOICE   [CHORD … flag]
    CHORD   [onset NOTE … [name …] flag]
    NOTE    [pitch dur vel [graphic …] [breakpoints …] [slots …] [articulations …] [name …] flag]

In the dictionary, a list is an atomarray (its sublists atomarrays inside it),
"free content" keeps bach's items as they are: numbers, symbols as strings,
rationals and pitches as strings ("1/2", "Db5"). On the way back such strings
become rationals and pitches again, except in text and filelist slots, whose
content is always text.
*/

#include "bachmcp.translate.convert.h"
#include "ext_atomarray.h"

#include <cctype>
#include <cstdio>
#include <cstring>

namespace {

// ── Symbols ─────────────────────────────────────────────────────────────── //

struct Names {
    t_symbol *roll, *name, *graphic, *breakpoints, *slots, *articulations;
    t_symbol *slotinfo, *commands, *voicenames, *markers, *type, *text, *filelist;
    t_symbol *header, *voices, *chords, *notes, *flag, *onset, *pitch, *spelling, *dur, *vel, *role, *content;
    t_symbol *atomarray, *dictionary;
    Names() {
        roll = gensym("roll"); name = gensym("name"); graphic = gensym("graphic");
        breakpoints = gensym("breakpoints"); slots = gensym("slots"); articulations = gensym("articulations");
        slotinfo = gensym("slotinfo"); commands = gensym("commands"); voicenames = gensym("voicenames");
        markers = gensym("markers"); type = gensym("type"); text = gensym("text"); filelist = gensym("filelist");
        header = gensym("header"); voices = gensym("voices"); chords = gensym("chords"); notes = gensym("notes");
        flag = gensym("flag"); onset = gensym("onset"); pitch = gensym("pitch"); spelling = gensym("spelling");
        dur = gensym("dur"); vel = gensym("vel"); role = gensym("role"); content = gensym("content");
        atomarray = gensym("atomarray"); dictionary = gensym("dictionary");
    }
};

const Names &sym()
{
    static const Names names;
    return names;
}

// The header elements in the order bach writes them; others follow in the dictionary's order.
const char *HEADER_ORDER[] = {
    "slotinfo", "commands", "clefs", "keys", "voicenames", "voicespacing", "hidevoices", "groups",
    "markers", "stafflines", "midichannels", "articulationinfo", "noteheadinfo", "numparts", "loop",
};
const long HEADER_COUNT = sizeof(HEADER_ORDER) / sizeof(HEADER_ORDER[0]);

const long MAX_SLOTS = 30;

// ═══ llll -> dictionary ════════════════════════════════════════════════════ //

t_object *new_array(long ac, t_atom *av)
{
    t_atomarray *aa = atomarray_new(ac, av);
    atomarray_flags(aa, ATOMARRAY_FLAG_FREECHILDREN);  // a sublist inside it is freed with it
    return (t_object *)aa;
}

t_object *llll_to_array(t_llll *ll, long skip);

/** One element of an llll as a dictionary atom: lists become atomarrays, rationals and pitches strings. */
void hatom_to_atom(const t_hatom *h, t_atom *a)
{
    switch (hatom_gettype(h)) {
        case H_LONG:
            atom_setlong(a, hatom_getlong(h));
            break;
        case H_DOUBLE:
            atom_setfloat(a, hatom_getdouble(h));
            break;
        case H_SYM:
            atom_setsym(a, hatom_getsym(h));
            break;
        case H_RAT: {
            char buf[64];
            t_rational r = hatom_getrational(h);
            snprintf(buf, sizeof(buf), "%lld/%lld", (long long)r.r_num, (long long)r.r_den);
            atom_setsym(a, gensym(buf));
            break;
        }
        case H_PITCH:
            atom_setsym(a, hatom_getpitch(h).toSym());
            break;
        case H_LLLL:
            atom_setobj(a, llll_to_array(hatom_getllll(h), 0));
            break;
        default:
            atom_setsym(a, gensym(""));
            break;
    }
}

/** The elements of an llll, after the first `skip`, as an atomarray. */
t_object *llll_to_array(t_llll *ll, long skip)
{
    long n = 0;
    t_llllelem *el = ll ? ll->l_head : NULL;
    for (long i = 0; el && i < skip; i++)
        el = el->l_next;
    for (t_llllelem *e = el; e; e = e->l_next)
        n++;
    t_atom *av = (t_atom *)sysmem_newptrclear(MAX(1, n) * sizeof(t_atom));
    long i = 0;
    for (; el; el = el->l_next)
        hatom_to_atom(&el->l_hatom, av + i++);
    t_object *aa = new_array(n, av);
    sysmem_freeptr(av);
    return aa;
}

/** The names of an item as bach writes one in a list of names: an atom, [] or a list of names. */
t_object *names_from_hatom(const t_hatom *h)
{
    if (hatom_gettype(h) == H_LLLL)
        return llll_to_array(hatom_getllll(h), 0);
    t_atom a;
    hatom_to_atom(h, &a);
    return new_array(1, &a);
}

t_symbol *head_symbol(t_llll *ll)
{
    return (ll && ll->l_head && hatom_gettype(&ll->l_head->l_hatom) == H_SYM) ? hatom_getsym(&ll->l_head->l_hatom) : NULL;
}

/** A number of a list (slot or command number) as a dictionary key: "1" … "30". */
t_symbol *number_key(const t_hatom *h)
{
    if (hatom_gettype(h) == H_SYM)
        return hatom_getsym(h);
    char buf[32];
    snprintf(buf, sizeof(buf), "%ld", (long)hatom_getlong(h));
    return gensym(buf);
}

/** [slotinfo [1 [field items…] …] …] or [commands …]: by number, then by field. */
t_dictionary *numbered_fields(t_llll *element)
{
    t_dictionary *out = dictionary_new();
    for (t_llllelem *el = element->l_head->l_next; el; el = el->l_next) {
        if (hatom_gettype(&el->l_hatom) != H_LLLL)
            continue;
        t_llll *entry = hatom_getllll(&el->l_hatom);
        if (!entry->l_head)
            continue;
        t_dictionary *fields = dictionary_new();
        for (t_llllelem *f = entry->l_head->l_next; f; f = f->l_next) {
            if (hatom_gettype(&f->l_hatom) != H_LLLL)
                continue;
            t_llll *field = hatom_getllll(&f->l_hatom);
            t_symbol *key = head_symbol(field);
            if (key)
                dictionary_appendatomarray(fields, key, llll_to_array(field, 1));
        }
        dictionary_appenddictionary(out, number_key(&entry->l_head->l_hatom), (t_object *)fields);
    }
    return out;
}

/** [voicenames NAMES NAMES …]: each voice's names as a list. */
t_object *voicenames(t_llll *element)
{
    long n = element->l_size - 1;
    t_atom *av = (t_atom *)sysmem_newptrclear(MAX(1, n) * sizeof(t_atom));
    long i = 0;
    for (t_llllelem *el = element->l_head->l_next; el; el = el->l_next)
        atom_setobj(av + i++, names_from_hatom(&el->l_hatom));
    t_object *aa = new_array(n, av);
    sysmem_freeptr(av);
    return aa;
}

/** [markers [onset NAMES role content…] …]: one dictionary per marker. */
t_object *markers(t_llll *element)
{
    long n = element->l_size - 1;
    t_atom *av = (t_atom *)sysmem_newptrclear(MAX(1, n) * sizeof(t_atom));
    long i = 0;
    for (t_llllelem *el = element->l_head->l_next; el; el = el->l_next) {
        if (hatom_gettype(&el->l_hatom) != H_LLLL)
            continue;
        t_llll *marker = hatom_getllll(&el->l_hatom);
        t_dictionary *d = dictionary_new();
        t_llllelem *part = marker->l_head;
        if (part) {
            dictionary_appendfloat(d, sym().onset, hatom_getdouble(&part->l_hatom));
            part = part->l_next;
        }
        if (part) {
            dictionary_appendatomarray(d, sym().name, names_from_hatom(&part->l_hatom));
            part = part->l_next;
        }
        if (part) {
            t_atom role;
            hatom_to_atom(&part->l_hatom, &role);
            dictionary_appendatom(d, sym().role, &role);
            if (part->l_next)
                dictionary_appendatomarray(d, sym().content, llll_to_array(marker, 3));
        }
        atom_setobj(av + i++, (t_object *)d);
    }
    t_object *aa = new_array(i, av);
    sysmem_freeptr(av);
    return aa;
}

t_dictionary *header_element(t_dictionary *header, t_llll *element, t_symbol *key)
{
    if (key == sym().slotinfo || key == sym().commands)
        dictionary_appenddictionary(header, key, (t_object *)numbered_fields(element));
    else if (key == sym().voicenames)
        dictionary_appendatomarray(header, key, voicenames(element));
    else if (key == sym().markers)
        dictionary_appendatomarray(header, key, markers(element));
    else
        dictionary_appendatomarray(header, key, llll_to_array(element, 1));
    return header;
}

/** [pitch dur vel [graphic …] [breakpoints …] [slots …] [articulations …] [name …] flag] */
t_dictionary *note(t_llll *ll)
{
    t_dictionary *d = dictionary_new();
    t_llllelem *el = ll->l_head;
    if (el) {
        dictionary_appendfloat(d, sym().pitch, hatom_getdouble(&el->l_hatom));
        if (hatom_gettype(&el->l_hatom) == H_PITCH)
            dictionary_appendsym(d, sym().spelling, hatom_getpitch(&el->l_hatom).toSym());
        el = el->l_next;
    }
    if (el) {
        dictionary_appendfloat(d, sym().dur, hatom_getdouble(&el->l_hatom));
        el = el->l_next;
    }
    if (el) {
        dictionary_appendlong(d, sym().vel, hatom_getlong(&el->l_hatom));
        el = el->l_next;
    }
    long flag = 0;
    for (; el; el = el->l_next) {
        if (hatom_gettype(&el->l_hatom) != H_LLLL) {
            flag = hatom_getlong(&el->l_hatom);
            continue;
        }
        t_llll *extra = hatom_getllll(&el->l_hatom);
        t_symbol *what = head_symbol(extra);
        if (what == sym().slots) {
            t_dictionary *slots = dictionary_new();
            for (t_llllelem *s = extra->l_head->l_next; s; s = s->l_next) {
                if (hatom_gettype(&s->l_hatom) != H_LLLL || !hatom_getllll(&s->l_hatom)->l_head)
                    continue;
                t_llll *slot = hatom_getllll(&s->l_hatom);
                dictionary_appendatomarray(slots, number_key(&slot->l_head->l_hatom), llll_to_array(slot, 1));
            }
            dictionary_appenddictionary(d, sym().slots, (t_object *)slots);
        } else if (what) {  // graphic, breakpoints, articulations, name
            dictionary_appendatomarray(d, what, llll_to_array(extra, 1));
        }
    }
    dictionary_appendlong(d, sym().flag, flag);
    return d;
}

/** [onset NOTE … [name …] flag] */
t_dictionary *chord(t_llll *ll)
{
    t_dictionary *d = dictionary_new();
    t_llllelem *el = ll->l_head;
    dictionary_appendfloat(d, sym().onset, el ? hatom_getdouble(&el->l_hatom) : 0.);
    long n = 0;
    for (t_llllelem *e = el ? el->l_next : NULL; e; e = e->l_next)
        n++;
    t_atom *av = (t_atom *)sysmem_newptrclear(MAX(1, n) * sizeof(t_atom));
    long count = 0, flag = 0;
    t_object *names = NULL;
    for (el = el ? el->l_next : NULL; el; el = el->l_next) {
        if (hatom_gettype(&el->l_hatom) != H_LLLL) {
            flag = hatom_getlong(&el->l_hatom);
            continue;
        }
        t_llll *item = hatom_getllll(&el->l_hatom);
        if (head_symbol(item) == sym().name)
            names = llll_to_array(item, 1);
        else
            atom_setobj(av + count++, (t_object *)note(item));
    }
    dictionary_appendatomarray(d, sym().notes, new_array(count, av));
    sysmem_freeptr(av);
    if (names)
        dictionary_appendatomarray(d, sym().name, names);
    dictionary_appendlong(d, sym().flag, flag);
    return d;
}

/** [CHORD … flag] */
t_dictionary *voice(t_llll *ll)
{
    t_dictionary *d = dictionary_new();
    t_atom *av = (t_atom *)sysmem_newptrclear(MAX(1, ll->l_size) * sizeof(t_atom));
    long count = 0, flag = 0;
    for (t_llllelem *el = ll->l_head; el; el = el->l_next) {
        if (hatom_gettype(&el->l_hatom) == H_LLLL)
            atom_setobj(av + count++, (t_object *)chord(hatom_getllll(&el->l_hatom)));
        else
            flag = hatom_getlong(&el->l_hatom);
    }
    dictionary_appendatomarray(d, sym().chords, new_array(count, av));
    sysmem_freeptr(av);
    dictionary_appendlong(d, sym().flag, flag);
    return d;
}

// ═══ dictionary -> llll ════════════════════════════════════════════════════ //

/** The atoms of an entry: an array's elements, or the single value. False if there is no such entry. */
bool entry_atoms(t_dictionary *d, t_symbol *key, long *ac, t_atom **av)
{
    *ac = 0;
    *av = NULL;
    if (!d || !dictionary_hasentry(d, key))
        return false;
    if (dictionary_entryisatomarray(d, key)) {
        t_object *aa = NULL;
        dictionary_getatomarray(d, key, &aa);
        if (aa)
            atomarray_getatoms((t_atomarray *)aa, ac, av);
        return true;
    }
    return dictionary_getatoms(d, key, ac, av) == MAX_ERR_NONE;
}

double entry_float(t_dictionary *d, t_symbol *key, double fallback)
{
    t_atom a;
    return (d && dictionary_getatom(d, key, &a) == MAX_ERR_NONE) ? atom_getfloat(&a) : fallback;
}

long entry_long(t_dictionary *d, t_symbol *key, long fallback)
{
    t_atom a;
    return (d && dictionary_getatom(d, key, &a) == MAX_ERR_NONE) ? (long)atom_getlong(&a) : fallback;
}

t_dictionary *entry_dictionary(t_dictionary *d, t_symbol *key)
{
    t_object *sub = NULL;
    if (d && dictionary_hasentry(d, key) && dictionary_entryisdictionary(d, key))
        dictionary_getdictionary(d, key, &sub);
    return (t_dictionary *)sub;
}

bool is_class(t_atom *a, t_symbol *classname)
{
    return atom_gettype(a) == A_OBJ && atom_getobj(a) && object_classname(atom_getobj(a)) == classname;
}

/** A string that bach reads as a rational or a pitch ("1/2", "Db5"), appended as such; false if it is neither. */
bool append_rational_or_pitch(t_llll *ll, const char *s)
{
    bool maybe_rational = (isdigit((unsigned char)s[0]) || s[0] == '-' || s[0] == '+') && strchr(s, '/');
    bool maybe_pitch = strchr("ABCDEFGabcdefg", s[0]) && s[0] && strpbrk(s, "0123456789");
    if (!maybe_rational && !maybe_pitch)
        return false;
    t_llll *parsed = llll_from_text_buf(s);
    bool done = false;
    if (parsed && parsed->l_size == 1) {
        e_hatom_types t = (e_hatom_types)hatom_gettype(&parsed->l_head->l_hatom);
        if (t == H_RAT || t == H_PITCH) {
            llll_appendhatom(ll, &parsed->l_head->l_hatom);
            done = true;
        }
    }
    llll_free(parsed);
    return done;
}

void append_atoms(t_llll *ll, long ac, t_atom *av, bool literal);

/** One dictionary atom into an llll: an atomarray becomes a sublist; text stays text when `literal`. */
void append_atom(t_llll *ll, t_atom *a, bool literal)
{
    switch (atom_gettype(a)) {
        case A_LONG:
            llll_appendlong(ll, atom_getlong(a));
            break;
        case A_FLOAT:
            llll_appenddouble(ll, atom_getfloat(a));
            break;
        case A_SYM: {
            t_symbol *s = atom_getsym(a);
            if (literal || !append_rational_or_pitch(ll, s->s_name))
                llll_appendsym(ll, s);
            break;
        }
        case A_OBJ:
            if (is_class(a, sym().atomarray)) {
                long ac = 0;
                t_atom *av = NULL;
                atomarray_getatoms((t_atomarray *)atom_getobj(a), &ac, &av);
                t_llll *sub = llll_get();
                append_atoms(sub, ac, av, literal);
                llll_appendllll(ll, sub);
            }
            break;
        default:
            break;
    }
}

void append_atoms(t_llll *ll, long ac, t_atom *av, bool literal)
{
    for (long i = 0; i < ac; i++)
        append_atom(ll, av + i, literal);
}

/** [key items…] from an entry's atoms. */
t_llll *keyed_list(t_symbol *key, long ac, t_atom *av, bool literal = false)
{
    t_llll *ll = llll_get();
    llll_appendsym(ll, key);
    append_atoms(ll, ac, av, literal);
    return ll;
}

/** Names in a list of names (voicenames, a marker): none -> [], one atom -> the atom, more -> a list. */
void append_names_element(t_llll *ll, t_atom *names)
{
    long ac = 0;
    t_atom *av = NULL;
    if (is_class(names, sym().atomarray))
        atomarray_getatoms((t_atomarray *)atom_getobj(names), &ac, &av);
    else if (atom_gettype(names) != A_OBJ) {
        append_atom(ll, names, false);
        return;
    }
    if (ac == 1 && atom_gettype(av) != A_OBJ) {
        append_atom(ll, av, false);
        return;
    }
    t_llll *sub = llll_get();
    append_atoms(sub, ac, av, false);
    llll_appendllll(ll, sub);
}

/** The names of a chord or note as [name …], when it has any. */
void append_item_names(t_llll *ll, t_dictionary *d)
{
    long ac = 0;
    t_atom *av = NULL;
    if (entry_atoms(d, sym().name, &ac, &av) && ac > 0)
        llll_appendllll(ll, keyed_list(sym().name, ac, av));
}

/** Which slots hold text (text, filelist), from the header's slotinfo: their content is never parsed. */
void text_slots(t_dictionary *header, bool literal[MAX_SLOTS + 1])
{
    for (long i = 0; i <= MAX_SLOTS; i++)
        literal[i] = false;
    t_dictionary *slotinfo = entry_dictionary(header, sym().slotinfo);
    if (!slotinfo)
        return;
    for (long i = 1; i <= MAX_SLOTS; i++) {
        char buf[8];
        snprintf(buf, sizeof(buf), "%ld", i);
        long ac = 0;
        t_atom *av = NULL;
        if (entry_atoms(entry_dictionary(slotinfo, gensym(buf)), sym().type, &ac, &av) && ac > 0 && atom_gettype(av) == A_SYM)
            literal[i] = atom_getsym(av) == sym().text || atom_getsym(av) == sym().filelist;
    }
}

/** [slotinfo [1 [field items…] …] …] or [commands …] from their dictionary. */
t_llll *numbered_fields_llll(t_symbol *key, t_dictionary *d)
{
    t_llll *ll = llll_get();
    llll_appendsym(ll, key);
    long n = 0;
    t_symbol **keys = NULL;
    dictionary_getkeys_ordered(d, &n, &keys);
    for (long number = 1; number <= 1000 && n > 0; number++) {  // in number order
        char buf[16];
        snprintf(buf, sizeof(buf), "%ld", number);
        t_dictionary *fields = entry_dictionary(d, gensym(buf));
        if (!fields)
            continue;
        t_llll *entry = llll_get();
        llll_appendlong(entry, number);
        long nf = 0;
        t_symbol **fkeys = NULL;
        dictionary_getkeys_ordered(fields, &nf, &fkeys);
        for (long i = 0; i < nf; i++) {
            long ac = 0;
            t_atom *av = NULL;
            entry_atoms(fields, fkeys[i], &ac, &av);
            llll_appendllll(entry, keyed_list(fkeys[i], ac, av, fkeys[i] == sym().name));
        }
        if (fkeys)
            dictionary_freekeys(fields, nf, fkeys);
        llll_appendllll(ll, entry);
    }
    if (keys)
        dictionary_freekeys(d, n, keys);
    return ll;
}

/** One header element of the dictionary as bach's [key …]. */
t_llll *header_element_llll(t_dictionary *header, t_symbol *key)
{
    if (key == sym().slotinfo || key == sym().commands) {
        t_dictionary *d = entry_dictionary(header, key);
        return d ? numbered_fields_llll(key, d) : NULL;
    }
    long ac = 0;
    t_atom *av = NULL;
    if (!entry_atoms(header, key, &ac, &av))
        return NULL;
    t_llll *ll = llll_get();
    llll_appendsym(ll, key);
    if (key == sym().voicenames) {
        for (long i = 0; i < ac; i++)
            append_names_element(ll, av + i);
    } else if (key == sym().markers) {
        for (long i = 0; i < ac; i++) {
            if (!is_class(av + i, sym().dictionary))
                continue;
            t_dictionary *m = (t_dictionary *)atom_getobj(av + i);
            t_llll *marker = llll_get();
            llll_appenddouble(marker, entry_float(m, sym().onset, 0.));
            long nac = 0;
            t_atom *nav = NULL;
            t_atom empty;
            entry_atoms(m, sym().name, &nac, &nav);
            if (dictionary_entryisatomarray(m, sym().name)) {
                t_object *aa = NULL;
                dictionary_getatomarray(m, sym().name, &aa);
                atom_setobj(&empty, aa);
                append_names_element(marker, &empty);
            } else if (nac == 1) {
                append_atom(marker, nav, false);
            } else {
                llll_appendllll(marker, llll_get());
            }
            t_atom role;
            if (dictionary_getatom(m, sym().role, &role) == MAX_ERR_NONE)
                append_atom(marker, &role, true);
            else
                llll_appendsym(marker, gensym("none"));
            long cac = 0;
            t_atom *cav = NULL;
            if (entry_atoms(m, sym().content, &cac, &cav))
                append_atoms(marker, cac, cav, false);
            llll_appendllll(ll, marker);
        }
    } else {
        append_atoms(ll, ac, av, false);
    }
    return ll;
}

t_llll *note_llll(t_dictionary *n, const bool literal_slots[MAX_SLOTS + 1])
{
    t_llll *ll = llll_get();
    t_symbol *spelling = NULL;
    t_atom a;
    if (dictionary_getatom(n, sym().spelling, &a) == MAX_ERR_NONE && atom_gettype(&a) == A_SYM)
        spelling = atom_getsym(&a);
    if (!(spelling && append_rational_or_pitch(ll, spelling->s_name)))
        llll_appenddouble(ll, entry_float(n, sym().pitch, 6000.));
    llll_appenddouble(ll, entry_float(n, sym().dur, 1000.));
    llll_appendlong(ll, entry_long(n, sym().vel, 100));

    long ac = 0;
    t_atom *av = NULL;
    if (entry_atoms(n, sym().graphic, &ac, &av))
        llll_appendllll(ll, keyed_list(sym().graphic, ac, av));
    if (entry_atoms(n, sym().breakpoints, &ac, &av) && ac > 0)
        llll_appendllll(ll, keyed_list(sym().breakpoints, ac, av));
    t_dictionary *slots = entry_dictionary(n, sym().slots);
    if (slots) {
        t_llll *sl = llll_get();
        llll_appendsym(sl, sym().slots);
        long nk = 0;
        t_symbol **keys = NULL;
        dictionary_getkeys_ordered(slots, &nk, &keys);
        for (long i = 0; i < nk; i++) {
            long number = atol(keys[i]->s_name);
            t_llll *slot = llll_get();
            if (number > 0)
                llll_appendlong(slot, number);
            else
                llll_appendsym(slot, keys[i]);  // a slot given by its name
            entry_atoms(slots, keys[i], &ac, &av);
            append_atoms(slot, ac, av, number > 0 && number <= MAX_SLOTS && literal_slots[number]);
            llll_appendllll(sl, slot);
        }
        if (keys)
            dictionary_freekeys(slots, nk, keys);
        llll_appendllll(ll, sl);
    }
    if (entry_atoms(n, sym().articulations, &ac, &av) && ac > 0)
        llll_appendllll(ll, keyed_list(sym().articulations, ac, av, true));
    append_item_names(ll, n);
    llll_appendlong(ll, entry_long(n, sym().flag, 0));
    return ll;
}

t_llll *chord_llll(t_dictionary *c, const bool literal_slots[MAX_SLOTS + 1])
{
    t_llll *ll = llll_get();
    llll_appenddouble(ll, entry_float(c, sym().onset, 0.));
    long ac = 0;
    t_atom *av = NULL;
    entry_atoms(c, sym().notes, &ac, &av);
    for (long i = 0; i < ac; i++)
        if (is_class(av + i, sym().dictionary))
            llll_appendllll(ll, note_llll((t_dictionary *)atom_getobj(av + i), literal_slots));
    append_item_names(ll, c);
    llll_appendlong(ll, entry_long(c, sym().flag, 0));
    return ll;
}

t_llll *voice_llll(t_dictionary *v, const bool literal_slots[MAX_SLOTS + 1])
{
    t_llll *ll = llll_get();
    long ac = 0;
    t_atom *av = NULL;
    entry_atoms(v, sym().chords, &ac, &av);
    for (long i = 0; i < ac; i++)
        if (is_class(av + i, sym().dictionary))
            llll_appendllll(ll, chord_llll((t_dictionary *)atom_getobj(av + i), literal_slots));
    llll_appendlong(ll, entry_long(v, sym().flag, 0));
    return ll;
}

}  // namespace

// ═══ The two directions ════════════════════════════════════════════════════ //

void roll_to_dictionary(t_llll *roll, t_dictionary *out, t_object *x)
{
    dictionary_clear(out);
    t_dictionary *header = dictionary_new();
    long nvoices = 0;
    for (t_llllelem *el = roll->l_head; el; el = el->l_next)
        if (hatom_gettype(&el->l_hatom) == H_LLLL && !head_symbol(hatom_getllll(&el->l_hatom)))
            nvoices++;
    t_atom *voices = (t_atom *)sysmem_newptrclear(MAX(1, nvoices) * sizeof(t_atom));
    long count = 0;
    for (t_llllelem *el = roll->l_head; el; el = el->l_next) {
        if (hatom_gettype(&el->l_hatom) != H_LLLL) {
            if (!(hatom_gettype(&el->l_hatom) == H_SYM && hatom_getsym(&el->l_hatom) == sym().roll))
                object_warn(x, "an atom outside any list was skipped");
            continue;
        }
        t_llll *item = hatom_getllll(&el->l_hatom);
        t_symbol *key = head_symbol(item);
        if (key)
            header_element(header, item, key);
        else
            atom_setobj(voices + count++, (t_object *)voice(item));
    }
    dictionary_appenddictionary(out, sym().header, (t_object *)header);
    dictionary_appendatomarray(out, sym().voices, new_array(count, voices));
    sysmem_freeptr(voices);
}

t_llll *dictionary_to_roll(t_dictionary *dict, t_object *x)
{
    t_llll *roll = llll_get();
    llll_appendsym(roll, sym().roll);
    t_dictionary *header = entry_dictionary(dict, sym().header);
    bool literal_slots[MAX_SLOTS + 1];
    text_slots(header, literal_slots);

    if (header) {
        for (long i = 0; i < HEADER_COUNT; i++) {
            t_llll *el = header_element_llll(header, gensym(HEADER_ORDER[i]));
            if (el)
                llll_appendllll(roll, el);
        }
        long n = 0;
        t_symbol **keys = NULL;
        dictionary_getkeys_ordered(header, &n, &keys);
        for (long i = 0; i < n; i++) {  // elements bach may add that are not listed above
            bool known = false;
            for (long j = 0; j < HEADER_COUNT && !known; j++)
                known = !strcmp(keys[i]->s_name, HEADER_ORDER[j]);
            t_llll *el = known ? NULL : header_element_llll(header, keys[i]);
            if (el)
                llll_appendllll(roll, el);
        }
        if (keys)
            dictionary_freekeys(header, n, keys);
    }

    long ac = 0;
    t_atom *av = NULL;
    if (!entry_atoms(dict, sym().voices, &ac, &av))
        object_warn(x, "the dictionary has no \"voices\": only the header was translated");
    for (long i = 0; i < ac; i++) {
        if (is_class(av + i, sym().dictionary))
            llll_appendllll(roll, voice_llll((t_dictionary *)atom_getobj(av + i), literal_slots));
        else
            object_warn(x, "voice %ld is not an object: skipped", i + 1);
    }
    return roll;
}
