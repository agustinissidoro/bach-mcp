"""Checks on the instrument docs (py/bach_mcp/docs). Run: python -m unittest discover -s py/tests"""

import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.translate import CLEFS, MAX_CENTS, ScoreError, normalize_score  # noqa: E402

DOCS = os.path.join(os.path.dirname(__file__), "..", "bach_mcp", "docs")
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

    def test_json_spellings_are_accepted(self):
        for path in doc_files():
            text = parse(path)[3]
            for art in re.findall(r'"art":\s*"([^"]+)"', text):
                chord = {"onset": 0, "art": art, "notes": [{"pitch": 6000, "dur": 100}]}
                try:
                    normalize_score({"voices": [{"name": "T", "chords": [chord]}]})
                except ScoreError as exc:
                    self.fail(f"{path}: \"art\": {art!r} rejected ({exc})")
            for head in re.findall(r'"head":\s*"([^"]+)"', text):
                chord = {"onset": 0, "notes": [{"pitch": 6000, "dur": 100, "head": head}]}
                try:
                    normalize_score({"voices": [{"name": "T", "chords": [chord]}]})
                except ScoreError as exc:
                    self.fail(f"{path}: \"head\": {head!r} rejected ({exc})")


if __name__ == "__main__":
    unittest.main()
