import pathlib
import unittest
from unittest.mock import patch

from handlers.admin_shop import is_shop_admin, parse_price
from handlers.shop import parse_efc_amount, parse_ticket_quantity, shop_keyboard
from handlers.start import miniapp_keyboard
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

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
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
        self.assertEqual(str(parse_price("7,50")), "7.50")
        self.assertIsNone(parse_price("0"))

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

    async def test_admin_can_read_and_update_shop_prices(self):
        await api.get_shop_admin_settings()
        await api.update_shop_admin_settings(42, "750", "7.5")
        self.assertEqual(FakeSession.calls[0][0], "GET")
        self.assertEqual(
            FakeSession.calls[0][1],
            "https://backend.example/internal/shop/admin/settings",
        )
        self.assertEqual(FakeSession.calls[1][0], "PUT")
        self.assertEqual(FakeSession.calls[1][2]["json"], {
            "admin_id": 42,
            "efc_price_uzs": "750",
            "ticket_price_efc": "7.5",
        })

    def test_admin_price_handler_is_registered_and_guarded(self):
        root = pathlib.Path(__file__).parents[1]
        source = (root / "handlers" / "admin_shop.py").read_text(encoding="utf-8")
        bot = (root / "bot.py").read_text(encoding="utf-8")
        self.assertIn('Command("shop_admin")', source)
        self.assertIn("is_shop_admin", source)
        self.assertIn("dp.include_router(admin_shop_router)", bot)
        with patch("handlers.admin_shop.ADMIN_USER_IDS", {42}), patch(
            "handlers.admin_shop.ADMIN_CHAT_ID", 0
        ):
            self.assertTrue(is_shop_admin(42))
            self.assertFalse(is_shop_admin(43))

    def test_shop_is_reachable_from_start_and_wallet(self):
        root = pathlib.Path(__file__).parents[1]
        start = (root / "handlers" / "start.py").read_text(encoding="utf-8")
        wallet = (root / "handlers" / "wallet.py").read_text(encoding="utf-8")
        bot = (root / "bot.py").read_text(encoding="utf-8")
        self.assertIn('callback_data="shop:open"', start)
        self.assertIn('callback_data="shop:open"', wallet)
        self.assertIn("dp.include_router(shop_router)", bot)

    def test_shop_admin_control_is_visible_only_to_admins(self):
        user_callbacks = [
            button.callback_data
            for row in shop_keyboard(admin=False).inline_keyboard
            for button in row
        ]
        admin_callbacks = [
            button.callback_data
            for row in shop_keyboard(admin=True).inline_keyboard
            for button in row
        ]
        self.assertNotIn("shop_admin:open", user_callbacks)
        self.assertIn("shop_admin:open", admin_callbacks)

    def test_start_shop_does_not_depend_on_miniapp_url(self):
        with patch("handlers.start.MINIAPP_URL", ""):
            callbacks = [
                button.callback_data
                for row in miniapp_keyboard().inline_keyboard
                for button in row
            ]
        self.assertIn("shop:open", callbacks)

    def test_start_exposes_shop_price_control_only_to_admins(self):
        user_callbacks = [
            button.callback_data
            for row in miniapp_keyboard(admin=False).inline_keyboard
            for button in row
        ]
        admin_callbacks = [
            button.callback_data
            for row in miniapp_keyboard(admin=True).inline_keyboard
            for button in row
        ]
        self.assertNotIn("shop_admin:open", user_callbacks)
        self.assertIn("shop_admin:open", admin_callbacks)


if __name__ == "__main__":
    unittest.main()
