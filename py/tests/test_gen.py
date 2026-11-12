"""Tests for sound: the gen~ skill (GEN_SKILL.md), the GenExpr check (gen_check.js, Node) and
send_gen. Run: python -m unittest discover -s py/tests"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.bridge.protocol import words as split  # noqa: E402
from bach_mcp.prompt.modes import MODE_TOOLS, TYPE_MODE, instance_skill  # noqa: E402
from bach_mcp.prompt.skill import GEN_SKILL_PATH, load_skill, read_skill, skill_for, with_gen  # noqa: E402
from bach_mcp.tools.gen_tools import check_gen, gendsp, panel_mismatch, register_gen_tools  # noqa: E402
from bach_mcp.tools.playground import prepare  # noqa: E402
from bach_mcp.tools.session import Target, serve_targets  # noqa: E402

NODE = shutil.which(os.getenv("BACH_NODE") or "node")
needs_node = unittest.skipUnless(NODE, "Node.js is not installed")

GEN = read_skill(GEN_SKILL_PATH)
_EXAMPLE = re.compile(r"```\n(//.*?)```(?:\s*```json\n(.*?)```)?", re.S)

FM = """// A sine whose level follows the gate.
// in1: pitch, a MIDI note number
// in2: gate, 0..1
// out1: mono
Param level(-12);
out1 = cycle(mtof(in1)) * dbtoa(level) * slide(in2, 100, 4000);
"""
FM_PARAMS = {"level": {"type": "slider", "range": [-60, 0], "value": -12, "unit": "dB"}}


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class FakeBridge:
    def __init__(self):
        self.sent = []

    def flush(self):
        pass

    def send(self, text):
        self.sent.append(text)
        return True


class SkillTests(unittest.TestCase):
    def test_a_synth_reads_sound_only(self):
        source = with_gen(load_skill(raw=True))
        synth = instance_skill(source, "gen", "synth")
        self.assertIn("electronic composer", synth)
        self.assertIn("You are writing a **synth**", synth)
        self.assertNotIn("You are writing an **fx**", synth)
        self.assertIn("send_gen", synth)
        for word in ("bach.roll", "midicents", "write_score", "send_algorithm", "<!--"):
            self.assertNotIn(word, synth)
        fx = instance_skill(source, "gen", "fx")
        self.assertIn("You are writing an **fx**", fx)
        self.assertIn("Feedback delay", fx)
        self.assertNotIn("Two-operator FM", fx)

    def test_the_score_never_reads_sound(self):
        source = with_gen(load_skill(raw=True))
        for mode in ("score", "algo"):
            text = skill_for(source, mode)
            self.assertNotIn("GenExpr", text)
            self.assertEqual(text, skill_for(load_skill(raw=True), mode), "the sound skill adds nothing to the score's")

    def test_a_skill_with_its_own_sound_part_is_kept(self):
        mine = "<!-- gen -->\nMy own sound skill.\n<!-- /gen -->\n"
        self.assertEqual(with_gen(mine), mine)
        self.assertEqual(skill_for(with_gen(mine), "gen").strip(), "My own sound skill.")

    def test_sound_has_its_own_tools(self):
        self.assertEqual(TYPE_MODE["synth"], "gen")
        self.assertEqual(TYPE_MODE["fx"], "gen")
        self.assertEqual(MODE_TOOLS["gen"], ("send_gen",))
        for mode in ("score", "algo"):
            self.assertNotIn("send_gen", MODE_TOOLS[mode])


@needs_node
class CheckTests(unittest.TestCase):
    def check(self, code, params=None, instance_type="synth"):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "x.genexpr")
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            declared = os.path.join(folder, "x.json")
            with open(declared, "w", encoding="utf-8") as f:
                json.dump(params or {}, f)
            return check_gen(path, instance_type, declared, node=NODE)

    def refused(self, code, saying, params=None, instance_type="synth"):
        result = self.check(code, params, instance_type)
        self.assertFalse(result["ok"], code)
        self.assertIn(saying, result["error"])
        return result

    def test_the_examples_of_the_skill_pass(self):
        examples = _EXAMPLE.findall(GEN)
        self.assertGreaterEqual(len(examples), 3)
        for code, params in examples:
            instance_type = "fx" if "// in1: sound in" in code else "synth"
            declared = json.loads(params) if params else {"speed": {"type": "slider", "range": [-4, 4], "value": 1, "step": 0.01}}
            result = self.check(code, declared, instance_type)
            self.assertTrue(result["ok"], f"{code.splitlines()[0]}: {result.get('error')}")

    def test_what_it_reports(self):
        result = self.check(FM, FM_PARAMS)
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["description"], "A sine whose level follows the gate.")
        self.assertEqual([p["index"] for p in result["inlets"]], [1, 2])
        self.assertEqual(result["inlets"][0]["about"], "pitch, a MIDI note number")
        self.assertEqual(len(result["outlets"]), 1)
        self.assertEqual(result["params"][0]["send"], -12)

    def test_what_is_not_genexpr(self):
        head = "// x\n// out1: mono\n"
        self.refused(head + "var x = 1;\nout1 = x;", "variables are not declared")
        self.refused(head + "x = 0;\nx++;\nout1 = x;", "no ++")
        self.refused(head + "out1 = Math.sin(1);", "no objects in GenExpr")
        self.refused(head + "x = 1\nout1 = x;", "; is missing")
        self.refused(head + "a = 1;\nout1 = a[0];", "no arrays")
        self.refused(head + "out1 = saw(220);", "phasor")
        self.refused(head + "out1 = cycl(220);", "Did you mean cycle")
        self.refused(head + "out1 = cycle(220, 0, 1);", "takes 1 to 2 arguments")
        self.refused(head + 'out1 = cycle(0.5, index="fase");', "does not exist")
        self.refused(head + "out1 = y * 2;", "y is not set before it is read")
        self.refused(head + "if (noise() > 0) { g = 1; }\nout1 = g;", "give it a value before")
        self.refused(head + "x = 1;\nHistory z(0);\nout1 = x + z;", "comes after the first statement")
        self.refused(head + "Delay d(1000);\nout1 = d;", "d.read(")
        self.refused(head + "Data t(64);\nout1 = peek(u, 0);", "name of a Data or a Buffer")
        self.refused(head + "Param mix(0.5);\nout1 = mix(1, 0, mix);", "rename", {"mix": {"type": "slider", "range": [0, 1], "value": 0.5, "step": 0.01}})

    def test_the_file(self):
        self.refused("out1 = cycle(220);", "must open with a // comment")
        self.refused("// x\nout1 = cycle(220);", "out1 is not described")
        self.refused("// x\n// out1: left\n// out2: right\nout2 = cycle(220);", "never out1")
        self.refused("// x\n// out1: mono\nout1 = cycle(220);", "processes the sound that comes in", instance_type="fx")
        self.refused("// x\n// out1: mono\nout1 = in1;", "in1 is not described")

    def test_params_and_code_agree(self):
        self.refused(FM, "has no Param in the code", {**FM_PARAMS, "cutoff": {"type": "slider", "range": [20, 20000], "value": 1000}})
        self.refused(FM, "is not in params", {})
        self.refused(FM, "starts at -12 in the code and at -6 in params", {"level": {"type": "slider", "range": [-60, 0], "value": -6}})
        self.refused(FM, "slider, toggle or menu", {"level": {"type": "range", "range": [-60, 0], "value": [-12, -6]}})
        menu = "// x\n// out1: mono\nParam shape(1);\nout1 = selector(shape + 1, cycle(220), phasor(220) * 2 - 1);"
        result = self.check(menu, {"shape": {"type": "menu", "options": ["sine", "saw"], "value": "saw"}})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["params"][0]["send"], 1)

    def test_buffers_are_reported(self):
        code = '// x\n// out1: mono\nBuffer source("my_sound");\nData window(512);\nout1 = sample(source, phasor(1)) * peek(window, 3);'
        result = self.check(code)
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["buffers"], [{"name": "source", "buffer": "my_sound"}])
        self.assertEqual(result["data"], ["window"])


class PanelMismatchTests(unittest.TestCase):
    """The last check on the gendsp: every panel parameter is a Param there and sends a number."""

    def test_match(self):
        patch = gendsp("// x\nParam shape(1);\nParam wet(0.5);\nout1 = in1;\n", 1, 1)
        params = [{"name": "shape", "type": "menu", "send": 1}, {"name": "wet", "type": "slider", "send": 0.5}]
        self.assertEqual(panel_mismatch(patch, params), [])

    def test_missing_param_and_symbol(self):
        patch = gendsp("// x\n// Param gone(1);\nParam shape(1);\nout1 = in1;\n", 1, 1)
        params = [{"name": "gone", "send": 1}, {"name": "shape", "send": "saw"}, {"name": "on", "send": True}]
        problems = panel_mismatch(patch, params)
        self.assertEqual(len(problems), 4)
        self.assertIn("gone is not a Param", problems[0])
        self.assertIn("'saw', not a number", problems[1])


@needs_node
class SendGenTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.playground = prepare(os.path.join(self.folder, "playground"))
        self.bridge = FakeBridge()
        mcp = FakeMCP()
        register_gen_tools(mcp, self.bridge, node=NODE)
        self.send_gen = mcp.tools["send_gen"]
        self.addCleanup(serve_targets, None)

    def serve(self, name, instance_type):
        serve_targets(lambda: Target(name, instance_type, self.playground))

    def test_a_synth_is_saved_and_loaded(self):
        self.serve("bell", "synth")
        answer = self.send_gen(FM, FM_PARAMS)
        self.assertTrue(answer.startswith("OK. synth saved as gen/bell.genexpr"), answer)
        self.assertIn("in1: pitch, a MIDI note number", answer)
        self.assertIn("level: slider -60..0 dB = -12", answer)
        self.assertEqual([split(sent) for sent in self.bridge.sent], [["bell", "load_gen", "bell.gendsp"]])
        gen = os.path.join(self.playground, "gen")
        with open(os.path.join(gen, "bell.genexpr"), encoding="utf-8") as f:
            self.assertEqual(f.read(), FM)
        with open(os.path.join(gen, "bell.gendsp"), encoding="utf-8") as f:
            patcher = json.load(f)["patcher"]
        boxes = [box["box"] for box in patcher["boxes"]]
        self.assertEqual(patcher["classnamespace"], "dsp.gen")
        self.assertEqual(boxes[0]["code"], FM.replace("\n", "\r\n"))
        self.assertEqual(sorted(box["text"] for box in boxes[1:]), ["in 1", "in 2", "out 1"])
        self.assertEqual(len(patcher["lines"]), 3)
        with open(os.path.join(gen, "bell.json"), encoding="utf-8") as f:
            about = json.load(f)
        self.assertEqual(about["type"], "synth")
        self.assertEqual(about["params"][0]["name"], "level")

    def test_params_may_come_as_text_and_errors_load_nothing(self):
        self.serve("bell", "synth")
        self.assertTrue(self.send_gen(FM, json.dumps(FM_PARAMS)).startswith("OK"))
        answer = self.send_gen(FM.replace("cycle", "sine"), FM_PARAMS)
        self.assertTrue(answer.startswith("ERROR in bell.genexpr line 6: gen~ has no operator sine"), answer)
        self.assertEqual(len(self.bridge.sent), 1)
        with open(os.path.join(self.playground, "gen", "bell.genexpr"), encoding="utf-8") as f:
            self.assertEqual(f.read(), FM, "the file that works stays")

    def test_only_for_sound(self):
        self.serve("melody", "generator")
        answer = self.send_gen(FM, FM_PARAMS)
        self.assertTrue(answer.startswith("ERROR: melody is a generator instance"), answer)
        self.assertEqual(self.bridge.sent, [])

    def test_the_patcher_without_inlets(self):
        patcher = gendsp("out1 = noise();\n", 0, 2)["patcher"]
        self.assertEqual(patcher["boxes"][0]["box"]["numinlets"], 1)
        self.assertEqual([box["box"]["text"] for box in patcher["boxes"][1:]], ["out 1", "out 2"])

    def test_the_playground_has_the_sound_skill(self):
        with open(os.path.join(self.playground, "skills", "core-electronic.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), GEN)
        with open(os.path.join(self.playground, "skills", "profiles", "minimal-electronic-composer.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"skills": ["core-electronic"]})


if __name__ == "__main__":
    unittest.main()
