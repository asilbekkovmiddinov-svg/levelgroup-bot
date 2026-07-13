from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, MATCH_RESULTS_CHANNEL_ID
from services.arena_moderation import (
    ArenaDecision,
    ArenaModerationRequest,
    apply_arena_decision,
    moderation_error_message,
)
from services.arena_notifications import ArenaNotification, send_arena_notification


router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID


def _value(value) -> str:
    return escape(str(value), quote=True)


def admin_match_keyboard(match: dict) -> InlineKeyboardMarkup:
    match_id = int(match["id"])
    creator_id = int(match["creator_telegram_id"])
    opponent_id = int(match["opponent_telegram_id"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏆 Player 1 Win",
                    callback_data=f"arena_decision:{match_id}:PLAYER_1_WIN:{creator_id}",
                ),
                InlineKeyboardButton(
                    text="🏆 Player 2 Win",
                    callback_data=f"arena_decision:{match_id}:PLAYER_2_WIN:{opponent_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Technical Win",
                    callback_data=f"arena_decision:{match_id}:TECHNICAL_WIN",
                ),
                InlineKeyboardButton(
                    text="💰 Refund",
                    callback_data=f"arena_decision:{match_id}:REFUND",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data=f"arena_decision:{match_id}:CANCEL",
                )
            ],
        ]
    )


def format_admin_match(match: dict) -> str:
    return (
        "🎮 <b>1vs1 Arena Admin</b>\n\n"
        f"🆔 Match ID: <code>{_value(match['id'])}</code>\n"
        f"👤 Player 1: <code>{_value(match['creator_telegram_id'])}</code>\n"
        f"👥 Player 2: <code>{_value(match.get('opponent_telegram_id'))}</code>\n"
        f"💰 Tikilgan EFC: <b>{_value(match['efc_amount'])}</b>\n"
        f"🏆 Mukofot: <b>{_value(match['winner_reward'])}</b>\n"
        f"📌 Status: <b>{_value(match['status'])}</b>\n"
        f"🔐 Room Code: <code>{_value(match.get('room_code') or 'yo‘q')}</code>\n\n"
        f"📸 Player 1 screenshot: <code>{_value(match.get('creator_result_screenshot') or 'yo‘q')}</code>\n"
        f"📸 Player 2 screenshot: <code>{_value(match.get('opponent_result_screenshot') or 'yo‘q')}</code>"
    )


def format_result_channel(match: dict) -> str:
    return (
        "🏁 <b>1vs1 Arena natijasi</b>\n\n"
        f"🆔 Match ID: <code>{_value(match['id'])}</code>\n"
        f"👤 Player 1: <code>{_value(match['creator_telegram_id'])}</code>\n"
        f"👥 Player 2: <code>{_value(match['opponent_telegram_id'])}</code>\n"
        f"🏆 G‘olib: <code>{_value(match.get('winner_telegram_id') or 'yo‘q')}</code>\n"
        f"💰 Mukofot: <b>{_value(match.get('winner_reward', 0))} EFC</b>\n"
        f"💸 Komissiya: <b>{_value(match.get('commission_amount', 0))} EFC</b>\n"
        f"📌 Natija turi: <b>{_value(match.get('result_type') or 'yo‘q')}</b>"
    )


def _request_from_callback(data: str) -> ArenaModerationRequest:
    parts = data.split(":")
    if len(parts) not in {3, 4} or parts[0] != "arena_decision":
        raise ValueError("Noto‘g‘ri moderation so‘rovi.")
    decision = ArenaDecision(parts[2])
    winner_id = int(parts[3]) if len(parts) == 4 else None
    if decision in {ArenaDecision.PLAYER_1_WIN, ArenaDecision.PLAYER_2_WIN} and not winner_id:
        raise ValueError("G‘olib aniqlanmagan.")
    return ArenaModerationRequest(
        match_id=int(parts[1]), decision=decision, winner_telegram_id=winner_id
    )


def _legacy_request(data: str) -> ArenaModerationRequest:
    parts = data.split(":")
    if parts[0] == "admin_match_win" and len(parts) == 3:
        return ArenaModerationRequest(
            match_id=int(parts[1]),
            decision=ArenaDecision.PLAYER_1_WIN,
            winner_telegram_id=int(parts[2]),
        )
    if parts[0] == "admin_match_cancel" and len(parts) == 2:
        return ArenaModerationRequest(
            match_id=int(parts[1]), decision=ArenaDecision.CANCEL
        )
    raise ValueError("Noto‘g‘ri moderation so‘rovi.")


async def _notify_players(callback: CallbackQuery, match: dict, decision: ArenaDecision):
    for user_id in (match.get("creator_telegram_id"), match.get("opponent_telegram_id")):
        if not user_id:
            continue
        if decision == ArenaDecision.REFUND:
            notification = ArenaNotification.REFUNDED
            detail = "Stake balansingizga qaytarildi."
            amount = None
        elif decision == ArenaDecision.CANCEL:
            notification = ArenaNotification.CANCELLED
            detail = "Match admin tomonidan bekor qilindi."
            amount = None
        elif user_id == match.get("winner_telegram_id"):
            notification = ArenaNotification.WINNER
            detail = "Mukofot hisobingizga o‘tkazildi."
            amount = match.get("winner_reward")
        else:
            notification = ArenaNotification.ADMIN_REVIEW
            detail = "Match natijasi admin tomonidan yakunlandi."
            amount = None
        await send_arena_notification(
            callback.bot,
            user_id,
            notification,
            match_id=match["id"],
            detail=detail,
            amount=amount,
        )


async def _apply_callback(callback: CallbackQuery, request: ArenaModerationRequest):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return
    try:
        match = await apply_arena_decision(
            request, admin_telegram_id=callback.from_user.id
        )
    except Exception as error:
        await callback.answer(moderation_error_message(error), show_alert=True)
        return

    await callback.message.edit_text(
        "✅ <b>Decision applied</b>\n\n" + format_admin_match(match),
        reply_markup=None,
    )
    await _notify_players(callback, match, request.decision)
    if MATCH_RESULTS_CHANNEL_ID:
        try:
            await callback.bot.send_message(
                chat_id=MATCH_RESULTS_CHANNEL_ID,
                text=format_result_channel(match),
            )
        except Exception:
            pass
    await callback.answer("Qaror muvaffaqiyatli qo‘llandi.")


@router.message(F.text.startswith("/admin_match"))
async def admin_match_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return
    await message.answer(
        "ℹ️ Arena match tafsilotlari authsiz user endpointdan olinmaydi.\n\n"
        "Admin review xabaridagi moderatsiya tugmalaridan foydalaning."
    )


@router.callback_query(F.data.startswith("arena_decision:"))
async def arena_match_decision(callback: CallbackQuery):
    try:
        request = _request_from_callback(callback.data or "")
    except (ValueError, TypeError):
        await callback.answer("Noto‘g‘ri moderation so‘rovi.", show_alert=True)
        return
    await _apply_callback(callback, request)


@router.callback_query(F.data.startswith("admin_match_win:"))
@router.callback_query(F.data.startswith("admin_match_cancel:"))
async def legacy_admin_match_decision(callback: CallbackQuery):
    try:
        request = _legacy_request(callback.data or "")
    except (ValueError, TypeError):
        await callback.answer("Noto‘g‘ri moderation so‘rovi.", show_alert=True)
        return
    await _apply_callback(callback, request)
