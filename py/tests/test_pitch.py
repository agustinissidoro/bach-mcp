"""The pitch functions and the answers of the pitch tools."""

import json
import os
import re
import unittest

from bach_mcp import pitch
from bach_mcp.pitch import CHORDS, SCALES, PitchError, tidy
from bach_mcp.pitch_tools import FUNCTIONS, PITCH_TOOLS, call_pitch_tool


def call(name, **arguments):
    return json.loads(call_pitch_tool(name, arguments))


class ReadingTests(unittest.TestCase):
    def test_names_and_numbers_in_any_shape(self):
        self.assertEqual(call("p2mc", pitches="Db4"), 6100)
        self.assertEqual(call("p2mc", pitches=["C4", 6400, "G4"]), [6000, 6400, 6700])
        self.assertEqual(call("p2mc", pitches=[["C4", "E4"], ["G3"]]), [[6000, 6400], [5500]])

    def test_the_forms_a_model_sends(self):
        self.assertEqual(call("p2mc", pitches="D4 F4 A4"), [6200, 6500, 6900])
        self.assertEqual(call("p2mc", pitches="D4, F4, A4"), [6200, 6500, 6900])
        self.assertEqual(call("p2mc", pitches='["D4", "F4"]'), [6200, 6500])
        self.assertEqual(call("p2mc", pitches=["db4", "f#4", "bb3"]), [6100, 6600, 5800])
        self.assertIn("write flats as b", call_pitch_tool("p2mc", {"pitches": ["D♭4"]}))
        self.assertIn("'F#4'", call_pitch_tool("p2mc", {"pitches": "F♯4"}))

    def test_octaves_change_at_c_and_microtones_add_cents(self):
        self.assertEqual(call("p2mc", pitches=["B3", "C4", "Cb4", "B#3"]), [5900, 6000, 5900, 6000])
        self.assertEqual(call("p2mc", pitches=["E4-14", "C4+50", "Bb4-31"]), [6386, 6050, 6969])

    def test_errors_say_what_a_pitch_is(self):
        self.assertIn("is not a pitch", call_pitch_tool("p2mc", {"pitches": "H4"}))
        self.assertIn("add the octave", call_pitch_tool("p2mc", {"pitches": "Db"}))
        self.assertTrue(call_pitch_tool("transpose", {"pitches": "C4"}).startswith("ERROR:"))

    def test_mc2p_names_the_numbers(self):
        self.assertEqual(call("mc2p", midicents=[6100, 6386.31, 6050]), ["C#4", "E4-13.69", "C4+50"])


class AnswerTests(unittest.TestCase):
    def test_every_answer_is_one_json_value_with_whole_numbers_plain(self):
        text = call_pitch_tool("transpose", {"pitches": [6000.0, 6050.5], "cents": 100})
        self.assertEqual(text, "[6100, 6150.5]")
        self.assertEqual(call_pitch_tool("get_midicents", {"values": ["5/4"], "unit": "ratio", "reference": "C4"}),
                         "[6386.31]")

    def test_the_shape_is_kept(self):
        self.assertEqual(call("transpose", pitches=[[6000, 6400], [6700]], cents=-1200), [[4800, 5200], [5500]])
        self.assertEqual(call("mirror", pitches=[[6000, 6400], 6700], axis="C4"), [[6000, 5600], 5300])
        self.assertEqual(call("force_scale", pitches=[[6100], 6300], scale="major", root="C"), [[6000], 6200])

    def test_the_tools_are_the_pitch_tools_of_score_mode(self):
        from bach_mcp.modes import MODE_TOOLS
        self.assertEqual(set(FUNCTIONS), set(PITCH_TOOLS))
        self.assertTrue(set(PITCH_TOOLS) <= set(MODE_TOOLS["score"]))
        self.assertFalse(set(PITCH_TOOLS) & set(MODE_TOOLS["algo"]))


class TransformTests(unittest.TestCase):
    line = ["C4", "E4", "G4", "F#4", "B4"]

    def test_transpose(self):
        self.assertEqual(call("transpose", pitches=["D4", "F4"], cents=[-1200, -500]), [4500, 4800])
        self.assertEqual(call("transpose", pitches="D4", cents="-1200 -500"), 4500)
        self.assertTrue(call_pitch_tool("transpose", {"pitches": "D4", "cents": []}).startswith("ERROR:"))
        self.assertEqual(call("transpose", pitches=self.line, cents=-400), [5600, 6000, 6300, 6200, 6700])
        self.assertEqual(call("transpose", pitches=self.line, cents=50), [6050, 6450, 6750, 6650, 7150])

    def test_reverse_is_the_retrograde(self):
        self.assertEqual(call("reverse", pitches=self.line), [7100, 6600, 6700, 6400, 6000])
        self.assertEqual(call("reverse", pitches=[["C4", "E4"], "G4"]), [6700, [6000, 6400]])

    def test_mirror_around_an_axis_or_the_first_pitch(self):
        self.assertEqual(call("mirror", pitches=self.line, axis="C4"), [6000, 5600, 5300, 5400, 4900])
        self.assertEqual(call("mirror", pitches=["E4", "G4"]), [6400, 6100])
        self.assertEqual(call("mirror", pitches=["E4"], axis=6050), [5700])

    def test_force_scale_to_a_library_scale_or_given_pitches(self):
        self.assertEqual(call("force_scale", pitches=["C#4", "D#4", "F#4", "G#4", "A#4"], scale="major", root="C"),
                         [6000, 6200, 6500, 6700, 6900])
        self.assertEqual(call("force_scale", pitches=["C#4", "D#4"], scale="major", root="D"), [6100, 6200])
        self.assertEqual(call("force_scale", pitches=[6100, 6900, 4000], scale="C E G"), [6000, 6700, 4000])
        self.assertEqual(call("force_scale", pitches=[6030], scale="rast", root="C4"), [6000])
        self.assertEqual(call("force_scale", pitches=[6330], scale="rast", root="C4"), [6350])


