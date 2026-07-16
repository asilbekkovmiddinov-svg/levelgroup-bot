import unittest
from unittest.mock import patch

from services import api


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

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
        return FakeResponse({"telegram_id": 42, "efc_balance": "10"})

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse({"success": True})


class WalletInternalApiTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_wallet_uses_internal_endpoint_and_key(self):
        wallet = await api.get_wallet(42)

        self.assertEqual(wallet["telegram_id"], 42)
        method, url, kwargs = FakeSession.calls[0]
        self.assertEqual(method, "GET")
        self.assertEqual(url, "https://backend.example/internal/wallet/42")
        self.assertEqual(kwargs["headers"], {"X-Internal-Api-Key": "internal-test-key"})

    async def test_seen_uses_internal_endpoint_and_key(self):
        await api.update_user_seen(42)

        method, url, kwargs = FakeSession.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://backend.example/internal/users/42/seen")
        self.assertEqual(kwargs["headers"], {"X-Internal-Api-Key": "internal-test-key"})

    async def test_register_uses_internal_contract(self):
        await api.register_internal_user(42, "ali", "Ali", "Valiyev")

        method, url, kwargs = FakeSession.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://backend.example/internal/users/register")
        self.assertEqual(kwargs["headers"], {"X-Internal-Api-Key": "internal-test-key"})
        self.assertEqual(kwargs["json"], {
            "telegram_id": 42,
            "username": "ali",
            "first_name": "Ali",
            "last_name": "Valiyev",
        })

    async def test_wallet_admin_actions_use_internal_key(self):
        actions = (
            (api.claim_deposit, (7, 42)),
            (api.approve_deposit, (7, 42)),
            (api.reject_deposit, (7, 42)),
            (api.claim_withdraw, (8, 42)),
            (api.approve_withdraw, (8, 42)),
            (api.reject_withdraw, (8, 42)),
        )

        for action, args in actions:
            FakeSession.calls = []
            await action(*args)
            self.assertEqual(
                FakeSession.calls[0][2]["headers"],
                {"X-Internal-Api-Key": "internal-test-key"},
            )

    async def test_legacy_wallet_create_uses_internal_contract(self):
        await api.create_deposit(42, 15000, "bot-deposit:42:7")
        await api.create_withdraw(42, 20000, "8600", "Ali", "Bank")

        self.assertEqual(FakeSession.calls[0][1], "https://backend.example/internal/deposit/create")
        self.assertEqual(FakeSession.calls[1][1], "https://backend.example/internal/withdraw/create")
        self.assertEqual(FakeSession.calls[0][2]["headers"], {
            "X-Internal-Api-Key": "internal-test-key",
            "Idempotency-Key": "bot-deposit:42:7",
        })
        self.assertEqual(
            FakeSession.calls[1][2]["headers"],
            {"X-Internal-Api-Key": "internal-test-key"},
        )

    async def test_deposit_claim_forwards_receipt_revision(self):
        await api.claim_deposit(7, 42, receipt_revision=3)
        self.assertEqual(FakeSession.calls[0][2]["json"], {"admin_id": 42, "receipt_revision": 3})

    async def test_safe_json_exposes_backend_detail_as_message(self):
        result = await api.safe_json(FakeResponse({"detail": "Deposit must be claimed"}, 409))

        self.assertEqual(result["message"], "Deposit must be claimed")


if __name__ == "__main__":
    unittest.main()
