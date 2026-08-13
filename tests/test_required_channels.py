from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatMemberStatus

from handlers.start import missing_channels


@pytest.mark.asyncio
async def test_returns_only_missing_channel():
    bot = SimpleNamespace(get_chat_member=AsyncMock())
    bot.get_chat_member.side_effect = [
        SimpleNamespace(status=ChatMemberStatus.MEMBER),
        SimpleNamespace(status=ChatMemberStatus.LEFT),
    ]

    result = await missing_channels(bot, 123)

    assert len(result) == 1
    assert result[0]["chat_id"] == "@levelgroup_buyurtmalar"


@pytest.mark.asyncio
async def test_all_joined_returns_empty():
    bot = SimpleNamespace(get_chat_member=AsyncMock())
    bot.get_chat_member.side_effect = [
        SimpleNamespace(status=ChatMemberStatus.MEMBER),
        SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR),
    ]

    assert await missing_channels(bot, 123) == []


@pytest.mark.asyncio
async def test_verification_error_fails_closed():
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=RuntimeError("telegram unavailable")))

    result = await missing_channels(bot, 123)

    assert len(result) == 2
