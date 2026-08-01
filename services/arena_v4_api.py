from services.match_api import ArenaApiClient, ArenaApiError


client = ArenaApiClient()


async def list_reviews(review_type: str, *, limit: int = 50):
    return await client.request(
        "GET",
        "/internal/arena/reviews",
        internal=True,
        params={
            "status": "PENDING",
            "review_type": review_type,
            "limit": limit,
            "offset": 0,
        },
    )


async def get_review_detail(review_id: int):
    return await client.request(
        "GET", f"/internal/arena/reviews/{review_id}", internal=True
    )


async def claim_review(review_id: int, admin_id: int):
    return await client.request(
        "POST",
        f"/internal/arena/reviews/{review_id}/claim",
        internal=True,
        json={"admin_id": admin_id},
    )


async def submit_score(
    review_id: int,
    admin_id: int,
    owner_score: int,
    opponent_score: int,
):
    return await client.request(
        "POST",
        f"/internal/arena/reviews/{review_id}/decision",
        internal=True,
        idempotency_key=(
            f"bot:score:{review_id}:{admin_id}:{owner_score}:{opponent_score}"
        ),
        json={
            "admin_id": admin_id,
            "owner_score": owner_score,
            "opponent_score": opponent_score,
            "reason": "Arena Admin Bot V4 score review",
        },
    )


async def submit_match_score(
    match_id: int, admin_id: int, owner_score: int, opponent_score: int,
):
    return await client.request(
        "POST", f"/internal/arena/matches/{match_id}/score", internal=True,
        idempotency_key=f"bot:match-score:{match_id}:{admin_id}:{owner_score}:{opponent_score}",
        json={"admin_id": admin_id, "owner_score": owner_score,
              "opponent_score": opponent_score, "reason": "TELEGRAM_CHANNEL"},
    )


async def cancel_channel_match(match_id: int, admin_id: int, reason: str):
    return await client.request(
        "POST", f"/internal/arena/matches/{match_id}/cancel", internal=True,
        idempotency_key=f"bot:match-cancel:{match_id}:{admin_id}:{reason}",
        json={"admin_id": admin_id, "reason": reason},
    )


async def cancel_match(review_id: int, admin_id: int):
    return await client.request(
        "POST",
        f"/internal/arena/reviews/{review_id}/cancel",
        internal=True,
        idempotency_key=f"bot:cancel:{review_id}:{admin_id}",
        json={
            "admin_id": admin_id,
            "reason": "Arena Admin Bot V4 cancel",
        },
    )


async def submit_appeal_decision(
    review_id: int,
    admin_id: int,
    action: str,
    *,
    owner_score: int | None = None,
    opponent_score: int | None = None,
):
    payload = {
        "admin_id": admin_id,
        "action": action,
        "reason": "Arena Admin Bot V4 appeal review",
    }
    if action == "UPDATE_SCORE":
        payload["owner_score"] = owner_score
        payload["opponent_score"] = opponent_score
    return await client.request(
        "POST",
        f"/internal/arena/reviews/{review_id}/appeal-decision",
        internal=True,
        idempotency_key=(
            f"bot:appeal:{review_id}:{admin_id}:{action}:"
            f"{owner_score}:{opponent_score}"
        ),
        json=payload,
    )


__all__ = [
    "ArenaApiError",
    "cancel_match",
    "claim_review",
    "get_review_detail",
    "list_reviews",
    "submit_appeal_decision",
    "submit_score",
    "submit_match_score",
    "cancel_channel_match",
]
