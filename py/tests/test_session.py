"""Telling a new chat from the next turn of the same one."""

import unittest

from bach_mcp.session import conversation, new_conversation, starts_conversation


class StartsConversationTests(unittest.TestCase):
    def test_the_first_user_message_starts_a_chat(self):
        self.assertTrue(starts_conversation([{"role": "system", "content": "skill"}, {"role": "user", "content": "hi"}]))

    def test_later_turns_and_tool_rounds_do_not(self):
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "", "tool_calls": []},
                   {"role": "tool", "content": "OK"}]
        self.assertFalse(starts_conversation(history))
        self.assertFalse(starts_conversation(history + [{"role": "user", "content": "more"}]))
        self.assertFalse(starts_conversation([]))
        self.assertFalse(starts_conversation(None))

    def test_each_new_chat_has_its_own_number(self):
        before = conversation()
        self.assertEqual(new_conversation(), before + 1)
        self.assertEqual(conversation(), before + 1)


if __name__ == "__main__":
    unittest.main()
