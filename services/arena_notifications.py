import logging
from enum import StrEnum
from html import escape
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from services.arena_links import ArenaMiniAppConfigError, build_arena_miniapp_url


logger = logging.getLogger(__name__)


class ArenaNotification(StrEnum):
    MATCH_CREATED = "match_created"
    OPPONENT_FOUND = "opponent_found"
    FIVE_MINUTES_LEFT = "five_minutes_left"
    READY_REQUIRED = "ready_required"
    READY_EXPIRED = "ready_expired"
    TECHNICAL_REVIEW = "technical_review"
    ROOM_CODE_READY = "room_code_ready"
    SCREENSHOT_REQUIRED = "screenshot_required"
    VIDEO_REQUIRED = "video_required"
    EVIDENCE_ACCEPTED = "evidence_accepted"
    ADMIN_REVIEW = "admin_review"
    WINNER = "winner"
    REWARD_PAID = "reward_paid"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


_TEMPLATES = {
    ArenaNotification.MATCH_CREATED: "🎮 <b>Match yaratildi.</b>",
    ArenaNotification.OPPONENT_FOUND: "👥 <b>Raqib topildi.</b>",
    ArenaNotification.FIVE_MINUTES_LEFT: "⏳ <b>Match boshlanishiga 5 daqiqa qoldi.</b>",
    ArenaNotification.READY_REQUIRED: "✅ <b>Tayyorlikni tasdiqlash vaqti keldi.</b>",
    ArenaNotification.READY_EXPIRED: "⌛ <b>Tayyorlik muddati tugadi.</b>",
    ArenaNotification.TECHNICAL_REVIEW: "⚠️ <b>Match texnik ko‘rib chiqishga yuborildi.</b>",
    ArenaNotification.ROOM_CODE_READY: "🔐 <b>Room Code bosqichi tayyor.</b>",
    ArenaNotification.SCREENSHOT_REQUIRED: "📸 <b>Match screenshotini yuboring.</b>",
    ArenaNotification.VIDEO_REQUIRED: "🎥 <b>Match videosini yuboring.</b>",
    ArenaNotification.EVIDENCE_ACCEPTED: "✅ <b>Dalillar qabul qilindi.</b>",
    ArenaNotification.ADMIN_REVIEW: "🔎 <b>Admin matchni tekshirmoqda.</b>",
    ArenaNotification.WINNER: "🏆 <b>Siz g‘olib bo‘ldingiz!</b>",
    ArenaNotification.REWARD_PAID: "💰 <b>Mukofot hisobingizga o‘tkazildi.</b>",
    ArenaNotification.REFUNDED: "↩️ <b>Stake balansingizga qaytarildi.</b>",
    ArenaNotification.CANCELLED: "❌ <b>Match bekor qilindi.</b>",
}

_MINIAPP_ACTIONS = {
    ArenaNotification.MATCH_CREATED: "detail",
    ArenaNotification.OPPONENT_FOUND: "detail",
    ArenaNotification.FIVE_MINUTES_LEFT: "ready",
    ArenaNotification.READY_REQUIRED: "ready",
    ArenaNotification.ROOM_CODE_READY: "room-code",
    ArenaNotification.SCREENSHOT_REQUIRED: "evidence",
    ArenaNotification.VIDEO_REQUIRED: "evidence",
    ArenaNotification.EVIDENCE_ACCEPTED: "detail",
    ArenaNotification.ADMIN_REVIEW: "detail",
}


def _safe(value: Any) -> str:
    return escape(str(value), quote=True)


def format_arena_notification(
    notification: ArenaNotification,
    *,
    match_id: int | None = None,
    detail: str | None = None,
    amount: Any | None = None,
) -> str:
    lines = [_TEMPLATES[notification]]
    if match_id is not None:
        lines.extend(("", f"🆔 Match ID: <code>{_safe(match_id)}</code>"))
    if amount is not None:
        lines.append(f"💰 Summa: <b>{_safe(amount)} EFC</b>")
    if detail:
        lines.extend(("", _safe(detail)))
    return "\n".join(lines)


def arena_notification_keyboard(
    notification: ArenaNotification, *, match_id: int | None = None
) -> InlineKeyboardMarkup | None:
    if notification in {
        ArenaNotification.SCREENSHOT_REQUIRED,
        ArenaNotification.VIDEO_REQUIRED,
    } and match_id is not None:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📎 Evidence yuborish",
                        callback_data=f"arena_evidence:{match_id}",
                    )
                ]
            ]
        )
    action = _MINIAPP_ACTIONS.get(notification)
    if action is None:
        return None
    try:
        url = build_arena_miniapp_url(action=action, match_id=match_id)
    except ArenaMiniAppConfigError:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Arena MiniApp’ni ochish",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


async def send_arena_notification(
    bot,
    chat_id: int,
    notification: ArenaNotification,
    *,
    match_id: int | None = None,
    detail: str | None = None,
    amount: Any | None = None,
) -> bool:
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=format_arena_notification(
                notification,
                match_id=match_id,
                detail=detail,
                amount=amount,
            ),
            reply_markup=arena_notification_keyboard(
                notification, match_id=match_id
            ),
        )
        return True
    except Exception:
        logger.warning("Arena notification delivery failed: %s", notification.value)
        return False
