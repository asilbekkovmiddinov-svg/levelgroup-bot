import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


try:
    import aiohttp  # noqa: F401
except ModuleNotFoundError:
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientError = type("ClientError", (Exception,), {})
    aiohttp.ClientConnectionError = type(
        "ClientConnectionError", (aiohttp.ClientError,), {}
    )
    aiohttp.ContentTypeError = type("ContentTypeError", (aiohttp.ClientError,), {})

    class ClientTimeout:
        def __init__(self, total):
            self.total = total

    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.ClientSession = object
    sys.modules["aiohttp"] = aiohttp

if "dotenv" not in sys.modules:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv

from services.arena_moderation import (
    ArenaDecision,
    ArenaModerationInProgressError,
    ArenaModerationRequest,
    apply_arena_decision,
    moderation_error_message,
)
from services.match_api import ArenaApiError


class ArenaModerationTests(unittest.TestCase):
    def test_all_decisions_use_internal_resolve_wrapper(self):
        cases = (
            (ArenaDecision.PLAYER_1_WIN, 101),
            (ArenaDecision.PLAYER_2_WIN, 202),
            (ArenaDecision.TECHNICAL_WIN, None),
            (ArenaDecision.REFUND, None),
            (ArenaDecision.CANCEL, None),
        )
        for decision, winner_id in cases:
            resolver = AsyncMock(return_value={"id": 42, "status": "COMPLETED"})
            with self.subTest(decision=decision), patch(
                "services.arena_moderation.resolve_match", resolver
            ):
                result = asyncio.run(
                    apply_arena_decision(
                        ArenaModerationRequest(42, decision, winner_id),
                        admin_telegram_id=9,
                    )
                )
            self.assertEqual(result["id"], 42)
            resolver.assert_awaited_once_with(
                match_id=42,
                admin_telegram_id=9,
                winner_telegram_id=winner_id,
                decision=decision.value,
                admin_comment="Admin moderation qarori",
            )

    def test_parallel_double_click_is_blocked(self):
        entered = asyncio.Event()
        release = asyncio.Event()

        async def resolver(**_kwargs):
            entered.set()
            await release.wait()
            return {"id": 42}

        async def scenario():
            request = ArenaModerationRequest(42, ArenaDecision.CANCEL)
            first = asyncio.create_task(
                apply_arena_decision(request, admin_telegram_id=9)
            )
            await entered.wait()
            with self.assertRaises(ArenaModerationInProgressError):
                await apply_arena_decision(request, admin_telegram_id=9)
            release.set()
            await first

        with patch("services.arena_moderation.resolve_match", resolver):
            asyncio.run(scenario())

    def test_safe_http_error_mapping(self):
        self.assertIn(
            "avval qo‘llangan",
            moderation_error_message(ArenaApiError("raw", status=409)),
        )
        for status in (401, 403):
            message = moderation_error_message(ArenaApiError("secret", status=status))
            self.assertIn("autentifikatsiyasi", message)
            self.assertNotIn("secret", message)
        self.assertIn(
            "topilmadi", moderation_error_message(ArenaApiError("raw", status=404))
        )
        self.assertIn(
            "vaqtinchalik",
            moderation_error_message(ArenaApiError("raw", status=503)),
        )


if __name__ == "__main__":
    unittest.main()
