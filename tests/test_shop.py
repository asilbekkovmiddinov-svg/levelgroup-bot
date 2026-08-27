import pathlib
import unittest
from unittest.mock import patch

from handlers.shop import parse_efc_amount, parse_ticket_quantity
from services import api


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def json(self):
        return self.payload


class FakeSession:
    calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse({"success": True, "data": {}})

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse({"success": True, "data": {}})


class ShopTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeSession.calls = []
        self.patches = (
            patch.object(api, "BACKEND_URL", "https://backend.example"),
            patch.object(api, "INTERNAL_API_KEY", "internal-test-key"),
            patch.object(api.aiohttp, "ClientSession", FakeSession),
        )
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    def test_amount_parsers_reject_invalid_values(self):
        self.assertEqual(str(parse_efc_amount("10,50")), "10.50")
        self.assertIsNone(parse_efc_amount("0"))
        self.assertIsNone(parse_efc_amount("1.001"))
        self.assertEqual(parse_ticket_quantity("5"), 5)
        self.assertIsNone(parse_ticket_quantity("-1"))
        self.assertIsNone(parse_ticket_quantity("1.5"))

    async def test_shop_api_uses_internal_auth_and_idempotency(self):
        await api.get_shop_catalog(42)
        await api.buy_shop_efc(42, "10", "efc-key")
        await api.buy_shop_tickets(42, 2, "ticket-key")

        self.assertEqual(
            [call[1] for call in FakeSession.calls],
            [
                "https://backend.example/internal/shop/catalog/42",
                "https://backend.example/internal/shop/buy-efc",
                "https://backend.example/internal/shop/buy-ticket",
            ],
        )
        self.assertEqual(
            FakeSession.calls[0][2]["headers"],
            {"X-Internal-Api-Key": "internal-test-key"},
        )
        self.assertEqual(
            FakeSession.calls[1][2]["headers"]["Idempotency-Key"],
            "efc-key",
        )
        self.assertEqual(
            FakeSession.calls[2][2]["headers"]["Idempotency-Key"],
            "ticket-key",
        )

    def test_shop_is_reachable_from_start_and_wallet(self):
        root = pathlib.Path(__file__).parents[1]
        start = (root / "handlers" / "start.py").read_text(encoding="utf-8")
        wallet = (root / "handlers" / "wallet.py").read_text(encoding="utf-8")
        bot = (root / "bot.py").read_text(encoding="utf-8")
        self.assertIn('callback_data="shop:open"', start)
        self.assertIn('callback_data="shop:open"', wallet)
        self.assertIn("dp.include_router(shop_router)", bot)


if __name__ == "__main__":
    unittest.main()
