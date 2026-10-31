/*
bachmcp.translate.convert.h
---------------------------
bach.roll's gathered syntax (a bach llll) <-> bachjson-complete (a Max
dictionary), as declared in bachjson-syntax-specification.md at the root of
the repository. The llll side is bach's own: what bach.roll dumps and reads,
with or without the leading "roll".

    roll_to_dictionary(roll, d, x) a gathered-syntax llll -> the dictionary d (cleared first)
    dictionary_to_roll(dict, x)    a bachjson-complete dictionary -> a new llll (the caller frees it)
    merge_onset_chords(roll)       a copy of the roll where, in each voice, chords with the same
                                   onset are one chord (the caller frees it)

`x` is the object that reports problems in the Max console. Neither function
changes its input.
*/
#pragma once

#include "foundation/llllobj.h"
#include "ext_dictionary.h"

void roll_to_dictionary(t_llll *roll, t_dictionary *out, t_object *x);
t_llll *dictionary_to_roll(t_dictionary *dict, t_object *x);
t_llll *merge_onset_chords(const t_llll *roll);
