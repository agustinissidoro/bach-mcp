"""The evaluation suite's checks, on hand-written scores (no model)."""

import json
import unittest

from bach_mcp.evaluate import (CASES, check_algorithm_code, check_harmonics, check_jazz_chords, check_microtonal,
                               check_neapolitan, check_row, check_scale, check_spiral, check_transposition, check_trio,
                               pitch_tool_checks, plan_accidentals, summary)
from bach_mcp.pitch_tools import call_pitch_tool
from bach_mcp.translate import normalize_score


def score(*voices):
    return normalize_score({"voices": [{"name": name, "chords": chords} for name, chords in voices]})


def passed(checks):
    return {label: ok for label, ok, _ in checks}


class NeapolitanTests(unittest.TestCase):
    def test_a_correct_cadence_passes(self):
        chords = [[0, ["C3", 1000], ["G3", 1000], ["E4", 1000], ["C5", 1000]],
                  [1000, ["F3", 1000], ["F4", 1000], ["Ab4", 1000], ["Db5", 1000]],
                  [2000, ["G3", 1000], ["G4", 1000], ["B4", 1000], ["D5", 1000]],
                  [3000, ["C3", 1000], ["G4", 1000], ["C5", 1000], ["E5", 1000]]]
        self.assertTrue(all(passed(check_neapolitan(score(("Piano", chords)), None)).values()))

    def test_a_flat_dropped_from_the_neapolitan_fails(self):
        chords = [[0, ["F3", 1000], ["F4", 1000], ["Ab4", 1000], ["D5", 1000]],
                  [1000, ["G3", 1000], ["G4", 1000], ["B4", 1000], ["D5", 1000]],
                  [2000, ["C3", 1000], ["G4", 1000], ["C5", 1000], ["E5", 1000]]]
        result = passed(check_neapolitan(score(("Piano", chords)), None))
        self.assertFalse(result["Neapolitan chord (Db F Ab)"])
        self.assertTrue(result["ends V -> I"])

    def test_voices_sounding_together_make_one_chord(self):
        voices = [(name, [[0, [p, 1000]], [1000, [q, 1000]]])
                  for name, p, q in (("S", "Db5", "C5"), ("A", "Ab4", "G4"), ("T", "F4", "E4"), ("B", "F3", "C3"))]
        result = passed(check_neapolitan(score(*voices), None))
        self.assertTrue(result["Neapolitan chord (Db F Ab)"])
        self.assertTrue(result["4 notes in every chord"])
        self.assertFalse(result["ends V -> I"])


class TrioTests(unittest.TestCase):
    def test_staggered_entries_and_a_staccato_cello(self):
        s = score(("Violin", [[0, ["G4", 500]], [500, ["A4", 500]]]),
                  ("Viola", [[1000, ["C4", 500]], [1500, ["D4", 500]]]),
                  ("Cello", [[2000, {"art": "staccato"}, ["C3", 250]], [2500, {"art": "staccato"}, ["D3", 250]]]))
        self.assertTrue(all(passed(check_trio(s, None)).values()))

    def test_entering_together_fails(self):
        s = score(("Violin", [[0, ["G4", 500]]]), ("Viola", [[0, ["C4", 500]]]), ("Cello", [[0, ["C3", 500]]]))
        result = passed(check_trio(s, None))
        self.assertFalse(result["entries one after another"])
        self.assertFalse(result["cello staccato"])

    def test_a_cello_below_its_range_fails(self):
        s = score(("Violin", [[0, ["G4", 500]]]), ("Viola", [[500, ["C4", 500]]]), ("Cello", [[1000, ["B1", 500]]]))
        self.assertFalse(passed(check_trio(s, None))["every instrument in its range"])


class SpiralTests(unittest.TestCase):
    def test_twelve_quarter_tones_up_with_a_held_end(self):
        chords = [[i * 250, [6000 + i * 50, 250 if i < 11 else 2000]] for i in range(12)]
        self.assertTrue(all(passed(check_spiral(score(("Flute", chords)), None)).values()))

    def test_semitones_only_fail_the_quarter_tones(self):
        chords = [[i * 250, [6000 + i * 100, 250]] for i in range(12)]
        result = passed(check_spiral(score(("Flute", chords)), None))
        self.assertFalse(result["quarter-tones"])
        self.assertFalse(result["last note held longest"])


class MicrotonalTests(unittest.TestCase):
    def test_just_intonation_passes(self):
        chord = [[0, ["C3", 4000], ["E3-14", 4000], ["G3+2", 4000], ["Bb3-31", 4000]]]
        self.assertTrue(all(passed(check_microtonal(score(("Strings", chord)), None)).values()))

    def test_equal_temperament_fails(self):
        chord = [[0, ["C3", 4000], ["E3", 4000], ["G3", 4000], ["Bb3", 4000]]]
        result = passed(check_microtonal(score(("Strings", chord)), None))
        self.assertFalse(result["E a just third (-14 cents)"])
        self.assertFalse(result["Bb the natural seventh (-31 cents)"])


class PlanTests(unittest.TestCase):
    def test_accidentals_named_in_a_plan(self):
        plan = "The Neapolitan is D♭ major (D♭ F A♭), then G7 with F#; Bb and E# too."
        self.assertEqual(plan_accidentals(plan), {1, 8, 6, 10, 5})

    def test_words_are_not_notes(self):
        self.assertEqual(plan_accidentals("A beautiful cadence. Bass line, then Eb."), {3})


