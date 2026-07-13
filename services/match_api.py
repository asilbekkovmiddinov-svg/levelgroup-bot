import asyncio
import logging
from typing import Any, TypedDict

import aiohttp

from config import (
    ARENA_API_RETRIES,
    ARENA_API_RETRY_BACKOFF_SECONDS,
    ARENA_API_TIMEOUT_SECONDS,
    ARENA_API_URL,
    INTERNAL_API_KEY,
)


logger = logging.getLogger(__name__)
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class ArenaMatchResponse(TypedDict, total=False):
    id: int
    game_type: str
    creator_display_name: str
    opponent_display_name: str
    efc_amount: str
    total_pool: str
    winner_reward: str
    status: str
    scheduled_at: str
    room_code: str | None


class ArenaMatchListResponse(TypedDict):
    matches: list[ArenaMatchResponse]


class ArenaApiError(ValueError):
    def __init__(self, message: str, *, status: int | None = None, retryable=False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class ArenaAuthenticationError(ArenaApiError):
    pass


class ArenaTimeoutError(ArenaApiError):
    pass


class ArenaNetworkError(ArenaApiError):
    pass


class ArenaResponseError(ArenaApiError):
    pass


def _safe_error_message(status: int, payload: Any) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()[:300]

    messages = {
        400: "Arena so‘rovi noto‘g‘ri.",
        401: "Telegram tasdiqlash ma’lumoti yaroqsiz yoki eskirgan.",
        403: "Bu Arena amalini bajarishga ruxsat yo‘q.",
        404: "Arena match topilmadi.",
        409: "Match holati o‘zgargan. Ma’lumotni yangilang.",
        422: "Arena ma’lumotlari noto‘g‘ri formatda.",
        429: "Arena serveri band. Birozdan keyin qayta urinib ko‘ring.",
    }
    if status >= 500:
        return "Arena serverida vaqtinchalik xatolik yuz berdi."
    return messages.get(status, "Arena so‘rovi bajarilmadi.")


def _validate_response(payload: Any) -> Any:
    if not isinstance(payload, dict):
        raise ArenaResponseError("Arena serveridan noto‘g‘ri javob olindi.")
    if "matches" in payload and not isinstance(payload["matches"], list):
        raise ArenaResponseError("Arena matchlar ro‘yxati noto‘g‘ri formatda.")
    if "id" in payload and not isinstance(payload["id"], int):
        raise ArenaResponseError("Arena match javobi noto‘g‘ri formatda.")
    return payload


class ArenaApiClient:
    def __init__(
        self,
        base_url: str = ARENA_API_URL,
        timeout_seconds: float = ARENA_API_TIMEOUT_SECONDS,
        retries: int = ARENA_API_RETRIES,
        retry_backoff_seconds: float = ARENA_API_RETRY_BACKOFF_SECONDS,
        internal_api_key: str | None = INTERNAL_API_KEY,
        session_factory=aiohttp.ClientSession,
        sleep=asyncio.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=max(1.0, timeout_seconds))
        self.retries = max(0, retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.internal_api_key = internal_api_key
        self.session_factory = session_factory
        self.sleep = sleep

    async def request(
        self,
        method: str,
        path: str,
        *,
        init_data: str | None = None,
        internal: bool = False,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        if not self.base_url:
            raise ArenaApiError("ARENA_API_URL yoki BACKEND_URL sozlanmagan.")
        headers = {}
        if internal:
            if not self.internal_api_key:
                raise ArenaAuthenticationError("INTERNAL_API_KEY sozlanmagan.")
            headers["X-Internal-Api-Key"] = self.internal_api_key
        else:
            if not isinstance(init_data, str) or not init_data.strip():
                raise ArenaAuthenticationError("Telegram initData talab qilinadi.")
            headers["X-Telegram-Init-Data"] = init_data

        url = f"{self.base_url}{path}"
        last_error: ArenaApiError | None = None
        for attempt in range(self.retries + 1):
            try:
                async with self.session_factory(timeout=self.timeout) as session:
                    async with session.request(
                        method, url, headers=headers, json=json, params=params
                    ) as response:
                        try:
                            payload = await response.json()
                        except (aiohttp.ContentTypeError, ValueError):
                            payload = None

                        if response.status >= 400:
                            retryable = response.status in RETRYABLE_STATUSES
                            error = ArenaApiError(
                                _safe_error_message(response.status, payload),
                                status=response.status,
                                retryable=retryable,
                            )
                            if retryable and attempt < self.retries:
                                last_error = error
                                await self.sleep(
                                    self.retry_backoff_seconds * (attempt + 1)
                                )
                                continue
                            raise error
                        return _validate_response(payload)
            except asyncio.TimeoutError as error:
                last_error = ArenaTimeoutError(
                    "Arena serveri javob bermadi. Qayta urinib ko‘ring.",
                    retryable=True,
                )
            except aiohttp.ClientError as error:
                last_error = ArenaNetworkError(
                    "Arena serveri bilan aloqa o‘rnatilmadi.",
                    retryable=True,
                )
            except ArenaApiError:
                raise

            if attempt < self.retries:
                logger.warning(
                    "Arena API temporary failure; retrying (attempt %s/%s)",
                    attempt + 1,
                    self.retries + 1,
                )
                await self.sleep(self.retry_backoff_seconds * (attempt + 1))

        raise last_error or ArenaApiError("Arena so‘rovi bajarilmadi.")


client = ArenaApiClient()


async def create_match(
    init_data=None,
    stake_efc=None,
    scheduled_at=None,
    game_type="EFOOTBALL",
    **legacy,
):
    if stake_efc is None:
        stake_efc = legacy.get("efc_amount")
    return await client.request(
        "POST",
        "/matches/",
        init_data=init_data,
        json={
            "game_type": game_type,
            "stake_efc": stake_efc,
            "scheduled_at": scheduled_at,
            "rules_accepted": True,
        },
    )


async def get_open_matches(init_data=None, skip=0, limit=20):
    return await client.request(
        "GET", "/matches/open", init_data=init_data, params={"skip": skip, "limit": limit}
    )


async def get_user_matches(init_data=None, skip=0, limit=20):
    return await client.request(
        "GET", "/matches/me", init_data=init_data, params={"skip": skip, "limit": limit}
    )


async def get_match(match_id, init_data=None):
    return await client.request("GET", f"/matches/{match_id}", init_data=init_data)


async def accept_match(match_id, init_data=None):
    return await client.request(
        "POST",
        f"/matches/{match_id}/accept",
        init_data=init_data,
        json={"rules_accepted": True},
    )


async def set_player_ready(match_id, init_data=None):
    return await client.request(
        "POST", f"/matches/{match_id}/ready", init_data=init_data, json={}
    )


async def create_room_code(match_id, init_data=None, room_code=None):
    return await client.request(
        "POST",
        f"/matches/{match_id}/room-code",
        init_data=init_data,
        json={"room_code": room_code},
    )


async def upload_result_screenshot(
    match_id, init_data=None, screenshot_file_id=None, video_file_id=None
):
    payload = {}
    if screenshot_file_id:
        payload["screenshot_file_id"] = screenshot_file_id
    if video_file_id:
        payload["video_file_id"] = video_file_id
    return await client.request(
        "POST", f"/matches/{match_id}/screenshot", init_data=init_data, json=payload
    )


async def upload_internal_evidence(
    match_id,
    telegram_id,
    screenshot_file_id=None,
    video_file_id=None,
):
    payload = {
        "match_id": match_id,
        "telegram_id": telegram_id,
    }
    if screenshot_file_id:
        payload["screenshot_file_id"] = screenshot_file_id
    if video_file_id:
        payload["video_file_id"] = video_file_id
    return await client.request(
        "POST", "/matches/internal/evidence", internal=True, json=payload
    )


async def cancel_match(
    match_id, init_data=None, cancel_reason=None, admin_telegram_id=None
):
    return await client.request(
        "POST",
        f"/matches/{match_id}/cancel",
        init_data=init_data,
        json={"cancel_reason": cancel_reason},
    )


async def get_match_stats(init_data=None):
    return await client.request("GET", "/matches/stats/me", init_data=init_data)


async def get_leaderboard(init_data=None, period="all", limit=20):
    return await client.request(
        "GET",
        "/matches/leaderboard",
        init_data=init_data,
        params={"period": period, "limit": limit},
    )


async def get_match_guide(init_data=None):
    return await client.request("GET", "/matches/guide", init_data=init_data)


async def get_due_scheduled_matches(limit=50):
    return await client.request(
        "GET", "/matches/worker/due-scheduled", internal=True, params={"limit": limit}
    )


async def get_expired_ready_matches(limit=50):
    return await client.request(
        "GET", "/matches/worker/expired-ready", internal=True, params={"limit": limit}
    )


async def start_ready_check(match_id):
    return await client.request(
        "POST", f"/matches/{match_id}/start-ready-check", internal=True
    )


async def finish_ready_check(match_id):
    return await client.request(
        "POST", f"/matches/{match_id}/finish-ready-check", internal=True
    )


async def resolve_match(
    match_id,
    admin_telegram_id,
    winner_telegram_id=None,
    admin_comment=None,
    decision=None,
):
    payload = {
        "admin_telegram_id": admin_telegram_id,
        "winner_telegram_id": winner_telegram_id,
        "admin_comment": admin_comment,
    }
    if decision:
        payload["decision"] = decision
    return await client.request(
        "POST", f"/matches/{match_id}/resolve", internal=True, json=payload
    )
