import aiohttp

from config import API_BASE_URL


async def _request(method: str, path: str, json: dict | None = None):
    url = f"{API_BASE_URL}{path}"

    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, json=json) as response:
            data = await response.json()

            if response.status >= 400:
                detail = data.get("detail", "Noma’lum xatolik")
                raise ValueError(detail)

            return data


async def create_match(creator_telegram_id: int, efc_amount: float, scheduled_at: str):
    return await _request(
        "POST",
        "/matches/",
        {
            "creator_telegram_id": creator_telegram_id,
            "efc_amount": efc_amount,
            "scheduled_at": scheduled_at,
        },
    )


async def get_open_matches(skip: int = 0, limit: int = 20):
    return await _request(
        "GET",
        f"/matches/open?skip={skip}&limit={limit}",
    )


async def get_user_matches(telegram_id: int, skip: int = 0, limit: int = 20):
    return await _request(
        "GET",
        f"/matches/user/{telegram_id}?skip={skip}&limit={limit}",
    )


async def get_match(match_id: int):
    return await _request(
        "GET",
        f"/matches/{match_id}",
    )


async def accept_match(match_id: int, opponent_telegram_id: int):
    return await _request(
        "POST",
        f"/matches/{match_id}/accept",
        {
            "opponent_telegram_id": opponent_telegram_id,
        },
    )


async def start_ready_check(match_id: int):
    return await _request(
        "POST",
        f"/matches/{match_id}/start-ready-check",
    )


async def set_player_ready(match_id: int, telegram_id: int):
    return await _request(
        "POST",
        f"/matches/{match_id}/ready",
        {
            "telegram_id": telegram_id,
        },
    )


async def finish_ready_check(match_id: int):
    return await _request(
        "POST",
        f"/matches/{match_id}/finish-ready-check",
    )


async def create_room_code(match_id: int, telegram_id: int, room_code: str):
    return await _request(
        "POST",
        f"/matches/{match_id}/room-code",
        {
            "telegram_id": telegram_id,
            "room_code": room_code,
        },
    )


async def upload_result_screenshot(
    match_id: int,
    telegram_id: int,
    screenshot_file_id: str,
):
    return await _request(
        "POST",
        f"/matches/{match_id}/screenshot",
        {
            "telegram_id": telegram_id,
            "screenshot_file_id": screenshot_file_id,
        },
    )


async def resolve_match(
    match_id: int,
    admin_telegram_id: int,
    winner_telegram_id: int,
    admin_comment: str | None = None,
):
    return await _request(
        "POST",
        f"/matches/{match_id}/resolve",
        {
            "admin_telegram_id": admin_telegram_id,
            "winner_telegram_id": winner_telegram_id,
            "admin_comment": admin_comment,
        },
    )


async def cancel_match(
    match_id: int,
    cancel_reason: str,
    admin_telegram_id: int | None = None,
):
    return await _request(
        "POST",
        f"/matches/{match_id}/cancel",
        {
            "admin_telegram_id": admin_telegram_id,
            "cancel_reason": cancel_reason,
        },
    )


async def get_match_stats(telegram_id: int):
    return await _request(
        "GET",
        f"/matches/stats/{telegram_id}",
    )


async def get_leaderboard(period: str = "all", limit: int = 20):
    return await _request(
        "GET",
        f"/matches/leaderboard?period={period}&limit={limit}",
    )


async def get_match_guide():
    return await _request(
        "GET",
        "/matches/guide",
    )
