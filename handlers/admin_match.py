from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_CHAT_ID, MATCH_RESULTS_CHANNEL_ID
from services.match_api import get_match, resolve_match, cancel_match


router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID


def admin_match_keyboard(match: dict):
    match_id = match["id"]
    creator_id = match["creator_telegram_id"]
    opponent_id = match["opponent_telegram_id"]

    buttons = []

    if creator_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏆 Yaratuvchini g‘olib qilish",
                    callback_data=f"admin_match_win:{match_id}:{creator_id}",
                )
            ]
        )

    if opponent_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏆 Raqibni g‘olib qilish",
                    callback_data=f"admin_match_win:{match_id}:{opponent_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Matchni bekor qilish",
                callback_data=f"admin_match_cancel:{match_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_admin_match(match: dict) -> str:
    return (
        "🎮 <b>1vs1 Arena Admin</b>\n\n"
        f"🆔 Match ID: <code>{match['id']}</code>\n"
        f"👤 Yaratuvchi: <code>{match['creator_telegram_id']}</code>\n"
        f"👥 Raqib: <code>{match.get('opponent_telegram_id')}</code>\n"
        f"💰 Tikilgan EFC: <b>{match['efc_amount']}</b>\n"
        f"🏆 Mukofot: <b>{match['winner_reward']}</b>\n"
        f"📌 Status: <b>{match['status']}</b>\n"
        f"🔐 Room Code: <code>{match.get('room_code') or 'yo‘q'}</code>\n\n"
        f"📸 Yaratuvchi screenshot: <code>{match.get('creator_result_screenshot') or 'yo‘q'}</code>\n"
        f"📸 Raqib screenshot: <code>{match.get('opponent_result_screenshot') or 'yo‘q'}</code>"
    )


def format_result_channel(match: dict) -> str:
    return (
        "🏁 <b>1vs1 Arena natijasi</b>\n\n"
        f"🆔 Match ID: <code>{match['id']}</code>\n"
        f"👤 Player 1: <code>{match['creator_telegram_id']}</code>\n"
        f"👥 Player 2: <code>{match['opponent_telegram_id']}</code>\n"
        f"🏆 G‘olib: <code>{match['winner_telegram_id']}</code>\n"
        f"❌ Mag‘lub: <code>{match['loser_telegram_id']}</code>\n"
        f"💰 Mukofot: <b>{match['winner_reward']} EFC</b>\n"
        f"💸 Komissiya: <b>{match['commission_amount']} EFC</b>\n"
        f"📌 Natija turi: <b>{match['result_type']}</b>"
    )


@router.message(F.text.startswith("/admin_match"))
async def admin_match_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "ℹ️ Foydalanish:\n"
            "<code>/admin_match MATCH_ID</code>\n\n"
            "Masalan:\n"
            "<code>/admin_match 12</code>"
        )
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Match ID raqam bo‘lishi kerak.")
        return

    try:
        match = await get_match(match_id)
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return

    await message.answer(
        format_admin_match(match),
        reply_markup=admin_match_keyboard(match),
    )


@router.callback_query(F.data.startswith("admin_match_win:"))
async def admin_match_win(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    _, match_id, winner_id = callback.data.split(":")
    match_id = int(match_id)
    winner_id = int(winner_id)

    try:
        match = await resolve_match(
            match_id=match_id,
            admin_telegram_id=callback.from_user.id,
            winner_telegram_id=winner_id,
            admin_comment="Admin tomonidan tasdiqlandi",
        )
    except ValueError as error:
        await callback.message.edit_text(f"❌ {error}")
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Match yakunlandi!\n\n"
        f"{format_admin_match(match)}"
    )

    for user_id in [match["creator_telegram_id"], match["opponent_telegram_id"]]:
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=(
                    "🏁 <b>1vs1 Arena match yakunlandi!</b>\n\n"
                    f"🆔 Match ID: <code>{match['id']}</code>\n"
                    f"🏆 G‘olib: <code>{match['winner_telegram_id']}</code>\n"
                    f"💰 Mukofot: <b>{match['winner_reward']} EFC</b>"
                ),
            )
        except Exception:
            pass

    if MATCH_RESULTS_CHANNEL_ID:
        try:
            await callback.bot.send_message(
                chat_id=MATCH_RESULTS_CHANNEL_ID,
                text=format_result_channel(match),
            )
        except Exception:
            pass

    await callback.answer()


@router.callback_query(F.data.startswith("admin_match_cancel:"))
async def admin_match_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    match_id = int(callback.data.split(":")[1])

    try:
        match = await cancel_match(
            match_id=match_id,
            admin_telegram_id=callback.from_user.id,
            cancel_reason="Admin tomonidan bekor qilindi",
        )
    except ValueError as error:
        await callback.message.edit_text(f"❌ {error}")
        await callback.answer()
        return

    await callback.message.edit_text(
        "❌ Match bekor qilindi!\n\n"
        f"{format_admin_match(match)}"
    )

    for user_id in [match["creator_telegram_id"], match["opponent_telegram_id"]]:
        if user_id:
            try:
                await callback.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "❌ <b>1vs1 Arena match bekor qilindi.</b>\n\n"
                        f"🆔 Match ID: <code>{match['id']}</code>\n"
                        "Locked EFC balansga qaytarildi."
                    ),
                )
            except Exception:
                pass

    await callback.answer()
