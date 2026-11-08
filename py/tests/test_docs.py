"""Checks on the instrument docs (py/bach_mcp/prompt/docs). Run: python -m unittest discover -s py/tests"""

import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.prompt.docs import DocLibrary  # noqa: E402
# bach.roll's clefs and its highest pitch (G9), which the instrument docs must stay within.
CLEFS = ["G", "F", "FG", "FGG", "FFG", "FFGG", "G8va", "G15ma", "G8vb", "G15mb", "F8va", "F15ma", "F8vb", "F15mb",
         "Soprano", "Mezzo", "Alto", "Tenor", "Barytone", "Percussion", "None"]
MAX_CENTS = 12700
# bach.roll's names for articulations and noteheads (its symbol tables, read from the external).
ARTICULATIONS = {"staccato", "staccatissimo", "portato", "accent", "martellato", "fermata", "trill", "harmonic",
                 "accentstaccato", "accentportato", "portatostaccato", "martellatostaccato", "upmordent", "mordent",
                 "downmordent", "doublemordent", "gruppetto", "lefthandpizzicato", "upbowing", "downbowing",
                 "tremolo1", "tremolo2", "tremolo3"}
NOTEHEADS = {"white", "black", "cross", "diamond", "square", "blacksquare", "whitesquare", "rhombus", "blackrhombus",
             "whiterhombus", "triangle", "blacktriangle", "whitetriangle", "doublewhole", "none"}
# A doc names a mark in words (articulation harmonic, annotation "pizz.", notehead cross, glissando 700),
# which the skill says how to write in each mode: never a JSON key, which belongs to one mode only.
JSON_KEY = re.compile(r'"\w+"\s*:')

DOCS = os.path.join(os.path.dirname(__file__), "..", "bach_mcp", "prompt", "docs")
CORE_FIELDS = ("register", "expanded_register", "transposing", "clefs", "techniques")


def doc_files():
    return sorted(glob.glob(os.path.join(DOCS, "*", "*.md")))


def parse(path):
    """Split a doc into its front matter (dict of raw strings), core and section titles."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise AssertionError(f"{path}: no front matter")
    meta = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    body = m.group(2)
    core = body.split("\n## ", 1)[0]
    sections = re.findall(r"^## (.+)$", body, re.M)
    return meta, core, sections, text


def aliases(meta):
    return [a.strip() for a in meta.get("aliases", "").strip("[]").split(",") if a.strip()]


def field(core, name):
    m = re.search(rf"^{name}:\s*(.*)$", core, re.M)
    return m.group(1) if m else None


class DocsTests(unittest.TestCase):
    def test_front_matter(self):
        seen = {}
        for path in doc_files():
            meta, _, _, _ = parse(path)
            names = aliases(meta)
            self.assertTrue(names, f"{path}: no aliases")
            self.assertEqual(meta.get("family"), os.path.basename(os.path.dirname(path)), path)
            for name in names:
                self.assertEqual(name, name.lower(), f"{path}: alias {name!r} must be lower case")
                self.assertNotIn(name, seen, f"alias {name!r} in {path} and {seen.get(name)}")
                seen[name] = path

    def test_instrument_fields(self):
        for path in doc_files():
            if os.path.basename(path) == "_family.md":
                continue
            _, core, sections, _ = parse(path)
            positions = []
            for name in CORE_FIELDS:
                m = re.search(rf"^{name}:", core, re.M)
                self.assertIsNotNone(m, f"{path}: missing {name}:")
                positions.append(m.start())
            self.assertEqual(positions, sorted(positions), f"{path}: core fields out of order")
            self.assertIn("Harmonics", sections, f"{path}: no ## Harmonics section")

            lo, hi = (int(x) for x in re.match(r"(\d+)\s*[–-]\s*(\d+)$", field(core, "register")).groups())
            self.assertLess(lo, hi, path)
            for line in (field(core, "register"), field(core, "expanded_register")):
                for value in re.findall(r"\b\d{4,5}\b", line):
                    self.assertLessEqual(int(value), MAX_CENTS, f"{path}: {value} out of range")

            self.assertRegex(field(core, "transposing"), r"^(no|yes: )", path)
            main = field(core, "clefs").split(";")[0].strip()
            self.assertIn(main, CLEFS, f"{path}: unknown main clef {main!r}")


    def test_marks_are_named_in_words_bach_knows(self):
        for path in doc_files():
            text = parse(path)[3]
            self.assertIsNone(JSON_KEY.search(text), f"{path}: name the mark in words, not as a JSON key")
            for first, second in re.findall(r"\barticulation (\w+)(?:\s*(?:/|or)\s*(\w+))?", text):
                for name in filter(None, (first, second)):
                    self.assertIn(name, ARTICULATIONS, f"{path}: bach has no articulation {name!r}")
            for name in re.findall(r"\bnotehead (\w+)", text):
                self.assertIn(name, NOTEHEADS, f"{path}: bach has no notehead {name!r}")

    def test_the_skill_names_only_marks_bach_knows(self):
        from bach_mcp.prompt.skill import read_skill
        skill = read_skill()
        listed = re.search(r'`"articulations"`: (.*?)one, or a list', skill, re.S).group(1)
        self.assertEqual(set(re.findall(r'"(\w+)"', listed)) - ARTICULATIONS, set())
        listed = re.search(r'`"notehead"`: (.*?)\.\n', skill, re.S).group(1)
        self.assertEqual(set(re.findall(r'"(\w+)"', listed)) - NOTEHEADS, set())


class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = DocLibrary()

    def keys(self, text):
        return [d.key for d in self.library.find(text)]

    def test_family_comes_with_the_instrument(self):
        self.assertEqual(self.keys("a slow piece for Cello and flute"),
                         ["strings/_family", "strings/cello", "woodwinds/_family", "woodwinds/flute"])

    def test_longest_name_wins(self):
        self.assertEqual(self.keys("alto flute and bass clarinet"),
                         ["woodwinds/_family", "woodwinds/alto-flute", "woodwinds/bass-clarinet"])

    def test_whole_words_only(self):
        self.assertEqual(self.keys("celloist? no: violoncellist, pianissimo, clarity"), [])

    def test_whole_file_without_front_matter_or_clefs(self):
        doc = self.library.docs["strings/cello"]
        self.assertTrue(doc.text.startswith("# Cello"))
        self.assertIn("## Harmonics", doc.text)
        self.assertNotIn("clefs:", doc.text)
        self.assertNotIn("aliases:", doc.text)

    def test_each_file_once_and_deterministic(self):
        messages = [
            {"role": "system", "content": "skill"},
            {"role": "user", "content": "a cello solo"},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": [{"type": "text", "text": "now add a violin to the cello"}]},
        ]
        out, added = self.library.augment(messages)
        self.assertEqual(added, ["strings/violin"])
        self.assertIn("# Cello", out[1]["content"])
        later = out[3]["content"][-1]["text"]
        self.assertIn("# Violin", later)
        self.assertNotIn("# Cello", later)
        self.assertEqual(self.library.augment(messages)[0], out)
        self.assertEqual(messages[1]["content"], "a cello solo")  # the input is not modified

    def test_already_augmented_messages_are_left_alone(self):
        text, _ = self.library.augment_text("a cello solo", set())
        out, added = self.library.augment([{"role": "user", "content": text}])
        self.assertEqual(out[0]["content"], text)
        self.assertEqual(added, [])


if __name__ == "__main__":
    unittest.main()
