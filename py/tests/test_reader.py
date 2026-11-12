"""What the model is shown of a score (music/reader.py): the same syntax, without what says nothing.
Run: python -m unittest discover -s py/tests"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.music.reader import count_notes, describe, lean, number, read_view  # noqa: E402

SCORE = {
    "header": {
        "slotinfo": {"1": {"name": ["amplitude envelope"], "type": ["function"], "range": [0.0, 127.0]},
                     "7": {"name": ["sample"], "type": ["text"], "width": [100.0]},
                     "20": {"name": ["dynamics"], "type": ["dynamics"], "access": ["readandwrite"]}},
        "commands": {"1": {"name": ["command"]}},
        "clefs": ["G", "F"], "keys": ["CM", "CM"], "voicenames": [["Flute"], []], "voicespacing": [0.0, 17.0, 17.0],
        "hidevoices": [0, 0], "groups": [], "stafflines": [5, 5], "midichannels": [1, 2], "numparts": [1, 1],
        "loop": [0.0, 0.0],
        "markers": [{"onset": 0.0, "name": [], "role": "timesig", "content": [[2, 2, 3], 8]},
                    {"onset": 1500.0, "name": ["B", 2], "role": "none"}],
    },
    "voices": [
        {"chords": [
            {"onset": 0.0, "notes": [
                {"pitch": 7200.0, "dur": 500.0, "vel": 100, "slots": {"20": ["p<"], "7": ["a.wav"]}, "flag": 0},
                {"pitch": 7650.0, "dur": 333.333333, "vel": 100, "breakpoints": [[0.0, 0.0, 0.0], [1.0, 200.0, 0.0]],
                 "articulations": [], "name": ["x"], "flag": 16}], "name": [], "flag": 0},
            {"onset": 1000.0, "notes": [{"pitch": 7400.0, "dur": 500.0, "vel": 100, "flag": 0}], "flag": 0}],
         "flag": 2},
        {"chords": [], "flag": 0},
    ],
}


class LeanTests(unittest.TestCase):
    def test_the_same_syntax_without_what_says_nothing(self):
        self.assertEqual(lean(SCORE), {
            "header": {"clefs": ["G", "F"], "keys": ["CM", "CM"], "voicenames": [["Flute"], []],
                       "markers": [{"onset": 0, "name": [], "role": "timesig", "content": [[2, 2, 3], 8]},
                                   {"onset": 1500, "name": ["B", 2], "role": "none"}],
                       "slotinfo": {"7": {"name": ["sample"], "type": ["text"]},
                                    "20": {"name": ["dynamics"], "type": ["dynamics"]}}},
            "voices": [
                {"flag": 2, "chords": [
                    {"onset": 0, "notes": [
                        {"pitch": 7200, "dur": 500, "vel": 100, "slots": {"20": ["p<"], "7": ["a.wav"]}},
                        {"pitch": 7650, "dur": 333.33, "vel": 100, "breakpoints": [[0, 0, 0], [1, 200, 0]],
                         "name": ["x"], "flag": 16}]},
                    {"onset": 1000, "notes": [{"pitch": 7400, "dur": 500, "vel": 100}]}]},
                {"chords": []}]})

    def test_the_score_is_left_as_it_was(self):
        before = json.dumps(SCORE)
        lean(SCORE)
        read_view(SCORE, voice=1, from_ms=500)
        self.assertEqual(json.dumps(SCORE), before)

    def test_numbers(self):
        self.assertEqual([number(6000.0), number(0.126), number(333.336), number("1/4"), number(True)],
                         [6000, 0.13, 333.34, "1/4", True])

    def test_a_score_without_a_header(self):
        self.assertEqual(lean({"voices": [{"chords": []}]}), {"voices": [{"chords": []}]})


class ReadViewTests(unittest.TestCase):
    def test_a_window_keeps_every_voice_in_its_place_and_only_its_markers(self):
        lines = read_view(SCORE, from_ms=500).splitlines()
        self.assertEqual(lines[0], "voice 1 (Flute): 3 notes in 2 chords, 0-1500 ms, pitch 7200-7650, clef G, muted")
        self.assertEqual(lines[3], "markers: timesig@0 B 2@1500")
        self.assertEqual(lines[4], "Shown: all voices, 500 ms to the end. A voice with no chords here is only not shown.")
        shown = json.loads(lines[5])
        self.assertEqual([len(v["chords"]) for v in shown["voices"]], [1, 0])
        self.assertEqual(shown["header"]["markers"], [{"onset": 1500, "name": ["B", 2], "role": "none"}])
        self.assertNotIn("slotinfo", shown["header"], "only the slots of the notes shown")

    def test_nothing_in_the_window(self):
        self.assertTrue(read_view(SCORE, voice=2).endswith("No notes in voice 2."))
        self.assertTrue(read_view(SCORE, from_ms=5000).endswith("No notes in the score in this window."))

    def test_describe_and_count(self):
        self.assertEqual(count_notes(SCORE), 3)
        self.assertEqual(describe(SCORE), "voice 1 (Flute): 3 notes in 2 chords, 0-1500 ms, pitch 7200-7650\n"
                                          "voice 2: empty\nmarkers: timesig@0 B 2@1500")


if __name__ == "__main__":
    unittest.main()
