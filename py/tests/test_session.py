"""Which conversation the tools are serving."""

import unittest

from bach_mcp.tools.session import conversation, new_conversation


class SessionTests(unittest.TestCase):
    def test_each_new_chat_has_its_own_number(self):
        before = conversation()
        self.assertEqual(new_conversation(), before + 1)
        self.assertEqual(conversation(), before + 1)


if __name__ == "__main__":
    unittest.main()
