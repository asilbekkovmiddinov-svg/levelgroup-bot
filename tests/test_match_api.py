import asyncio
import sys
import types
import unittest
from unittest.mock import patch


try:
    import aiohttp
except ModuleNotFoundError:
    aiohttp = types.ModuleType("aiohttp")

    class ClientError(Exception):
        pass

    class ClientConnectionError(ClientError):
        pass

    class ContentTypeError(ClientError):
        pass

    class ClientTimeout:
        def __init__(self, total):
            self.total = total

    aiohttp.ClientError = ClientError
    aiohttp.ClientConnectionError = ClientConnectionError
    aiohttp.ContentTypeError = ContentTypeError
    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.ClientSession = object
    sys.modules["aiohttp"] = aiohttp

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv

from services import match_api


class FakeResponse:
    def __init__(self, status=200, payload=None, json_error=None):
        self.status = status
        self.payload = payload if payload is not None else {"id": 42}
        self.json_error = json_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeRequest:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    async def __aenter__(self):
        if self.error:
            raise self.error
        return self.response

    async def __aexit__(self, *_):
        return False


class FakeSession:
    def __init__(self, factory):
        self.factory = factory

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def request(self, method, url, **kwargs):
        self.factory.calls.append((method, url, kwargs))
        item = self.factory.items.pop(0)
        if isinstance(item, BaseException):
            return FakeRequest(error=item)
        return FakeRequest(response=item)


class FakeSessionFactory:
    def __init__(self, *items):
        self.items = list(items)
        self.calls = []
        self.timeouts = []

    def __call__(self, *, timeout):
        self.timeouts.append(timeout.total)
        return FakeSession(self)


async def no_sleep(_seconds):
    return None


