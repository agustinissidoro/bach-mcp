"""The door for Claude: what the MCP app offers, and registering Bach in Claude Desktop and Claude Code."""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp import claude  # noqa: E402
from bach_mcp.bridge.max import OfflineBridge  # noqa: E402
from bach_mcp.config import Config  # noqa: E402
from bach_mcp.prompt.modes import MODE_TOOLS  # noqa: E402


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = claude.mcp_app(Config(), OfflineBridge())  # no model settings needed: Claude is the model

    def test_the_tools_and_the_skill(self):
        names = [t.name for t in asyncio.run(self.app.list_tools())]
        self.assertEqual(len(names), 13)
        self.assertEqual(set(names), set(MODE_TOOLS["score"]) | set(MODE_TOOLS["algo"]))
        self.assertTrue(self.app.instructions.startswith("# Bach"))

    def test_the_modes_are_prompts(self):
        prompts = {p.name: p for p in asyncio.run(self.app.list_prompts())}
        self.assertEqual(set(prompts), {"score", "algo"})
        text = asyncio.run(self.app.get_prompt("algo", {"request": "a slow canon"})).messages[0].content.text
        self.assertIn("send_algorithm", text)
        self.assertTrue(text.endswith("a slow canon"))
        self.assertIn("p2mc", asyncio.run(self.app.get_prompt("score", {})).messages[0].content.text)

    def test_the_instrument_docs_are_resources(self):
        uris = {str(r.uri) for r in asyncio.run(self.app.list_resources())}
        self.assertIn("bach://skill", uris)
        self.assertIn("bach://docs/strings/cello", uris)
        self.assertIn("bach://docs/woodwinds/_family", uris)
        cello = list(asyncio.run(self.app.read_resource("bach://docs/strings/cello")))[0].content
        self.assertTrue(cello.startswith("# Cello"))


class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.path = os.path.join(self.folder, "Claude", "claude_desktop_config.json")

    def read(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def test_a_new_configuration(self):
        claude.register_desktop(self.path)
        entry = self.read()["mcpServers"]["bach"]
        self.assertEqual(entry["args"], [claude.MAIN_PY, "connect"])
        self.assertEqual(entry["command"], sys.executable)

    def test_everything_else_is_kept_and_an_older_entry_replaced(self):
        os.makedirs(os.path.dirname(self.path))
        before = {"preferences": {"x": 1}, "mcpServers": {"other": {"command": "x"},
                                                          "bach-mcp": {"command": "py", "args": [claude.MAIN_PY, "serve"]}}}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(before, f)
        claude.register_desktop(self.path)
        after = self.read()
        self.assertEqual(after["preferences"], {"x": 1})
        self.assertEqual(set(after["mcpServers"]), {"other", "bach"})
        with open(self.path + ".bak", encoding="utf-8") as f:
            self.assertEqual(json.load(f), before)

    def test_claude_code_lines(self):
        http, stdio = claude.claude_code_commands(Config())
        self.assertTrue(stdio.startswith("claude mcp add --scope user bach -- "))
        self.assertTrue(stdio.endswith("serve --stdio"))
        self.assertTrue(http.endswith("http://127.0.0.1:8090/mcp"))

    def test_claude_code_without_its_command_goes_in_its_file(self):
        path = os.path.join(self.folder, "claude.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"account": "kept", "mcpServers": {"other": {}}}, f)
        os.chmod(path, 0o600)
        self.assertTrue(claude.register_code(Config(), None, path))
        with open(path, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual(after["account"], "kept")
        self.assertEqual(after["mcpServers"]["bach"], {"type": "http", "url": "http://127.0.0.1:8090/mcp"})
        self.assertIn("other", after["mcpServers"])
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_claude_code_not_on_this_computer(self):
        self.assertFalse(claude.register_code(Config(), None, os.path.join(self.folder, "none.json")))


if __name__ == "__main__":
    unittest.main()
