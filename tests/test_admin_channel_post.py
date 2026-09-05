import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from handlers.admin_channel_post import copy_post_to_channels, post_channels_keyboard


CHANNELS = [
    {"id": 1, "chat_id": "@first_channel", "title": "First"},
    {"id": 2, "chat_id": "@second_channel", "title": "Second"},
    {"id": 3, "chat_id": "@third_channel", "title": "Third"},
]


class FakeBot:
    def __init__(self):
        self.calls = []

    async def copy_message(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["chat_id"] == "@second_channel":
            raise RuntimeError("telegram error")


class AdminChannelPostTests(unittest.TestCase):
    def test_admin_can_select_one_or_all_channels(self):
        keyboard = post_channels_keyboard(CHANNELS, {1, 3})
        self.assertTrue(keyboard.inline_keyboard[0][0].text.startswith("✅"))
        self.assertTrue(keyboard.inline_keyboard[1][0].text.startswith("⬜"))
        self.assertTrue(keyboard.inline_keyboard[2][0].text.startswith("✅"))
        self.assertEqual(
            keyboard.inline_keyboard[0][0].callback_data,
            "postadmin:toggle:1",
        )
        self.assertTrue(any(
            button.callback_data == "postadmin:all"
            for row in keyboard.inline_keyboard
            for button in row
        ))

    def test_copy_continues_when_one_channel_fails(self):
        bot = FakeBot()
        with patch("handlers.admin_channel_post.asyncio.sleep", new=AsyncMock()):
            sent, failed = asyncio.run(copy_post_to_channels(
                bot,
                source_chat_id=101,
                source_message_id=55,
                channels=CHANNELS,
            ))
        self.assertEqual([item["id"] for item in sent], [1, 3])
        self.assertEqual([item["id"] for item in failed], [2])
        self.assertEqual(len(bot.calls), 3)
        self.assertTrue(all(call["from_chat_id"] == 101 for call in bot.calls))
        self.assertTrue(all(call["message_id"] == 55 for call in bot.calls))

    def test_flow_requires_preview_confirmation_and_blocks_double_send(self):
        source = Path("handlers/admin_channel_post.py").read_text(encoding="utf-8")
        self.assertIn('Command("post_admin")', source)
        self.assertIn("message.photo", source)
        self.assertIn("message.caption", source)
        self.assertIn("ChannelPostState.confirming", source)
        self.assertIn("ChannelPostState.sending", source)
        self.assertIn('F.data == "postadmin:send"', source)
        self.assertIn("await bot.copy_message(", source)


if __name__ == "__main__":
    unittest.main()
