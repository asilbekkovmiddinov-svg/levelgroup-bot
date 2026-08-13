import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.enums import ChatMemberStatus

from handlers.start import missing_channels


class RequiredChannelsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_only_missing_channel(self):
        bot = SimpleNamespace(get_chat_member=AsyncMock())
        bot.get_chat_member.side_effect = [
            SimpleNamespace(status=ChatMemberStatus.MEMBER),
            SimpleNamespace(status=ChatMemberStatus.LEFT),
        ]
        result = await missing_channels(bot, 123)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["chat_id"], "@levelgroup_buyurtmalar")

    async def test_all_joined_returns_empty(self):
        bot = SimpleNamespace(get_chat_member=AsyncMock())
        bot.get_chat_member.side_effect = [
            SimpleNamespace(status=ChatMemberStatus.MEMBER),
            SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR),
        ]
        self.assertEqual(await missing_channels(bot, 123), [])

    async def test_verification_error_fails_closed(self):
        bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=RuntimeError("telegram unavailable")))
        result = await missing_channels(bot, 123)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
