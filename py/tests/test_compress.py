"""The compressed form of bachjson-complete, for the model. Run: python -m unittest discover -s py/tests"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.music.compress import compress, expand, number  # noqa: E402

COMPLETE = {
    "header": {
        "slotinfo": {"20": {"name": ["dynamics"], "type": ["dynamics"]},
                     "22": {"name": ["articulations"], "type": ["articulations"]},
                     "3": {"name": ["amp"], "type": ["function"], "range": [0, 1]}},
        "commands": {"1": {"note": ["note"], "chord": ["chord"], "rest": ["rest"], "key": [0]}},
        "clefs": ["G", "F"], "keys": ["CM", "CM"],
        "voicenames": [["Flute"], []],
        "markers": [{"onset": 0.0, "name": ["A"], "role": "none"},
                    {"onset": 1500.0, "name": ["B"], "role": "tempo", "content": ["1/4", 60]}],
        "midichannels": [1, 2],
    },
    "voices": [
        {"chords": [
            {"onset": 0.0, "notes": [{"pitch": 6000.0, "dur": 500.0, "vel": 100, "flag": 0},
                                     {"pitch": 6400.0, "dur": 500.0, "vel": 100, "flag": 0}], "flag": 0},
            {"onset": 333.333333, "notes": [{"pitch": 6100.0, "spelling": "Db5", "dur": 1000.0, "vel": 90,
                                             "breakpoints": [[0.0, 0.0, 0.0], [1.0, 200.0, 0.0]],
                                             "slots": {"20": ["p<"], "22": ["staccato", "accent"],
                                                       "3": [[0.0, 0.0, 0.0], [1.0, 1.0, 0.0]]},
                                             "flag": 2}],
             "name": ["paul"], "flag": 0},
        ], "flag": 0},
        {"chords": [{"onset": 0.0, "notes": [{"pitch": 3600.0, "dur": 1500.0, "vel": 80, "flag": 0}], "flag": 0}],
         "flag": 0},
    ],
}


class CompressTests(unittest.TestCase):
    def test_gliss(self):
        from bach_mcp.music.compress import breakpoints, gliss
        self.assertEqual(gliss([[0, 0, 0], [1, 200, 0]]), 200)
        self.assertEqual(gliss([[0, 0, 0], [0.5, 300, 0], [1, -200, 0.5]]), [[0.5, 300], [1, -200, 0.5]])
        self.assertEqual(breakpoints(200), [[0, 0, 0], [1, 200, 0]])
        self.assertEqual(breakpoints([[0.5, 300], [1, -200, 0.5]]), [[0, 0, 0], [0.5, 300, 0], [1, -200, 0.5]])

    def test_linked_slots_have_names_without_slotinfo(self):
        bare = {"voices": [{"chords": [{"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "vel": 80,
                                                                "slots": {"20": ["mf"]}}]}]}]}
        self.assertEqual(compress(bare)["voices"][0]["chords"][0][1][3], {"dynamics": "mf"})
        self.assertEqual(expand(compress(bare))["voices"][0]["chords"][0]["notes"][0]["slots"], {"20": ["mf"]})

    def test_the_compressed_form(self):
        short = compress(COMPLETE)
        self.assertEqual(short, {
            "slots": {"3": "amp"},
            "markers": [[0, "A"], [1500, "B", "tempo", ["1/4", 60]]],
            "voices": [
                {"name": "Flute", "chords": [
                    [0, [6000, 500, 100], [6400, 500, 100]],
                    [333.33, [6100, 1000, 90, {"dynamics": "p<", "articulations": ["staccato", "accent"],
                                               "amp": [[0, 0, 0], [1, 1, 0]],
                                               "gliss": 200, "spelling": "Db5", "flag": 2}],
                     {"name": ["paul"]}],
                ]},
                {"chords": [[0, [3600, 1500, 80]]]},
            ],
        })

    def test_it_is_much_smaller(self):
        full = len(json.dumps(COMPLETE, separators=(",", ":")))
        short = len(json.dumps(compress(COMPLETE), separators=(",", ":")))
        self.assertLess(short, full * 0.6, f"{short} of {full} characters")

    def test_numbers(self):
        self.assertEqual([number(6000.0), number(333.3333), number(0.5), number(7), number("x")],
                         [6000, 333.33, 0.5, 7, "x"])

    def test_back_to_complete_keeps_what_was_not_shown(self):
        back = expand(compress(COMPLETE), COMPLETE)
        self.assertEqual(back["header"]["slotinfo"], COMPLETE["header"]["slotinfo"])
        self.assertEqual(back["header"]["commands"], COMPLETE["header"]["commands"])
        self.assertEqual(back["header"]["clefs"], ["G", "F"])
        self.assertEqual(back["header"]["voicenames"], [["Flute"], []])
        self.assertEqual(back["header"]["markers"][1],
                         {"onset": 1500, "name": ["B"], "role": "tempo", "content": ["1/4", 60]})
        note = back["voices"][0]["chords"][1]["notes"][0]
        self.assertEqual(note["slots"], {"20": ["p<"], "22": ["staccato", "accent"], "3": [[0, 0, 0], [1, 1, 0]]})
        self.assertEqual((note["spelling"], note["flag"], note["breakpoints"]), ("Db5", 2, [[0, 0, 0], [1, 200, 0]]))
        self.assertEqual(back["voices"][0]["chords"][1]["name"], ["paul"])
        self.assertEqual(back["voices"][0]["chords"][1]["onset"], 333.33, "two decimals")

    def test_what_the_model_writes_comes_back(self):
        written = {"voices": [{"name": "Oboe", "chords": [[0, [6200, 250, 70, {"dynamics": "mf"}]],
                                                         [250, [6400, 250, 70], [6700, 250, 70]]]}]}
        back = expand(written, COMPLETE)
        self.assertEqual(back["header"]["voicenames"], [["Oboe"]])
        self.assertEqual(back["voices"][0]["chords"][0]["notes"][0]["slots"], {"20": ["mf"]})
        self.assertEqual(len(back["voices"][0]["chords"][1]["notes"]), 2)
        self.assertEqual(compress(back)["voices"], written["voices"], "and compresses to what was written")


if __name__ == "__main__":
    unittest.main()