class LibraryTests(unittest.TestCase):
    def test_chords(self):
        self.assertEqual(call("get_chord", root="Db4", chord="major"), [6100, 6500, 6800])
        self.assertEqual(call("get_chord", root="Bb3", chord="half_diminished7"), [5800, 6100, 6400, 6800])
        self.assertEqual(call("get_chord", root="Eb4", chord="7b9"), [6300, 6700, 7000, 7300, 7600])
        self.assertEqual(call("get_chord", root="C4", chord="mystic"), [6000, 6600, 7000, 7600, 8100, 8600])

    def test_symbols_where_case_matters(self):
        self.assertEqual(call("get_chord", root="C4", chord="M7"), [6000, 6400, 6700, 7100])
        self.assertEqual(call("get_chord", root="C4", chord="m7"), [6000, 6300, 6700, 7000])
        self.assertEqual(call("get_chord", root="C4", chord="Dominant 7"), [6000, 6400, 6700, 7000])

    def test_inversions_and_several_roots(self):
        self.assertEqual(call("get_chord", root="C4", chord="major", inversion=1), [6400, 6700, 7200])
        self.assertEqual(call("get_chord", root="C4", chord="major", inversion=2), [6700, 7200, 7600])
        self.assertEqual(call("get_chord", root="C4", chord="dominant9", inversion=1), [6400, 6700, 7000, 7200, 7400])
        self.assertEqual(call("get_chord", root=["C4", "F4"], chord="minor"), [[6000, 6300, 6700], [6500, 6800, 7200]])

    def test_just_chords_are_exact(self):
        self.assertEqual(call("get_chord", root="C4", chord="harmonic7"), [6000, 6386.31, 6701.96, 6968.83])

    def test_scales(self):
        self.assertEqual(call("get_scale", root="E3", scale="harmonic minor"),
                         [5200, 5400, 5500, 5700, 5900, 6000, 6300, 6400])
        self.assertEqual(call("get_scale", root="C4", scale="whole_tone", direction="down"),
                         [7200, 7000, 6800, 6600, 6400, 6200, 6000])
        up_down = call("get_scale", root="C4", scale="major_pentatonic", octaves=2, direction="updown")
        self.assertEqual(up_down[:11], [6000, 6200, 6400, 6700, 6900, 7200, 7400, 7600, 7900, 8100, 8400])
        self.assertEqual(up_down[10:], up_down[:11][::-1])
        self.assertEqual(call("get_scale", root="C4", scale="rast"), [6000, 6200, 6350, 6500, 6700, 6900, 7050, 7200])
        self.assertEqual(call("get_scale", root="C4", scale="edo19")[1], 6063.16)
        self.assertEqual(call("get_scale", root="C4", scale="bohlen_pierce")[-1], 7901.96)

    def test_unknown_names_suggest_close_ones_and_list_gives_them_all(self):
        text = call_pitch_tool("get_scale", {"root": "C4", "scale": "dorain"})
        self.assertTrue(text.startswith("ERROR:") and "dorian" in text)
        self.assertIn("half_diminished7", call_pitch_tool("get_chord", {"root": "C4", "chord": "list"}))
        self.assertIn("edoN", call_pitch_tool("get_scale", {"root": "C4", "scale": "list"}))

    def test_every_library_entry_starts_at_the_root_and_rises(self):
        for name, steps in list(CHORDS.items()) + list(SCALES.items()):
            self.assertEqual(steps[0], 0, name)
            self.assertEqual(steps, sorted(steps), name)
            self.assertEqual(len(set(steps)), len(steps), name)
        for name, steps in SCALES.items():
            self.assertLess(steps[-1], pitch.PERIODS.get(name, 1200), name)

    def test_tuned_pitches(self):
        self.assertEqual(call("get_midicents", values=[1, 2, 3, 4, 5, 6, 7, 8], unit="harmonic", reference="C2"),
                         [3600, 4800, 5501.96, 6000, 6386.31, 6701.96, 6968.83, 7200])
        self.assertEqual(call("get_midicents", values="1 5/4 3/2", unit="ratio", reference="A4"), [6900, 7286.31, 7601.96])
        self.assertEqual(call("get_midicents", values=[440, 880], unit="hz"), [6900, 8100])


class SkillTests(unittest.TestCase):
    def test_every_tool_example_in_the_skill_is_the_real_answer(self):
        path = os.path.join(os.path.dirname(pitch.__file__), "BACH_SKILL.md")
        with open(path, encoding="utf-8") as f:
            text = re.sub(r"\s*\n\s*", " ", f.read())
        examples = re.findall(r"`(\w+)\(([^`]*)\)` → `([^`]*)`", text)
        self.assertGreaterEqual(len(examples), 1)
        for name, args, shown in examples:
            self.assertIn(name, FUNCTIONS)
            values = json.loads(f"[{args}]")
            self.assertEqual(FUNCTIONS[name](*values), shown, f"{name}({args})")

    def test_every_tool_description_example_is_the_real_answer(self):
        for name, fn in FUNCTIONS.items():
            m = re.search(r"Example: \w+\((.*)\) -> (.*)$", fn.__doc__, re.M)
            self.assertIsNotNone(m, name)
            self.assertEqual(fn(*json.loads(f"[{m.group(1)}]")), m.group(2), name)


if __name__ == "__main__":
    unittest.main()
