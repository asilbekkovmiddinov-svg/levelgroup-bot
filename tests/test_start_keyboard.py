import pathlib
import unittest


class StartKeyboardTest(unittest.TestCase):
    def test_start_removes_legacy_reply_keyboard(self):
        source = pathlib.Path("handlers/start.py").read_text(encoding="utf-8")

        self.assertIn("ReplyKeyboardRemove", source)
        self.assertIn("reply_markup=ReplyKeyboardRemove()", source)
        self.assertNotIn("ReplyKeyboardMarkup", source)
        self.assertNotIn("KeyboardButton(text=", source)
        self.assertNotIn("main_keyboard()", source)

    def test_start_exposes_configured_miniapp_button(self):
        source = pathlib.Path("handlers/start.py").read_text(encoding="utf-8")
        config = pathlib.Path("config.py").read_text(encoding="utf-8")

        self.assertIn('text="🚀 LEVEL_GROUP’ni ochish"', source)
        self.assertIn("web_app=WebAppInfo(url=MINIAPP_URL)", source)
        self.assertIn("if MINIAPP_URL:", source)
        self.assertIn('os.getenv("MINIAPP_URL")', config)
        self.assertNotIn("miniapp-jocker7005", source)


if __name__ == "__main__":
    unittest.main()