class ArenaApiClientTests(unittest.TestCase):
    def run_async(self, awaitable):
        return asyncio.run(awaitable)

    def client(self, factory, **kwargs):
        return match_api.ArenaApiClient(
            base_url="https://backend.example",
            retries=kwargs.pop("retries", 0),
            timeout_seconds=kwargs.pop("timeout_seconds", 3),
            internal_api_key=kwargs.pop("internal_api_key", "internal-key"),
            session_factory=factory,
            sleep=no_sleep,
            **kwargs,
        )

    def test_user_authentication_header_and_response(self):
        factory = FakeSessionFactory(FakeResponse(payload={"id": 42, "status": "PLAYING"}))
        result = self.run_async(
            self.client(factory).request(
                "GET", "/matches/42", init_data="verified-init-data"
            )
        )

        self.assertEqual(result["id"], 42)
        headers = factory.calls[0][2]["headers"]
        self.assertEqual(headers, {"X-Telegram-Init-Data": "verified-init-data"})
        self.assertEqual(factory.timeouts, [3])

    def test_missing_user_auth_is_rejected_before_network(self):
        factory = FakeSessionFactory()
        with self.assertRaises(match_api.ArenaAuthenticationError):
            self.run_async(self.client(factory).request("GET", "/matches/open"))
        self.assertEqual(factory.calls, [])

    def test_legacy_numeric_identity_is_not_treated_as_init_data(self):
        factory = FakeSessionFactory()
        with self.assertRaises(match_api.ArenaAuthenticationError):
            self.run_async(
                self.client(factory).request(
                    "GET", "/matches/42", init_data=123456789
                )
            )
        self.assertEqual(factory.calls, [])

    def test_internal_request_uses_only_internal_header(self):
        factory = FakeSessionFactory(FakeResponse(payload={"matches": []}))
        self.run_async(
            self.client(factory).request(
                "GET", "/matches/worker/due-scheduled", internal=True
            )
        )
        self.assertEqual(
            factory.calls[0][2]["headers"],
            {"X-Internal-Api-Key": "internal-key"},
        )

    def test_timeout_is_retried_and_returns_safe_error(self):
        factory = FakeSessionFactory(asyncio.TimeoutError(), asyncio.TimeoutError())
        with self.assertRaises(match_api.ArenaTimeoutError) as error:
            self.run_async(
                self.client(factory, retries=1).request(
                    "GET", "/matches/open", init_data="init-data"
                )
            )
        self.assertTrue(error.exception.retryable)
        self.assertEqual(len(factory.calls), 2)

    def test_network_error_is_retried(self):
        factory = FakeSessionFactory(
            aiohttp.ClientConnectionError(),
            FakeResponse(payload={"matches": []}),
        )
        result = self.run_async(
            self.client(factory, retries=1).request(
                "GET", "/matches/open", init_data="init-data"
            )
        )
        self.assertEqual(result, {"matches": []})
        self.assertEqual(len(factory.calls), 2)

    def test_retryable_http_error_then_success(self):
        factory = FakeSessionFactory(
            FakeResponse(status=503, payload={"detail": "private upstream detail"}),
            FakeResponse(payload={"matches": []}),
        )
        result = self.run_async(
            self.client(factory, retries=1).request(
                "GET", "/matches/open", init_data="init-data"
            )
        )
        self.assertEqual(result, {"matches": []})
        self.assertEqual(len(factory.calls), 2)

    def test_non_retryable_error_is_mapped_without_raw_response(self):
        factory = FakeSessionFactory(FakeResponse(status=404, payload={}))
        with self.assertRaises(match_api.ArenaApiError) as error:
            self.run_async(
                self.client(factory, retries=2).request(
                    "GET", "/matches/99", init_data="init-data"
                )
            )
        self.assertEqual(error.exception.status, 404)
        self.assertEqual(str(error.exception), "Arena match topilmadi.")
        self.assertEqual(len(factory.calls), 1)

    def test_malformed_success_response_is_rejected(self):
        factory = FakeSessionFactory(FakeResponse(payload=["not", "an", "object"]))
        with self.assertRaises(match_api.ArenaResponseError):
            self.run_async(
                self.client(factory).request(
                    "GET", "/matches/open", init_data="init-data"
                )
            )

    def test_backend_contract_wrappers_do_not_send_identity_fields(self):
        class Recorder:
            def __init__(self):
                self.calls = []

            async def request(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                return {"id": 42}

        recorder = Recorder()
        with patch.object(match_api, "client", recorder):
            self.run_async(match_api.create_match("init", 100, "2030-01-01T12:00:00"))
            self.run_async(match_api.accept_match(42, "init"))
            self.run_async(match_api.set_player_ready(42, "init"))

        create_payload = recorder.calls[0][1]["json"]
        accept_payload = recorder.calls[1][1]["json"]
        ready_payload = recorder.calls[2][1]["json"]
        self.assertEqual(create_payload["stake_efc"], 100)
        self.assertTrue(create_payload["rules_accepted"])
        self.assertEqual(accept_payload, {"rules_accepted": True})
        self.assertEqual(ready_payload, {})
        for payload in (create_payload, accept_payload, ready_payload):
            self.assertNotIn("telegram_id", payload)
            self.assertNotIn("creator_telegram_id", payload)
            self.assertNotIn("opponent_telegram_id", payload)

    def test_internal_evidence_uses_internal_endpoint_and_identity_body(self):
        class Recorder:
            def __init__(self):
                self.calls = []

            async def request(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                return {"id": 42, "status": "PLAYING"}

        recorder = Recorder()
        with patch.object(match_api, "client", recorder):
            result = self.run_async(
                match_api.upload_internal_evidence(
                    match_id=42,
                    telegram_id=1001,
                    screenshot_file_id="photo-id",
                )
            )

        self.assertEqual(result["id"], 42)
        args, kwargs = recorder.calls[0]
        self.assertEqual(args, ("POST", "/matches/internal/evidence"))
        self.assertTrue(kwargs["internal"])
        self.assertEqual(
            kwargs["json"],
            {
                "match_id": 42,
                "telegram_id": 1001,
                "screenshot_file_id": "photo-id",
            },
        )


if __name__ == "__main__":
    unittest.main()
