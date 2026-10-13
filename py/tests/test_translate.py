"""Tests for the deterministic layers. Run: python -m unittest discover -s py/tests"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.compose import euclid, run_program, scale  # noqa: E402
from bach_mcp.translate import (  # noqa: E402
    ScoreError,
    bach_pitch_to_cents,
    count_notes,
    llll_to_score,
    normalize_score,
    parse_llll,
    required_tonedivision,
    score_messages,
    score_to_addchords,
    score_to_llll,
    summarize,
)

SKILL = os.path.join(os.path.dirname(__file__), "..", "bach_mcp", "BACH_SKILL.md")


def one_voice(*chords, **voice):
    return {"voices": [dict(voice, chords=list(chords))]}


def chord(onset, *notes, **marks):
    """chord(0, (6000, 500), (6400, 500, {"vel": 30}), dyn="p")"""
    out = dict(marks, onset=onset, notes=[])
    for note in notes:
        pitch, dur, extra = (*note, {})[:3]
        out["notes"].append(dict(extra, pitch=pitch, dur=dur))
    return out


def body(*chords):
    """The llll of a single-voice score without the header."""
    return score_to_llll(normalize_score(one_voice(*chords)), with_header=False)[len("roll "):]


def error(score):
    with unittest.TestCase().assertRaises(ScoreError) as ctx:
        normalize_score(score)
    return str(ctx.exception)


class HierarchyTests(unittest.TestCase):
    """voices > chords > notes, exactly as bach.roll's gathered syntax."""

    def test_json_is_the_gathered_syntax_with_named_fields(self):
        score = normalize_score({"voices": [{"name": "Violin I", "chords": [
            {"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "vel": 100}]},
            {"onset": 1000, "notes": [{"pitch": 6400, "dur": 1000, "vel": 90},
                                      {"pitch": 6700, "dur": 250, "vel": 70}]},
        ]}]})
        self.assertEqual(
            score_to_llll(score),
            "roll [clefs G] [voicenames Violin_I] [markers] "
            "[[0 [6000 500 100]] [1000 [6400 1000 90] [6700 250 70]]]",
        )

    def test_units_are_never_converted(self):
        self.assertEqual(body(chord(1234.5, (6050, 333.333))), "[[1234.5 [6050 333.333 80]]]")

    def test_voices_stay_in_order_and_may_be_empty(self):
        score = normalize_score({"voices": [{"chords": []}, {"name": "Tuba", "chords": [chord(0, (3600, 500))]}]})
        self.assertEqual(score_to_llll(score),
                         "roll [clefs G F] [voicenames nil Tuba] [markers] [] [[0 [3600 500 80]]]")
        self.assertEqual(score_to_addchords(score), "addchords [] [[0 [3600 500 80]]]")
        self.assertEqual(count_notes(score), 1)

    def test_chords_are_written_in_time_order(self):
        self.assertEqual(body(chord(500, (6200, 100)), chord(0, (6000, 100))),
                         "[[0 [6000 100 80]] [500 [6200 100 80]]]")

    def test_the_chord_owns_onset_and_marks_the_note_owns_what_sounds(self):
        self.assertIn("\"onset\" belongs to the chord", error(one_voice(
            {"onset": 0, "notes": [{"onset": 0, "pitch": 6000, "dur": 500}]})))
        self.assertIn("\"art\" belongs to the chord", error(one_voice(
            {"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "art": "staccato"}]})))
        self.assertIn("\"pitch\" belongs to the note", error(one_voice({"onset": 0, "pitch": 6000, "dur": 500})))
        self.assertIn("a voice holds \"chords\"", error({"voices": [{"notes": [{"pitch": 6000, "dur": 500}]}]}))

    def test_onset_pitch_and_duration_are_required(self):
        self.assertIn("voice 1, chord 2: \"onset\" is required", error(one_voice(
            chord(0, (6000, 500)), {"notes": [{"pitch": 6000, "dur": 500}]})))
        self.assertIn("voice 1, chord 1, note 2: \"dur\" is required", error(one_voice(
            {"onset": 0, "notes": [{"pitch": 6000, "dur": 500}, {"pitch": 6400}]})))
        self.assertIn("\"pitch\" is required", error(one_voice({"onset": 0, "notes": [{"dur": 500}]})))
        self.assertIn("\"notes\" must be a non-empty list", error(one_voice({"onset": 0, "notes": []})))
        self.assertIn("\"dur\" must be > 0", error(one_voice(chord(0, (6000, 0)))))

    def test_pitch_is_midicents_only(self):
        self.assertIn("looks like a MIDI note number", error(one_voice(chord(0, (60, 500)))))
        self.assertIn("MIDI 60 is 6000", error(one_voice(chord(0, (60, 500)))))
        self.assertIn("Pitch is a number in midicents", error(one_voice(chord(0, ("C4", 500)))))
        self.assertIn("out of range", error(one_voice(chord(0, (20000, 500)))))

    def test_key_aliases(self):
        score = normalize_score({"voices": [{"chords": [
            {"t": 250, "dynamics": "f", "articulation": "accent",
             "notes": [{"cents": 6000, "duration": 500, "velocity": 64}]}]}]})
        self.assertEqual(score_to_llll(score, with_header=False),
                         "roll [[250 [6000 500 64 [slots [20 f] [22 accent]]]]]")


class EncodeTests(unittest.TestCase):
    def test_chord_marks_are_written_once_on_the_first_note(self):
        llll = body(chord(0, (6000, 500), (6400, 500), (6700, 500),
                          dyn="p", art=["tenuto", "marcato"], text="sul pont. (molto)", lyric="la"))
        self.assertEqual(
            llll,
            "[[0 [6000 500 55 [slots [20 p] [21 la] [22 portato martellato] [24 sul pont. molto]]] "
            "[6400 500 55] [6700 500 55]]]",
        )

    def test_note_properties(self):
        self.assertEqual(
            body(chord(0, (3600, 4000), (6400, 1000, {"vel": 50, "gliss": 200, "head": "x"}))),
            "[[0 [3600 4000 80] [6400 1000 50 [breakpoints [0 0 0] [1 200 0]] [slots [23 cross]]]]]",
        )
        self.assertIn("[breakpoints [0 0 0] [0.5 300 0] [1 -200 0.5]]",
                      body(chord(0, (6000, 1000, {"gliss": [[0.5, 300], [1, -200, 0.5]]}))))
        self.assertIn("unknown notehead", error(one_voice(chord(0, (6000, 500, {"head": "star"})))))
        self.assertIn("last gliss point", error(one_voice(chord(0, (6000, 500, {"gliss": [[0.5, 300]]})))))

    def test_dynamic_holds_until_the_next_one(self):
        marks = ["f", None, None, "pp<", None, "sfzp", "cresc _"]
        chords = [chord(i * 100, (6000, 100), **({"dyn": d} if d else {})) for i, d in enumerate(marks)]
        chords[2]["notes"][0]["vel"] = 30
        score = normalize_score(one_voice(*chords, name="Cello"))
        voice = score["voices"][0]
        self.assertEqual(voice["clef"], "F")
        self.assertEqual([c["notes"][0]["vel"] for c in voice["chords"]], [100, 100, 30, 40, 40, 110, 110])

    def test_dynamics_use_bach_plain_syntax(self):
        self.assertIn("[20 p<f>p]", body(chord(0, (6000, 4000), dyn="p<f>p")))
        self.assertIn("[20 o << f]", body(chord(0, (6000, 500), dyn=" o  << f ")))
        self.assertIn("[20 p sub. <]", body(chord(0, (6000, 500), dyn="p sub. <")))
        for bad in ("loud!", "[p]", "p;f"):
            self.assertIn("invalid dynamic", error(one_voice(chord(0, (6000, 500), dyn=bad))), bad)
        self.assertIn("unknown articulation", error(one_voice(chord(0, (6000, 500), art="wobble"))))

    def test_clefs(self):
        clef = lambda **voice: normalize_score(one_voice(chord(0, (6000, 500)), **voice))["voices"][0]["clef"]  # noqa: E731
        self.assertEqual(clef(), "G")
        self.assertEqual(clef(name="Viola"), "Alto")
        self.assertEqual(clef(name="Viola", clef="treble"), "G")
        self.assertEqual(clef(clef="f15mb"), "F15mb")
        self.assertIn("unknown clef", error(one_voice(clef="Q")))

    def test_tonedivision_follows_the_pitches(self):
        division = lambda *cents: required_tonedivision(  # noqa: E731
            normalize_score(one_voice(*[chord(0, (c, 500)) for c in cents])))
        self.assertEqual(division(6000, 6100), 2)
        self.assertEqual(division(6000, 6050), 4)
        self.assertEqual(division(6050, 6225), 8)
        messages = score_messages(normalize_score(one_voice(chord(0, (6050, 500)))))
        self.assertEqual(messages[0], "tonedivision 4")
        self.assertTrue(messages[1].startswith("roll "))
        self.assertEqual(len(score_messages(normalize_score(one_voice(chord(0, (6000, 500)))))), 1)

    def test_markers(self):
        score = normalize_score({"markers": [{"onset": 4000, "name": "Part B"}, {"onset": 0, "name": "A"}],
                                 "voices": [{"chords": [chord(0, (6000, 500))]}]})
        self.assertIn("[markers [0 A] [4000 Part_B]]", score_to_llll(score))
        self.assertEqual(score_messages(score, add=True),
                         ["addchords [[0 [6000 500 80]]]", "addmarker 0 A", "addmarker 4000 Part_B"])
        self.assertIn("markers: A@0 Part_B@4000", summarize(score))

    def test_summary_is_in_bach_units(self):
        text = summarize(normalize_score(one_voice(chord(0, (5800, 500), (6100, 1500)), chord(1000, (6300, 250)))))
        self.assertEqual(text, "voice 1 clef G: 3 notes in 2 chords, 0-1500 ms, pitch 5800-6300. "
                               "Starts (pitch@onset): 5800+6100@0 6300@1000")


class DecodeTests(unittest.TestCase):
    def test_parse_handles_both_bracket_styles(self):
        self.assertEqual(parse_llll("roll [ 1. ( a 2 ) ]"), ["roll", [1.0, ["a", 2]]])
        self.assertEqual(parse_llll("[ `C5 `12 ]"), [["C5", "12"]])
        with self.assertRaises(ValueError):
            parse_llll("roll [ [ 1")

    def test_dump_to_json(self):
        dump = ("roll [clefs G F] [voicenames Flute nil] "
                "[ [ 0. [ 6000. 500. 100 [slots [20 mf] [22 staccato accent]] 0 ] 0 ] "
                "[ 500. [ 6400. 250. 90 0 ] [ 7300. 125. 60 0 ] 0 ] 0 ] [ 0 ]")
        score = llll_to_score(dump)
        self.assertEqual(score, {"voices": [
            {"voice": 1, "name": "Flute", "clef": "G", "chords": [
                {"onset": 0, "dyn": "mf", "art": ["staccato", "accent"],
                 "notes": [{"pitch": 6000, "dur": 500, "vel": 100}]},
                {"onset": 500, "notes": [{"pitch": 6400, "dur": 250, "vel": 90},
                                         {"pitch": 7300, "dur": 125, "vel": 60}]},
            ]},
            {"voice": 2, "clef": "F", "chords": []},
        ]})
        self.assertEqual(count_notes(score), 3)

    def test_bach_pitch_names_come_back_as_midicents(self):
        # bach outputs a name instead of cents for notes with a user-defined spelling; its C5 is middle C.
        for token, cents in (("C5", 6000), ("Db5", 6100), ("Cq5", 6050), ("Bbd5", 6950),
                             ("A^5", 6925), ("Fx4", 5500), ("C5+1/16t", 6012.5), ("A5-33/200t", 6867)):
            self.assertEqual(bach_pitch_to_cents(token), cents, token)
        dump = "roll [ [ 0. [ Db5 500. 100 0 ] [ Cq5 500. 100 0 ] [ 6050.5 500. 100 0 ] 0 ] 0 ]"
        notes = llll_to_score(dump)["voices"][0]["chords"][0]["notes"]
        self.assertEqual([n["pitch"] for n in notes], [6100, 6050, 6050.5])

    def test_dynamics_in_every_bach_output_mode(self):
        note = "roll [ [ 0. [ 6000. 500. 100 [ slots [ 20 %s ] ] 0 ] 0 ] 0 ]"
        cases = {
            # dynamicsoutputmode 2, full (bach's default)
            "[ [ auto 0 0. ] mf = ]": "mf",
            "[ [ auto 0 0. ] p < ]": "p<",
            "[ [ auto 0 0. ] f < ] [ [ auto 0 0.5 ] fff > ] [ [ auto 0 1. ] mp = ]": "f<fff>mp",
            "[ [ auto 0 0. ] f > ] [ [ breakpoint 1 0.306341 ] p < ] [ [ auto 0 1. ] niente = ]": "f > @1 p < niente",
            # dynamicsoutputmode 1, structured (also what a saved patch holds)
            "[ auto [ p subito ] < ] [ auto ff >> ] [ auto o = ]": "p subito < ff >> o",
            "[ auto p < ] [ auto [ fff tenuto ] = ] [ 0.8 [ ] > ] [ auto mp = ]": "p < fff tenuto = 0.8 > mp",
            "[ auto pp < ] [ auto [ ] = ]": "pp<|",
            # dynamicsoutputmode 0, plain
            "p<": "p<",
            "o << f >> o": "o<<f>>o",
            "p cresc _": "p cresc _",
        }
        for slot, expected in cases.items():
            decoded = llll_to_score(note % slot)["voices"][0]["chords"][0]
            self.assertEqual(decoded["dyn"], expected, slot)
            normalize_score(one_voice(decoded))  # what bach returns is valid input again

    def test_chord_marks_are_collected_from_any_note(self):
        dump = ("roll [ [ 500. [ 3600. 4000. 85 [ slots [ 22 stacc ] ] 0 ] "
                "[ 6400. 1000. 50 [ slots [ 20 [ [ auto 0 0. ] mf = ] ] [ 22 staccato acc ] [ 24 pizz. ] ] 0 ] "
                "[ name paul ] 0 ] 0 ]")
        self.assertEqual(llll_to_score(dump)["voices"][0]["chords"], [
            {"onset": 500, "dyn": "mf", "art": ["staccato", "accent"], "text": "pizz.",
             "notes": [{"pitch": 3600, "dur": 4000, "vel": 85}, {"pitch": 6400, "dur": 1000, "vel": 50}]},
        ])

    def test_real_bach_dump_shapes(self):
        # Shapes taken from the bach help patches: breakpoints with velocities,
        # text slots with spaces, slots given by name, short articulation names.
        dump = ("roll [ markers [ 510. [ marker 1 ] none ] [ 2000. `A1 none ] ] "
                "[ [ 688.571 [ 7600. 1276.57 126 [ breakpoints [ 0. 0. 0. 126 ] [ 0.183787 0. 0. 6 ] "
                "[ 0.679181 -200. 0. 127 ] [ 1. 600. 0.5 60 ] ] 0 ] 0 ] "
                "[ 2000. [ 7100. 1049. 100 [ slots [ 24 molto pont. ] [ notehead diam ] "
                "[ articulations port mart trem3 ] [ 5 68 ] ] [ name pippo ] 2 ] 0 ] "
                "[ 4000. [ 6200. 1000. 100 [ breakpoints [ 0. 0. 0. ] [ 1. -1200. 0. ] ] 0 ] 0 ] 0 ]")
        score = llll_to_score(dump)
        first, second, third = score["voices"][0]["chords"]
        self.assertEqual(first["onset"], 688.571)
        self.assertEqual(first["notes"][0]["dur"], 1276.57)
        self.assertEqual(first["notes"][0]["gliss"], [[0.1838, 0], [0.6792, -200], [1, 600, 0.5]])
        self.assertEqual(second["text"], "molto pont.")
        self.assertEqual(second["art"], ["tenuto", "marcato", "tremolo"])
        self.assertEqual(second["notes"][0]["head"], "diamond")
        self.assertEqual(third["notes"][0]["gliss"], -1200)
        self.assertEqual(score["markers"], [{"onset": 510, "name": "marker 1"}, {"onset": 2000, "name": "A1"}])

    def test_round_trip(self):
        source = {"markers": [{"onset": 2000, "name": "B"}], "voices": [
            {"name": "A", "chords": [
                chord(0, (6200, 500), dyn="p<"),
                chord(2000, (6500, 1500), (6800, 1500), (6950, 3000, {"head": "diamond"}),
                      art=["tenuto", "accent"], text="sul tasto"),
                chord(5000, (6600, 1000), dyn="f>pp", lyric="ah")]},
            {"name": "B", "chords": [
                chord(0, (3600, 4000, {"gliss": -200})),
                chord(4000, (3600, 2000, {"gliss": [[0.25, 500, -0.3], [1, 0]], "vel": 12}))]}]}
        canonical = normalize_score(source)
        decoded = llll_to_score(score_to_llll(canonical))
        self.assertEqual(score_to_llll(normalize_score(decoded)), score_to_llll(canonical))
        # and the decoded JSON is the JSON that was written, plus what the translator filled in
        self.assertEqual(decoded["voices"][0]["chords"][1], {
            "onset": 2000, "art": ["tenuto", "accent"], "text": "sul tasto",
            "notes": [{"pitch": 6500, "dur": 1500, "vel": 55}, {"pitch": 6800, "dur": 1500, "vel": 55},
                      {"pitch": 6950, "dur": 3000, "vel": 55, "head": "diamond"}]})


class SkillTests(unittest.TestCase):
    def setUp(self):
        with open(SKILL, encoding="utf-8") as handle:
            self.text = handle.read()

    def test_every_example_in_the_skill_is_a_valid_score(self):
        blocks = re.findall(r"```json\n(.*?)```", self.text, re.S)
        self.assertGreaterEqual(len(blocks), 6)
        for block in blocks:
            data = json.loads(block)
            if "voices" not in data:  # the bare chord that introduces the format
                data = one_voice(data)
            canonical = normalize_score(data)
            back = normalize_score(llll_to_score(score_to_llll(canonical)))
            self.assertEqual(score_to_llll(back), score_to_llll(canonical), block)

    def test_the_worked_example_follows_its_own_table(self):
        last = json.loads(re.findall(r"```json\n(.*?)```", self.text, re.S)[-1])
        chords = last["voices"][0]["chords"]
        self.assertEqual([c["onset"] for c in chords], [n * 250 for n in range(9)])
        self.assertEqual([c["notes"][0]["pitch"] for c in chords],
                         [6200, 6500, 6900, 6700, 7100, 6400, 7300, 6600, 6900])

    def test_pitch_table_is_in_midicents(self):
        rows = re.findall(r"^  (\d) ((?: +\d+){12})$", self.text, re.M)
        self.assertEqual(len(rows), 7)
        for octave, cells in rows:
            self.assertEqual([int(c) for c in cells.split()],
                             [(int(octave) + 1) * 1200 + i * 100 for i in range(12)])

    def test_inline_values_named_in_the_skill_are_accepted(self):
        section = lambda key: re.split(r"\n- |\n\n", self.text.split(f'- Optional `"{key}"`:', 1)[1], 1)[0]  # noqa: E731
        for art in re.findall(r'"([a-z]+)"', section("art")):
            normalize_score(one_voice(chord(0, (6000, 500), art=art)))
        for dyn in re.findall(r'"([a-z<>]+)"', section("dyn")):
            normalize_score(one_voice(chord(0, (6000, 500), dyn=dyn)))
        for head in re.findall(r'`"([a-z]+)"`', section("head")):
            normalize_score(one_voice(chord(0, (6000, 500, {"head": head}))))

    def test_the_skill_never_teaches_other_units(self):
        for block in re.findall(r"```json\n(.*?)```", self.text, re.S):
            self.assertNotRegex(block, r'"(t|beat|bpm|rest)"')
            self.assertNotRegex(block, r'"pitch": ("|\d{1,3}[,}\s])')


class ComposeTests(unittest.TestCase):
    """compose.py is not exposed to the model; it still thinks in note names and beats."""

    def test_helpers(self):
        self.assertEqual(scale("C4", "major", 8), [60, 62, 64, 65, 67, 69, 71, 72])
        self.assertEqual(euclid(3, 8), [1, 0, 0, 1, 0, 0, 1, 0])

    def test_program_builds_voices(self):
        raw = run_program(
            "voice(2, 'Bass')\n"
            "for p in scale('D4', 'dorian', 4): note(p, 0.5)\n"
            "rest(1, voice=2)\nnote('D2', 2, voice=2)\n", bpm=100)
        self.assertEqual(sum(len(v["notes"]) for v in raw["voices"]), 5)
        self.assertEqual(raw["voices"][1]["name"], "Bass")
        self.assertEqual(raw["voices"][1]["notes"][0]["t"], 1)
        self.assertEqual(raw["voices"][0]["notes"][3]["t"], 1.5)

    def test_seed_is_reproducible(self):
        code = "for i in range(8): note(rnd.choice(scale('C4', 'pentatonic', 5)), 0.25)"
        self.assertEqual(run_program(code, seed=3), run_program(code, seed=3))

    def test_restrictions_and_errors(self):
        for bad in ("import os", "note.__globals__", "open('x')", "while True: pass", "x = 1"):
            with self.assertRaises(ScoreError, msg=bad):
                run_program(bad)
        with self.assertRaises(ScoreError) as ctx:
            run_program("note('C4')\nnote(undefined_name)")
        self.assertIn("line 2", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
