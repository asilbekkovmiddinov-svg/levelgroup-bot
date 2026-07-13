import asyncio
from dataclasses import dataclass
from enum import StrEnum

from services.match_api import ArenaApiError, resolve_match


class ArenaDecision(StrEnum):
    PLAYER_1_WIN = "PLAYER_1_WIN"
    PLAYER_2_WIN = "PLAYER_2_WIN"
    TECHNICAL_WIN = "TECHNICAL_WIN"
    REFUND = "REFUND"
    CANCEL = "CANCEL"


@dataclass(frozen=True)
class ArenaModerationRequest:
    match_id: int
    decision: ArenaDecision
    winner_telegram_id: int | None = None


class ArenaModerationInProgressError(ValueError):
    pass


_in_flight: set[int] = set()
_guard = asyncio.Lock()


def moderation_error_message(error: Exception) -> str:
    if isinstance(error, ArenaModerationInProgressError):
        return "Bu match uchun qaror hozir qo‘llanmoqda. Biroz kuting."
    if not isinstance(error, ArenaApiError):
        return "Arena qarorini qo‘llashda xavfsiz ichki xatolik yuz berdi."
    if error.status == 409:
        return "Bu match bo‘yicha qaror avval qo‘llangan yoki holat o‘zgargan."
    if error.status in {401, 403}:
        return "Arena internal autentifikatsiyasi noto‘g‘ri yoki sozlanmagan."
    if error.status == 404:
        return "Arena match topilmadi."
    if error.status is not None and error.status >= 500:
        return "Arena serverida vaqtinchalik xatolik. Keyinroq qayta urinib ko‘ring."
    return "Arena qarorini qo‘llab bo‘lmadi. Match holatini tekshiring."


async def apply_arena_decision(
    request: ArenaModerationRequest,
    *,
    admin_telegram_id: int,
):
    async with _guard:
        if request.match_id in _in_flight:
            raise ArenaModerationInProgressError(
                "Arena moderation is already in progress"
            )
        _in_flight.add(request.match_id)

    try:
        return await resolve_match(
            match_id=request.match_id,
            admin_telegram_id=admin_telegram_id,
            winner_telegram_id=request.winner_telegram_id,
            decision=request.decision.value,
            admin_comment="Admin moderation qarori",
        )
    finally:
        async with _guard:
            _in_flight.discard(request.match_id)
