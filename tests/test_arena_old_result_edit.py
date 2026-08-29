import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDLER = (ROOT / "handlers" / "admin_arena_old_result.py").read_text(encoding="utf-8")
BOT = (ROOT / "bot.py").read_text(encoding="utf-8")


class ArenaOldResultEditTests(unittest.TestCase):
    def test_admin_can_reply_to_old_result_with_command(self):
        self.assertIn('/arena_edit', HANDLER)
        self.assertIn('reply_to_message', HANDLER)
        self.assertIn('edit_reply_markup', HANDLER)
        self.assertIn('✏️ Natijani tahrirlash', HANDLER)

    def test_match_id_can_be_supplied_directly(self):
        self.assertIn('parts[1].strip().isdigit()', HANDLER)
        self.assertIn('arv4:e:start:', HANDLER)

    def test_handler_is_registered(self):
        self.assertIn('admin_arena_old_result_router', BOT)
        self.assertIn('dp.include_router(admin_arena_old_result_router)', BOT)


if __name__ == '__main__':
    unittest.main()
