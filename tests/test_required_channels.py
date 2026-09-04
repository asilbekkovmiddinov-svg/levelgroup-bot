import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.enums import ChatMemberStatus

from handlers.start import SubscriptionConfigUnavailable, missing_channels


CHANNELS = [
    {"id": 1, "chat_id": "@one_channel", "title": "One", "url": "https://t.me/one_channel"},
    {"id": 2, "chat_id": "@two_channel", "title": "Two", "url": "https://t.me/two_channel"},
]


class RequiredChannelsTests(unittest.IsolatedAsyncioTestCase):
    @patch("handlers.start.get_subscription_channels", new_callable=AsyncMock)
    async def test_every_start_loads_current_channels_and_returns_missing(self, get_channels):
        get_channels.return_value = CHANNELS
        bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=[
            SimpleNamespace(status=ChatMemberStatus.MEMBER),
            SimpleNamespace(status=ChatMemberStatus.LEFT),
        ]))
        result = await missing_channels(bot, 123)
        self.assertEqual(result, [CHANNELS[1]])
        get_channels.assert_awaited_once()
        self.assertEqual(bot.get_chat_member.await_count, 2)

    @patch("handlers.start.get_subscription_channels", new_callable=AsyncMock)
    async def test_channel_configuration_failure_is_fail_closed(self, get_channels):
        get_channels.side_effect = RuntimeError("backend unavailable")
        with self.assertRaises(SubscriptionConfigUnavailable):
            await missing_channels(SimpleNamespace(), 123)

    async def test_restricted_non_member_is_missing(self):
        bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=SimpleNamespace(
            status=ChatMemberStatus.RESTRICTED,
            is_member=False,
        )))
        result = await missing_channels(bot, 123, [CHANNELS[0]])
        self.assertEqual(result, [CHANNELS[0]])


if __name__ == "__main__":
    unittest.main()
