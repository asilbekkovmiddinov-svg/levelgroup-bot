import re
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

    def test_actual_channel_title_format_is_supported(self):
        pattern = re.compile(
            r"(?:DB\s*#|Match\s*#|ARENA\s*[—–-]?\s*(?:№|#)\s*)(\d+)",
            re.IGNORECASE,
        )
        found = pattern.search("⚔️ ARENA — №35 MATCH")
        self.assertIsNotNone(found)
        self.assertEqual(found.group(1), "35")

    def test_channel_post_has_its_own_observer(self):
        self.assertIn('@router.channel_post(F.text.startswith("/arena_edit"))', HANDLER)
        self.assertIn('channel_post=True', HANDLER)
        self.assertIn('message.sender_chat.id == message.chat.id', HANDLER)

    def test_normal_messages_still_require_configured_admin(self):
        self.assertIn('message.from_user.id in ARENA_ADMIN_IDS', HANDLER)
        self.assertIn('channel_post and message.sender_chat', HANDLER)

    def test_handler_is_registered(self):
        self.assertIn('admin_arena_old_result_router', BOT)
        self.assertIn('dp.include_router(admin_arena_old_result_router)', BOT)


if __name__ == '__main__':
    unittest.main()
