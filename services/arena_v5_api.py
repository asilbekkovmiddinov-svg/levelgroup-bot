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


__all__ = [
    "ArenaApiError",
    "active_match",
    "complete_submission",
    "fail_submission",
    "prepare_submission",
    "validate_relay",
]
