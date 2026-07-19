import asyncio
import unittest

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.methods import SendMessage

from services import campaign_delivery
from services.campaign_delivery import CampaignDeliveryWorker, notification_keyboard, notification_text
from services.campaign_delivery_api import CampaignDeliveryApi, CampaignDeliveryApiError


def recipient(**overrides):
    value = {
        "recipient_id": 11, "campaign_id": 7, "telegram_id": 1001,
        "title": "Premium <sale>", "message": "Bugun & hozir", "image_url": None,
        "button_text": "Ochish", "button_action": "COIN_SHOP", "button_target": None,
        "promotion_id": None, "claimed_at": "2026-07-19T10:00:00Z",
    }
    value.update(overrides)
    return value


class FakeApi:
    def __init__(self, rows=None, sent_error=None):
        self.rows = list(rows or [])
        self.sent_error = sent_error
        self.sent_calls = []
        self.failed_calls = []
        self.recalculate_calls = []

    async def claim(self):
        rows, self.rows = self.rows, []
        return rows

    async def sent(self, *args):
        self.sent_calls.append(args)
        if self.sent_error:
            raise self.sent_error
        return {"status": "SENT", "final": True}

    async def failed(self, *args):
        self.failed_calls.append(args)
        return {"status": "FAILED" if not args[3] else "PENDING", "final": not args[3], "retry_count": 1}

    async def recalculate(self, campaign_id):
        self.recalculate_calls.append(campaign_id)
        return {"campaign_id": campaign_id}


class FakeBot:
    def __init__(self, errors=None):
        self.errors = list(errors or [])
        self.messages = []
        self.photos = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)
        if self.errors:
            error = self.errors.pop(0)
            if error:
                raise error

    async def send_photo(self, **kwargs):
        self.photos.append(kwargs)
        if self.errors:
            error = self.errors.pop(0)
            if error:
                raise error


async def no_sleep(_delay):
    return None


class CampaignDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_delivery_sent_callback_and_statistics(self):
        api = FakeApi([recipient()])
        bot = FakeBot()
        worker = CampaignDeliveryWorker(bot, api, rate_delay_seconds=0, sleep=no_sleep)
        result = await worker.process_batch()
        self.assertEqual((result.claimed, result.sent, result.failed), (1, 1, 0))
        self.assertEqual(len(bot.messages), 1)
        self.assertEqual(api.sent_calls[0][0:2], (11, "2026-07-19T10:00:00Z"))
        self.assertEqual(api.failed_calls, [])
        self.assertEqual(api.recalculate_calls, [7])

    async def test_banner_uses_photo_and_escapes_html(self):
        api = FakeApi([recipient(image_url="https://cdn.example/banner.webp")])
        bot = FakeBot()
        await CampaignDeliveryWorker(bot, api, rate_delay_seconds=0, sleep=no_sleep).process_batch()
        self.assertEqual(len(bot.photos), 1)
        self.assertIn("&lt;sale&gt;", bot.photos[0]["caption"])
        self.assertIn("&amp;", bot.photos[0]["caption"])

    async def test_rate_limit_uses_retry_after_and_exponential_backoff(self):
        method = SendMessage(chat_id=1001, text="test")
        errors = [TelegramRetryAfter(method, "limited", retry_after=2), None]
        bot = FakeBot(errors)
        api = FakeApi([recipient()])
        sleeps = []

        async def record_sleep(delay):
            sleeps.append(delay)

        result = await CampaignDeliveryWorker(
            bot, api, rate_delay_seconds=0, rate_limit_retries=2,
            backoff_seconds=1, sleep=record_sleep,
        ).process_batch()
        self.assertEqual(result.sent, 1)
        self.assertEqual(result.retries, 1)
        self.assertEqual(sleeps, [2.0])
        self.assertEqual(len(bot.messages), 2)

    async def test_permanent_failure_uses_backend_failed_contract(self):
        error = TelegramForbiddenError(SendMessage(chat_id=1001, text="x"), "bot blocked")
        api = FakeApi([recipient()])
        result = await CampaignDeliveryWorker(
            FakeBot([error]), api, rate_delay_seconds=0, sleep=no_sleep,
        ).process_batch()
        self.assertEqual(result.failed, 1)
        self.assertFalse(api.failed_calls[0][3])
        self.assertEqual(api.failed_calls[0][2], "TelegramForbiddenError")
        self.assertEqual(api.recalculate_calls, [7])

    async def test_sent_callback_failure_leaves_claim_for_ttl_recovery(self):
        api = FakeApi([recipient()], sent_error=CampaignDeliveryApiError("offline"))
        result = await CampaignDeliveryWorker(
            FakeBot(), api, rate_delay_seconds=0, sleep=no_sleep,
        ).process_batch()
        self.assertEqual(result.sent, 0)
        self.assertEqual(api.failed_calls, [])
        self.assertEqual(api.recalculate_calls, [7])

    async def test_empty_claim_returns_without_delivery(self):
        api = FakeApi([])
        result = await CampaignDeliveryWorker(FakeBot(), api, sleep=no_sleep).process_batch()
        self.assertEqual(result.claimed, 0)
        self.assertEqual(api.recalculate_calls, [])

    def test_inline_buttons_map_url_and_miniapp_actions(self):
        original = campaign_delivery.CAMPAIGN_MINIAPP_URL
        campaign_delivery.CAMPAIGN_MINIAPP_URL = "https://miniapp.example/app"
        try:
            miniapp = notification_keyboard(recipient(promotion_id=55))
            web_app_url = miniapp.inline_keyboard[0][0].web_app.url
            self.assertIn("page=promotions", web_app_url)
            self.assertIn("promotion_id=55", web_app_url)
            external = notification_keyboard(recipient(button_action="URL", button_target="https://example.com/deal"))
            self.assertEqual(external.inline_keyboard[0][0].url, "https://example.com/deal")
            self.assertIsNone(notification_keyboard(recipient(button_action="NONE")))
        finally:
            campaign_delivery.CAMPAIGN_MINIAPP_URL = original

    def test_message_text_is_safe_html(self):
        text = notification_text(recipient())
        self.assertEqual(text, "<b>Premium &lt;sale&gt;</b>\n\nBugun &amp; hozir")


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def json(self):
        return self.payload


class FakeSession:
    calls = []
    responses = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class CampaignDeliveryApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeSession.calls = []
        FakeSession.responses = []
        self.api = CampaignDeliveryApi("https://backend.example/", "secret", FakeSession)

    async def test_exact_internal_routes_and_auth(self):
        FakeSession.responses = [
            FakeResponse(200, [recipient()]), FakeResponse(200, {"status": "SENT"}),
            FakeResponse(200, {"status": "FAILED"}), FakeResponse(200, {"campaign_id": 7}),
        ]
        await self.api.claim()
        await self.api.sent(11, recipient()["claimed_at"], 0.2)
        await self.api.failed(11, recipient()["claimed_at"], "timeout", True, 0.3)
        await self.api.recalculate(7)
        self.assertEqual([call[0] for call in FakeSession.calls], [
            "https://backend.example/internal/campaigns/recipients/claim",
            "https://backend.example/internal/campaigns/recipients/11/sent",
            "https://backend.example/internal/campaigns/recipients/11/failed",
            "https://backend.example/internal/campaigns/7/recalculate",
        ])
        self.assertTrue(all(call[1]["headers"] == {"X-Internal-Api-Key": "secret"} for call in FakeSession.calls))
        self.assertNotIn("telegram_id", FakeSession.calls[1][1]["json"])

    async def test_internal_api_failure_is_safe(self):
        FakeSession.responses = [FakeResponse(403, {"detail": "secret detail"})]
        with self.assertRaisesRegex(CampaignDeliveryApiError, "HTTP 403"):
            await self.api.claim()