class AlgorithmTests(unittest.TestCase):
    ACCELERANDO = """
const params = {
  count: { type: "slider", range: [4, 40], value: 16 },
  from:  { type: "slider", range: [200, 1000], value: 500, unit: "ms" },
  to:    { type: "slider", range: [50, 190], value: 100, unit: "ms" },
};
function produce(p) {
  const s = score();
  const v = s.voice("Marimba");
  let t = 0;
  for (let i = 0; i < p.count; i++) {
    const gap = p.from + (p.to - p.from) * i / (p.count - 1);
    v.note(t, 7200, gap);
    t += gap;
  }
  return s;
}
"""

    def test_an_accelerating_producer_passes(self):
        checks, _ = check_algorithm_code(self.ACCELERANDO)
        self.assertTrue(all(passed(checks).values()), checks)

    def test_broken_code_fails(self):
        checks, _ = check_algorithm_code("function produce(p) { return nope; }")
        self.assertFalse(checks[0][1])


def notes_in_time(pitches, step=250):
    return [[i * step, [p, step]] for i, p in enumerate(pitches)]


def tool(name, **arguments):
    return json.loads(call_pitch_tool(name, arguments))


class PitchArithmeticTests(unittest.TestCase):
    def test_transposition(self):
        melody = tool("p2mc", pitches=["D4", "F4", "A4", "G4", "E4", "C#4", "D4"])
        right = score(("Violin", notes_in_time(melody)), ("Viola", notes_in_time(tool("transpose", pitches=melody, cents=-800))),
                      ("Cello", notes_in_time(tool("transpose", pitches=melody, cents=-1700))))
        self.assertTrue(all(passed(check_transposition(right, None)).values()))
        wrong = score(("Violin", notes_in_time(melody)), ("Viola", notes_in_time([p - 900 for p in melody])),
                      ("Cello", notes_in_time([p - 1700 for p in melody])))
        self.assertFalse(passed(check_transposition(wrong, None))["viola a minor sixth lower (-800)"])

    def test_row_forms(self):
        prime = tool("p2mc", pitches="G4 Bb4 D5 F#5 A5 C6 E6 G#6 B6 C#7 Eb7 F7")
        inversion = tool("mirror", pitches=prime)
        line = prime + tool("reverse", pitches=prime) + inversion + tool("reverse", pitches=inversion)
        self.assertTrue(all(passed(check_row(score(("Piano", notes_in_time(line))), None)).values()))
        swapped = prime + inversion + tool("reverse", pitches=prime) + tool("reverse", pitches=inversion)
        result = passed(check_row(score(("Piano", notes_in_time(swapped))), None))
        self.assertTrue(result["prime"])
        self.assertFalse(result["retrograde"])

    def test_jazz_chords(self):
        chords = [tool("get_chord", root=r, chord=c) for r, c in (("Bb3", "m7b5"), ("Eb3", "7b9"), ("Ab3", "maj9"), ("Db3", "13"))]
        right = score(("Piano", [[i * 1000] + [[p, 1000] for p in ps] for i, ps in enumerate(chords)]))
        self.assertTrue(all(passed(check_jazz_chords(right, None)).values()))
        inverted = [chords[0], tool("get_chord", root="Eb3", chord="7b9", inversion=1)] + chords[2:]
        result = passed(check_jazz_chords(score(("Piano", [[i * 1000] + [[p, 1000] for p in ps]
                                                           for i, ps in enumerate(inverted)])), None))
        self.assertFalse(result["Eb7b9 complete, root in the bass"])

    def test_scale(self):
        right = tool("get_scale", root="E3", scale="harmonic_minor", octaves=2, direction="updown")
        self.assertTrue(passed(check_scale(score(("Clarinet", notes_in_time(right))), None))[
            "E harmonic minor, E3 up two octaves and back"])
        natural = tool("get_scale", root="E3", scale="minor", octaves=2, direction="updown")
        self.assertFalse(all(passed(check_scale(score(("Clarinet", notes_in_time(natural))), None)).values()))

    def test_harmonics(self):
        exact = tool("get_midicents", values=list(range(1, 9)), unit="harmonic", reference="C2")
        self.assertTrue(all(passed(check_harmonics(score(("Strings", [[0] + [[p, 4000] for p in exact]])), None)).values()))
        tempered = [3600, 4800, 5500, 6000, 6400, 6700, 7000, 7200]
        self.assertFalse(passed(check_harmonics(score(("Strings", [[0] + [[p, 4000] for p in tempered]])), None))[
            "harmonics 1-8 of C2 to the cent"])

    def test_copied_from_the_tools_or_not(self):
        calls = [{"tool": "p2mc", "arguments": {}, "answer": "[6200, 6500]"}]
        copied = score(("Flute", notes_in_time([6200, 6500])))
        self.assertTrue(all(passed(pitch_tool_checks(copied, calls)).values()))
        retyped = score(("Flute", notes_in_time([6200, 6600])))
        self.assertFalse(passed(pitch_tool_checks(retyped, calls))["every pitch copied from a tool answer"])
        result = passed(pitch_tool_checks(copied, []))
        self.assertFalse(result["used the pitch tools"])
        self.assertIsNone(result["every pitch copied from a tool answer"])


class SummaryTests(unittest.TestCase):
    def test_counts_outcomes_and_checks(self):
        report = {"model": "m", "sampling": {}, "cases": {"spiral": [
            {"outcome": "valid", "seconds": 10, "checks": [("12 notes", True, "")]},
            {"outcome": "loop", "seconds": 30, "checks": []},
        ]}}
        text = summary(report)
        self.assertIn("valid 1/2, loops 1/2", text)
        self.assertIn("20 s mean", text)
        self.assertIn("1/1", text)

    def test_every_case_has_a_unique_name(self):
        self.assertEqual(len({c.name for c in CASES}), len(CASES))


if __name__ == "__main__":
    unittest.main()
