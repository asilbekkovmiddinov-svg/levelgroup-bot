import asyncio
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


if "dotenv" not in sys.modules:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv

if "aiogram" not in sys.modules:
    class WebAppInfo:
        def __init__(self, *, url):
            self.url = url

    class InlineKeyboardButton:
        def __init__(self, *, text, web_app=None, callback_data=None):
            self.text = text
            self.web_app = web_app
            self.callback_data = callback_data

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

from services import match_api
from services.arena_evidence_state import ArenaEvidenceStore, DuplicateEvidenceError
from services.arena_moderation import (
    ArenaDecision,
    ArenaModerationRequest,
    apply_arena_decision,
)
from services.arena_notifications import ArenaNotification, send_arena_notification
from tests.arena_smoke_helper import ArenaSmokeBackend, RecordingBot


class ArenaEndToEndSmokeTests(unittest.TestCase):
    def run_async(self, awaitable):
        return asyncio.run(awaitable)

    def test_complete_winner_flow_and_notification(self):
        async def scenario():
            backend = ArenaSmokeBackend()
            with patch.object(match_api, "client", backend):
                match = await match_api.create_match(
                    "creator-init", 100, "2030-01-01T12:00:00"
                )
                match_id = match["id"]
                await match_api.accept_match(match_id, "opponent-init")
                await match_api.start_ready_check(match_id)
                await match_api.set_player_ready(match_id, "creator-init")
                await match_api.set_player_ready(match_id, "opponent-init")
                ready = await match_api.finish_ready_check(match_id)
                self.assertEqual(ready["status"], "ROOM_READY")
                playing = await match_api.create_room_code(
                    match_id, "creator-init", "ROOM-42"
                )
                self.assertEqual(playing["status"], "PLAYING")

                for telegram_id, screenshot, video in (
                    (1001, "creator-photo", "creator-video"),
                    (2002, "opponent-photo", "opponent-video"),
                ):
                    await match_api.upload_internal_evidence(
                        match_id, telegram_id, screenshot_file_id=screenshot
                    )
                    evidence = await match_api.upload_internal_evidence(
                        match_id, telegram_id, video_file_id=video
                    )
                self.assertEqual(evidence["status"], "WAITING_ADMIN")

                with patch(
                    "services.arena_moderation.resolve_match",
                    match_api.resolve_match,
                ):
                    resolved = await apply_arena_decision(
                        ArenaModerationRequest(
                            match_id,
                            ArenaDecision.PLAYER_1_WIN,
                            winner_telegram_id=1001,
                        ),
                        admin_telegram_id=9001,
                    )
                self.assertEqual(resolved["status"], "COMPLETED")
                self.assertEqual(resolved["winner_telegram_id"], 1001)

            bot = RecordingBot()
            delivered = await send_arena_notification(
                bot,
                1001,
                ArenaNotification.WINNER,
                match_id=match_id,
                amount=resolved["winner_reward"],
            )
            self.assertTrue(delivered)
            self.assertIn("g‘olib", bot.messages[0]["text"])
            self.assertTrue(
                all(call["internal"] for call in backend.calls if "internal" in call["path"])
            )

        self.run_async(scenario())

    def test_refund_and_cancel_resolve_contracts(self):
        async def scenario():
            backend = ArenaSmokeBackend()
            with patch.object(match_api, "client", backend):
                refund_match = await match_api.create_match(
                    "creator-init", 100, "2030-01-01T12:00:00"
                )
                refunded = await match_api.resolve_match(
                    refund_match["id"], 9001, decision="REFUND"
                )
                cancel_match = await match_api.create_match(
                    "creator-init", 100, "2030-01-01T12:00:00"
                )
                cancelled = await match_api.resolve_match(
                    cancel_match["id"], 9001, decision="CANCEL"
                )
            self.assertEqual(refunded["decision"], "REFUND")
            self.assertEqual(refunded["status"], "COMPLETED")
            self.assertEqual(cancelled["decision"], "CANCEL")
            self.assertEqual(cancelled["status"], "CANCELLED")

        self.run_async(scenario())

    def test_duplicate_and_restart_recovery_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "arena-smoke.db")
            store = ArenaEvidenceStore(path)
            store.start(1001, 42)
            store.mark_accepted(1001, media_type="screenshot", file_id="photo")
            with self.assertRaises(DuplicateEvidenceError):
                store.mark_accepted(1001, media_type="screenshot", file_id="other")
            recovered = ArenaEvidenceStore(path).get(1001)
            self.assertEqual(recovered.match_id, 42)
            self.assertEqual(recovered.screenshot_file_id, "photo")

    def test_notification_transport_failure_is_non_fatal(self):
        bot = RecordingBot(fail=True)
        with self.assertLogs("services.arena_notifications", level="WARNING") as logs:
            delivered = self.run_async(
                send_arena_notification(
                    bot, 1001, ArenaNotification.CANCELLED, match_id=42
                )
            )
        self.assertFalse(delivered)
        self.assertNotIn("private transport detail", " ".join(logs.output))


if __name__ == "__main__":
    unittest.main()
