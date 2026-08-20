import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from handlers.start import missing_channels


class RequiredChannelsTests(unittest.IsolatedAsyncioTestCase):
    async def test_required_subscriptions_are_temporarily_disabled(self):
        bot = SimpleNamespace(get_chat_member=AsyncMock())
        result = await missing_channels(bot, 123)
        self.assertEqual(result, [])
        bot.get_chat_member.assert_not_awaited()

    async def test_telegram_verification_is_not_called_while_disabled(self):
        bot = SimpleNamespace(
            get_chat_member=AsyncMock(side_effect=RuntimeError("telegram unavailable"))
        )
        result = await missing_channels(bot, 123)
        self.assertEqual(result, [])
        bot.get_chat_member.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
