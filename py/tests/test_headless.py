"""Claude Code behind the hub (chat/headless.py), run on a stand-in `claude`.
Run: python -m unittest discover -s py/tests"""

import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp import claude  # noqa: E402
from bach_mcp.chat import headless  # noqa: E402
from bach_mcp.chat.headless import ClaudeConversation  # noqa: E402
from bach_mcp.config import Config  # noqa: E402

FAKE = f"""#!{sys.executable}
import json, os, sys, time
args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({{"args": args, "prompt": sys.stdin.read()}}) + "\\n")
mode = os.environ.get("FAKE_MODE", "tool")
def say(**line):
    print(json.dumps(line), flush=True)
if mode == "gone" and "--resume" in args:
    print("No conversation found with session ID: old", flush=True)
    sys.exit(1)
if mode == "crash":
    print("something broke", flush=True)
    sys.exit(2)
say(type="system", subtype="init", session_id="s1")
if mode == "login":
    say(type="assistant", error="authentication_failed", session_id="s1",
        message={{"content": [{{"type": "text", "text": "Failed to authenticate"}}]}})
    say(type="result", subtype="success", is_error=True, result="Failed to authenticate: expired", session_id="s1")
    sys.exit(1)
if mode == "slow":
    time.sleep(30)
say(type="system", subtype="status", status="requesting", session_id="s1")
say(type="stream_event", session_id="s1", event={{"type": "message_start"}})
say(type="stream_event", session_id="s1", event={{"type": "content_block_start", "content_block": {{"type": "thinking"}}}})
say(type="stream_event", session_id="s1", event={{"type": "content_block_start", "content_block": {{"type": "text", "text": ""}}}})
say(type="stream_event", session_id="s1", event={{"type": "content_block_start", "content_block": {{"type": "tool_use", "name": "mcp__bach__send_algorithm"}}}})
say(type="assistant", session_id="s1", message={{"content": [
    {{"type": "text", "text": "Writing it. "}},
    {{"type": "tool_use", "id": "t1", "name": "mcp__bach__send_algorithm", "input": {{"code": "x"}}}}]}})
say(type="user", session_id="s1", message={{"content": [
    {{"type": "tool_result", "tool_use_id": "t1", "content": [{{"type": "text", "text": "OK. loaded"}}]}}]}})
if mode == "turns":
    say(type="result", subtype="error_max_turns", is_error=True, session_id="s1", usage={{"output_tokens": 5}})
    sys.exit(0)
say(type="assistant", session_id="s1", message={{"content": [{{"type": "text", "text": "Done."}}]}})
say(type="result", subtype="success", is_error=False, result="Done.", session_id="s1", usage={{"output_tokens": 42}})
"""


class HeadlessTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.command = os.path.join(self.folder, "claude")
        with open(self.command, "w") as f:
            f.write(FAKE)
        os.chmod(self.command, os.stat(self.command).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.folder, "log")
        os.environ["FAKE_LOG"] = self.log
        self.addCleanup(os.environ.pop, "FAKE_LOG", None)
        self.addCleanup(os.environ.pop, "FAKE_MODE", None)
        self.chat = ClaudeConversation(self.command, Config(), "generator")

    def runs(self):
        with open(self.log) as f:
            return [json.loads(row) for row in f]

    def test_a_message_becomes_events(self):
        events = [e for e in self.chat.send("a canon") if e["type"] != "stage"]
        self.assertEqual([e["type"] for e in events], ["text", "tool_call", "tool_result", "text", "round", "done"])
        self.assertEqual(events[1]["name"], "send_algorithm")
        self.assertEqual(events[2], {"type": "tool_result", "id": "t1", "name": "send_algorithm", "result": "OK. loaded"})
        self.assertEqual(events[4]["usage"]["completion_tokens"], 42)
        self.assertEqual(self.chat.history[-1],
                         {"role": "assistant", "content": "Writing it. Done.", "session": "s1"})

    def test_the_stages_come_from_the_partial_messages(self):
        stages = [[e["stage"], *e.get("detail", [])] for e in self.chat.send("a canon") if e["type"] == "stage"]
        self.assertEqual(stages, [["sent"], ["thinking"], ["writing"], ["calling", "send_algorithm"]])
        self.assertIn("--include-partial-messages", self.runs()[0]["args"])

    def test_claude_gets_only_the_tools_and_the_skill_of_its_instance(self):
        list(self.chat.send("a canon"))
        run = self.runs()[0]
        args = run["args"]
        self.assertEqual(run["prompt"], "a canon")
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertEqual(args[args.index("--allowedTools") + 1], "mcp__bach__send_algorithm")
        self.assertIn("You are writing for a generator", args[args.index("--append-system-prompt") + 1])
        self.assertEqual(json.loads(args[args.index("--mcp-config") + 1]),
                         {"mcpServers": {"bach": {"type": "http", "url": Config().headless_mcp_url("algo")}}})
        self.assertNotIn("--resume", args)

    def test_claude_code_prompt_false_replaces_claude_codes_own(self):
        args = self.chat.command_line()
        self.assertIn("--append-system-prompt", args, "by default Claude Code keeps its own prompt")
        self.assertNotIn("--system-prompt", args)
        config = Config()
        config.claude.claude_code_prompt = False
        args = ClaudeConversation(self.command, config, "score").command_line()
        self.assertNotIn("--append-system-prompt", args)
        self.assertIn("You are writing for a score instance", args[args.index("--system-prompt") + 1])

    def test_the_prompt_is_sent_anew_on_every_resume(self):
        self.chat.session = "s1"
        args = self.chat.command_line()
        self.assertEqual(args[args.index("--system-prompt-snapshot") + 1], "off",
                         "else Claude Code resends the first message's prompt and a changed skill never arrives")

    def test_model_and_effort_only_when_set(self):
        args = self.chat.command_line()
        self.assertNotIn("--model", args, "unset: the account's default")
        self.assertNotIn("--effort", args)
        config = Config()
        config.claude.claude_model, config.claude.claude_effort = "sonnet", "low"
        args = ClaudeConversation(self.command, config, "score").command_line()
        self.assertEqual(args[args.index("--model") + 1], "sonnet")
        self.assertEqual(args[args.index("--effort") + 1], "low")

    def test_the_next_message_resumes_the_session(self):
        list(self.chat.send("one"))
        list(self.chat.send("two"))
        args = self.runs()[1]["args"]
        self.assertEqual(args[args.index("--resume") + 1], "s1")

    def test_a_session_that_is_gone_starts_a_new_one(self):
        os.environ["FAKE_MODE"] = "gone"
        self.chat.session = "old"
        events = list(self.chat.send("one"))
        self.assertEqual(events[-1], {"type": "done", "finish": "stop"})
        self.assertFalse(any(e["type"] == "error" for e in events))
        self.assertNotIn("--resume", self.runs()[1]["args"])
        self.assertEqual(self.chat.session, "s1")

    def test_not_logged_in_says_what_to_do(self):
        os.environ["FAKE_MODE"] = "login"
        events = list(self.chat.send("one"))
        self.assertEqual([e["type"] for e in events], ["round", "error", "done"])
        self.assertIn("auth login", events[1]["message"])
        self.assertEqual(self.chat.history[-1]["content"], "")

    def test_a_crash_is_reported(self):
        os.environ["FAKE_MODE"] = "crash"
        events = list(self.chat.send("one"))
        self.assertEqual([e["type"] for e in events], ["error", "done"])
        self.assertIn("something broke", events[0]["message"])

    def test_too_many_turns(self):
        os.environ["FAKE_MODE"] = "turns"
        self.assertEqual(list(self.chat.send("one"))[-1], {"type": "done", "finish": "rounds"})

    def test_stop_ends_it(self):
        os.environ["FAKE_MODE"] = "slow"
        events = self.chat.send("one")
        self.chat_thread_stop = __import__("threading").Timer(0.5, self.chat.cancel)
        self.chat_thread_stop.start()
        self.assertEqual(list(events), [])

    def test_no_claude_code(self):
        chat = ClaudeConversation(None, Config(), "generator")
        self.assertIn("not on this computer", list(chat.send("one"))[0]["message"])


class ToolResultTests(unittest.TestCase):
    def test_the_tools_text_comes_out_whole(self):
        self.assertEqual(headless._text('{"result":"OK. saved\\nParameters"}'), "OK. saved\nParameters")
        self.assertEqual(headless._text([{"type": "text", "text": '{"result":"OK."}'}]), "OK.")
        self.assertEqual(headless._text("plain"), "plain")
        self.assertEqual(headless._text('{"voices": []}'), '{"voices": []}')


class FindTests(unittest.TestCase):
    def test_the_newest_one_from_claude_desktop(self):
        self.assertEqual(sorted(["/a/claude-code/2.1.99/x/c", "/a/claude-code/2.1.309/x/c"], key=claude._version)[-1],
                         "/a/claude-code/2.1.309/x/c")


if __name__ == "__main__":
    unittest.main()
