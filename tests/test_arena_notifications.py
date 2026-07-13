import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if "dotenv" not in sys.modules:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv

if "aiogram" not in sys.modules:
    class WebAppInfo:
        def __init__(self, *, url):
            self.url = url

    class InlineKeyboardButton:
        def __init__(self, *, text, web_app):
            self.text = text
            self.web_app = web_app

    class InlineKeyboardMarkup:
        def __init__(self, *, inline_keyboard):
            self.inline_keyboard = inline_keyboard

    aiogram = types.ModuleType("aiogram")
    aiogram_types = types.ModuleType("aiogram.types")
    aiogram_types.InlineKeyboardButton = InlineKeyboardButton
    aiogram_types.InlineKeyboardMarkup = InlineKeyboardMarkup
    aiogram_types.WebAppInfo = WebAppInfo
    aiogram.types = aiogram_types
    sys.modules["aiogram"] = aiogram
    sys.modules["aiogram.types"] = aiogram_types

from services.arena_notifications import (
    ArenaNotification,
    arena_notification_keyboard,
    format_arena_notification,
    send_arena_notification,
)


class FakeBot:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []

    async def send_message(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("secret backend response")


class ArenaNotificationTests(unittest.TestCase):
    def test_all_notification_messages_are_available(self):
        for notification in ArenaNotification:
            text = format_arena_notification(notification, match_id=42)
            self.assertIn("<code>42</code>", text)

    def test_user_content_is_html_escaped(self):
        text = format_arena_notification(
            ArenaNotification.ADMIN_REVIEW,
            match_id=7,
            detail='<script token="secret">',
            amount="1<2",
        )
        self.assertNotIn("<script", text)
        self.assertIn("&lt;script", text)
        self.assertIn("1&lt;2", text)

    def test_configured_notification_has_miniapp_button(self):
        with patch(
            "services.arena_notifications.build_arena_miniapp_url",
            return_value="https://miniapp.example/?section=arena",
        ):
            markup = arena_notification_keyboard(
                ArenaNotification.READY_REQUIRED, match_id=42
            )
        self.assertEqual(
            markup.inline_keyboard[0][0].web_app.url,
            "https://miniapp.example/?section=arena",
        )

    def test_delivery_success_uses_formatted_message(self):
        bot = FakeBot()
        delivered = asyncio.run(
            send_arena_notification(
                bot,
                123,
                ArenaNotification.ROOM_CODE_READY,
                match_id=42,
            )
        )
        self.assertTrue(delivered)
        self.assertEqual(bot.calls[0]["chat_id"], 123)
        self.assertIn("Room Code", bot.calls[0]["text"])

    def test_delivery_failure_is_contained_and_safely_logged(self):
        bot = FakeBot(fail=True)
        with self.assertLogs("services.arena_notifications", level="WARNING") as logs:
            delivered = asyncio.run(
                send_arena_notification(
                    bot, 123, ArenaNotification.CANCELLED, match_id=42
                )
            )
        self.assertFalse(delivered)
        output = " ".join(logs.output)
        self.assertNotIn("secret backend response", output)
        self.assertNotIn("123", output)


if __name__ == "__main__":
    unittest.main()
