import pathlib
import unittest


class StartKeyboardTest(unittest.TestCase):
    def test_start_removes_legacy_reply_keyboard(self):
        source = pathlib.Path("handlers/start.py").read_text(encoding="utf-8")

        self.assertIn("ReplyKeyboardRemove", source)
        self.assertIn("reply_markup=ReplyKeyboardRemove()", source)
        self.assertNotIn("ReplyKeyboardMarkup", source)
        self.assertNotIn("KeyboardButton", source)
        self.assertNotIn("main_keyboard()", source)


if __name__ == "__main__":
    unittest.main()
