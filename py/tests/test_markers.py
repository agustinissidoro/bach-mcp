"""Markers with a role: how bach.quantize reads them (music/markers.py), write_markers, what the
score and algorithm tools answer about them, and the quantizer skill.
Run: python -m unittest discover -s py/tests"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.bridge import buffer as buffer_module  # noqa: E402
from bach_mcp.music.markers import check, measures, ordered, report  # noqa: E402
from bach_mcp.prompt.modes import instance_skill  # noqa: E402
from bach_mcp.prompt.skill import QUANTIZER_SKILL_PATH  # noqa: E402
from bach_mcp.prompt.skills import compile_skill  # noqa: E402
from bach_mcp.tools.algo_tools import check_algorithm  # noqa: E402
from bach_mcp.tools.playground import prepare  # noqa: E402
from bach_mcp.tools.score_tools import check_markers, register_score_tools  # noqa: E402
from bach_mcp.tools.session import Target, serve_targets  # noqa: E402
from test_algo import NODE, needs_node  # noqa: E402
from test_buffer import ROLL, FakeMax, FakeMCP  # noqa: E402


def mk(onset, role, content=None):
    return {"onset": onset, "name": [], "role": role, **({"content": content} if content is not None else {})}


FOUR = [mk(0, "timesig", [4, 4]), mk(2000, "barline"), mk(4000, "barline")]
SEVEN = [mk(0, "timesig", [[2, 2, 3], 8]), mk(250, "subdivision"), mk(500, "division"), mk(750, "subdivision"),
         mk(1000, "division"), mk(1250, "subdivision"), mk(1500, "subdivision"), mk(1750, "barline")]


class ReadingTests(unittest.TestCase):
    def test_measures_and_their_tempo(self):
        self.assertEqual(report(FOUR), "Measures, as bach.quantize will read the markers (2):\n"
                                       "  measures 1-2, from 0 ms: 4/4, 2000 ms (quarter = 120) each\n"
                                       "  the barline at 4000 ms closes measure 2; for music after it, bach repeats the measures given.")
        self.assertEqual(check(FOUR), ([], []))

    def test_a_pickup_beats_and_an_additive_meter(self):
        beats = [mk(500, "timesig", [3, 4]), mk(1000, "division"), mk(1600, "division"), mk(2300, "barline")]
        text = report(beats)
        self.assertIn("what comes before 500 ms is a pickup", text)
        self.assertIn("measure 1, from 500 ms: 3/4, 1800 ms (quarter = 100), 3 beats", text)
        self.assertEqual(check(beats), ([], []))
        self.assertIn("measure 1, from 0 ms: 2+2+3/8, 1750 ms (eighth = 240), 3 beats", report(SEVEN))
        self.assertEqual(check(SEVEN), ([], []))
        self.assertEqual(measures(SEVEN)[0]["units"], [2, 2, 3])

    def test_order_at_one_onset(self):
        mixed = [mk(0, "barline"), mk(0, "tempo", ["1/4", 60]), mk(0, "none")]
        self.assertEqual([m["role"] for m in ordered(mixed)], ["tempo", "barline", "none"])

    def test_no_role_no_report(self):
        self.assertEqual(report([{"onset": 0, "name": ["A"], "role": "none"}]), "")

    def test_what_bach_would_misread_is_an_error(self):
        cases = [
            ([mk(0, "timesig", [4, 4]), mk(0, "barline"), mk(2000, "barline")], "a timesig is already the barline of its measure"),
            ([mk(0, "timesig", [4, 3]), mk(2000, "barline")], "its content is the time signature"),
            ([mk(0, "timesig"), mk(2000, "barline")], "its content is the time signature"),
            ([mk(0, "tempo", [60, "1/4"]), mk(0, "barline"), mk(2000, "barline")], 'its content is [figure, value], e.g. ["1/4", 60]'),
            ([mk(0, "barline", [4, 4]), mk(2000, "barline")], "a barline has no content"),
            ([mk(0, "barline"), mk(0, "division"), mk(2000, "barline")], "the first beat of a measure is its barline"),
            ([mk(0, "timesig", [7, 8]), mk(500, "division"), mk(750, "subdivision"), mk(1750, "barline")],
             "1+2 = 3 units, which does not divide the numerator 7"),
            ([mk(500, "division")], "without any barline or timesig"),
        ]
        for markers, expected in cases:
            errors, _ = check(markers)
            self.assertTrue(errors and expected in errors[0], (expected, errors))
            self.assertIn(expected, check_markers(markers))

    def test_what_may_not_be_meant_is_a_warning(self):
        five = [mk(0, "timesig", [4, 4])] + [mk(t, "division") for t in (400, 800, 1200, 1600)] + [mk(2000, "barline")]
        errors, warnings = check(five)
        self.assertEqual(errors, [])
        self.assertIn("a measure of n beats has n - 1 division markers", warnings[0])
        self.assertIn("only one barline or timesig", check([mk(0, "timesig", [4, 4])])[1][0])
        self.assertIn("the groups 2+2+3 need a division at each group", check([mk(0, "timesig", [[2, 2, 3], 8]), mk(1750, "barline")])[1][0])


class WriteMarkersTests(unittest.TestCase):
    def setUp(self):
        self.folder = prepare(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.target = Target("notes1", "score", self.folder)
        serve_targets(lambda: self.target)
        self.addCleanup(serve_targets, None)
        self.max = FakeMax(self.target.scores)
        saved = buffer_module.BUFFER_FILE
        buffer_module.BUFFER_FILE = os.path.join(self.folder, "buffer.json")
        self.addCleanup(setattr, buffer_module, "BUFFER_FILE", saved)
        mcp = FakeMCP()
        register_score_tools(mcp, self.max)
        self.tools = mcp.tools

    def test_the_markers_change_and_the_notes_stay(self):
        reply = self.tools["write_markers"](markers=[{"onset": 2000, "role": "barline"}, {"onset": 0, "role": "timesig", "content": [4, 4]}])
        self.assertTrue(reply.startswith("OK. 2 markers written; the notes are as they were.\nMeasures, as bach.quantize"), reply)
        self.assertIn("measure 1, from 0 ms: 4/4, 2000 ms (quarter = 120)", reply)
        self.assertEqual(self.max.score["header"]["markers"], [mk(0, "timesig", [4, 4]), mk(2000, "barline")])
        self.assertEqual(self.max.score["voices"], ROLL["voices"])
        self.assertEqual(self.max.score["header"]["slotinfo"], ROLL["header"]["slotinfo"])
        self.assertEqual(self.max.sent[-1], "notes1 score_done")

    def test_add_keeps_the_ones_there_and_checks_them_together(self):
        reply = self.tools["write_markers"](markers=FOUR, add=True)
        self.assertTrue(reply.startswith("OK. Added 3 markers (4 now)"), reply)
        self.assertEqual([m["role"] for m in self.max.score["header"]["markers"]], ["timesig", "none", "barline", "barline"])
        reply = self.tools["write_markers"](markers=[mk(2000, "timesig", [3, 4])], add=True)
        self.assertIn("ERROR: with the markers already in the roll, barline and timesig at 2000 ms", reply)

    def test_mistakes_are_refused_with_what_to_correct(self):
        sent = len(self.max.sent)
        for markers, expected in (([{"onset": 0, "role": "timesig", "content": "4/4"}], '"content" is a list'),
                                  ([{"onset": 0, "role": "bar"}], 'role "bar" does not exist'),
                                  ([mk(0, "timesig", [4, 4]), mk(0, "barline")], "keep only the timesig"),
                                  ('[{"onset": 0 "role": "barline"}]', "markers is not valid JSON: a comma is missing"),
                                  ({"onset": 0}, '"markers" is a list of markers')):
            reply = self.tools["write_markers"](markers=markers)
            self.assertTrue(reply.startswith("ERROR") and expected in reply, reply)
        self.assertEqual(len(self.max.sent), sent)

    def test_write_score_says_the_measures_too_and_refuses_the_same_mistakes(self):
        note = {"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "vel": 80}]}
        reply = self.tools["write_score"](score={"header": {"markers": FOUR}, "voices": [{"chords": [note]}]})
        self.assertIn("measures 1-2, from 0 ms: 4/4, 2000 ms (quarter = 120) each", reply)
        reply = self.tools["write_score"](score={"header": {"markers": [mk(0, "timesig", [4, 4]), mk(0, "barline")]},
                                                 "voices": [{"chords": [note]}]})
        self.assertTrue(reply.startswith("ERROR: barline and timesig at 0 ms"), reply)

    def test_only_a_score_instance(self):
        self.target = Target("scales1", "generator", self.folder)
        self.assertIn("scales1 is a generator", self.tools["write_markers"](markers=FOUR))


class SkillTests(unittest.TestCase):
    def setUp(self):
        with open(QUANTIZER_SKILL_PATH, encoding="utf-8") as f:
            self.text = f.read()

    def test_the_playground_has_it_and_each_instance_reads_its_part(self):
        folder = prepare(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        compiled = compile_skill(folder, "minimal-algorithmic-composer", ["quantizer"])
        self.assertEqual(([name for name, _ in compiled.used], compiled.warnings), (["core-algorithmic", "quantizer"], []))
        parts = {t: instance_skill(compiled.text, mode, t).split("# Quantizer")[1]
                 for t, mode in (("score", "score"), ("generator", "algo"), ("transformer", "algo"), ("selector", "algo"))}
        for part in parts.values():
            self.assertIn("a measure of n beats has n − 1 division markers", part)
        self.assertEqual([("write_markers" in p, "grid(x" in p, "function produce" in p, "A selector may" in p) for p in parts.values()],
                         [(True, False, False, False), (False, True, True, False), (False, True, False, False), (False, True, False, True)])
        self.assertNotIn("Quantizer", instance_skill(compiled.text, "gen", "synth"))

    def test_its_json_example_is_what_it_says(self):
        markers = json.loads(re.findall(r"```json\n(.*?)```", self.text, re.S)[0])
        self.assertIsNone(check_markers(markers))
        self.assertEqual(check(markers), ([], []))
        text = report(markers)
        self.assertIn("measures 1-2, from 0 ms: 4/4, 2000 ms (quarter = 120) each", text)
        self.assertIn("measure 3, from 4000 ms: 2+2+3/8, 1750 ms (eighth = 240), 3 beats", text)

    @needs_node
    def test_its_code_example_passes_the_check_and_makes_its_measures(self):
        blocks = re.findall(r"```js\n(.*?)```", self.text, re.S)
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "example.js")
            with open(path, "w", encoding="utf-8") as f:
                f.write(blocks[0])
            result = check_algorithm(path, node=NODE)
        self.assertTrue(result.get("ok"), result)
        markers = result["score"]["header"]["markers"]
        self.assertEqual(check(markers), ([], []))
        self.assertEqual([m["role"] for m in markers], ["timesig"] + ["barline"] * 6)
        self.assertEqual(len(measures(markers)), 7)


if __name__ == "__main__":
    unittest.main()
