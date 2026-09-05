from services.match_api import ArenaApiClient, ArenaApiError


client = ArenaApiClient()


async def active_match(telegram_id: int):
    return await client.request(
        "GET",
        f"/internal/arena/v5/users/{telegram_id}/active-match",
        internal=True,
    )


async def validate_relay(telegram_id: int, token: str):
    return await client.request(
        "POST",
        "/internal/arena/v5/relay/validate",
        internal=True,
        json={"telegram_id": telegram_id, "token": token},
    )


async def prepare_submission(
    telegram_id: int, telegram_file_id: str, telegram_message_id: int
):
    return await client.request(
        "POST",
        "/internal/arena/v5/submissions/prepare",
        internal=True,
        json={
            "telegram_id": telegram_id,
            "telegram_file_id": telegram_file_id,
            "telegram_message_id": telegram_message_id,
        },
    )


async def complete_submission(submission_id: int, channel_message_id: int):
    return await client.request(
        "POST",
        f"/internal/arena/v5/submissions/{submission_id}/complete",
        internal=True,
        json={"admin_channel_message_id": channel_message_id},
    )


async def fail_submission(submission_id: int, error: str):
    return await client.request(
        "POST",
        f"/internal/arena/v5/submissions/{submission_id}/failed",
        internal=True,
        json={"error": error[:255] or "Telegram delivery failed"},
    )


async def list_seasons():
    return await client.request(
        "GET",
        "/internal/arena/v5/seasons",
        internal=True,
    )


async def create_season(
    *, admin_id: int, name: str, duration_days: int, prize_text: str | None
):
    return await client.request(
        "POST",
        "/internal/arena/v5/seasons",
        internal=True,
        json={
            "admin_id": admin_id,
            "name": name,
            "duration_days": duration_days,
            "prize_text": prize_text,
        },
    )


async def finish_season(season_id: int, *, admin_id: int):
    return await client.request(
        "POST",
        f"/internal/arena/v5/seasons/{season_id}/finish",
        internal=True,
        json={"admin_id": admin_id},
    )


async def update_season_duration(
    season_id: int, *, admin_id: int, duration_days: int
):
    return await client.request(
        "PATCH",
        f"/internal/arena/v5/seasons/{season_id}/duration",
        internal=True,
        json={"admin_id": admin_id, "duration_days": duration_days},
    )


__all__ = [
    "ArenaApiError",
    "active_match",
    "complete_submission",
    "create_season",
    "fail_submission",
    "finish_season",
    "list_seasons",
    "update_season_duration",
    "prepare_submission",
    "validate_relay",
]
