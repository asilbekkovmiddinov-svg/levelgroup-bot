from html import escape

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ARENA_ADMIN_CHANNEL_ID
from services.arena_v5_api import (
    active_match,
    complete_submission,
    fail_submission,
    prepare_submission,
    validate_relay,
)


router = Router()


def arena_token_from_start(text: str | None) -> str | None:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) != 2 or not parts[1].startswith("arena_"):
        return None
    token = parts[1].removeprefix("arena_").strip()
    return token if 16 <= len(token) <= 64 else None


def _match_text(match: dict) -> str:
    player_a = match["player_a"]
    player_b = match["player_b"]
    return (
        f"⚔️ <b>№{match['id']} MATCH</b>\n\n"
        f"🎮 <b>{escape(player_a['efootball_username'])}</b>\n"
        "🆚\n"
        f"🎮 <b>{escape(player_b['efootball_username'])}</b>\n\n"
        "Xona kodi va match haqidagi xabarlarni shu yerga yozing. "
        "Bot xabarni faqat raqibingizga yuboradi.\n\n"
        "Match tugagach natija screenshotini rasm sifatida yuboring."
    )


async def send_match_context(
    message: Message, token: str, *, telegram_id: int | None = None
) -> bool:
    try:
        data = await validate_relay(
            telegram_id or message.from_user.id, token
        )
    except Exception:
        await message.answer(
            "❌ Match havolasi noto‘g‘ri, sizga tegishli emas yoki match yakunlangan."
        )
        return False
    await message.answer(_match_text(data["match"]))
    return True


def _sender_name(data: dict, sender_id: int) -> str:
    match = data["match"]
    player = (
        match["player_a"]
        if match["player_a"]["telegram_id"] == sender_id
        else match["player_b"]
    )
    return player["efootball_username"]


async def _relay_target(message: Message) -> tuple[dict, int] | None:
    try:
        data = await active_match(message.from_user.id)
    except Exception:
        return None
    if not data.get("relay_allowed") or not data.get("opponent_telegram_id"):
        return None
    return data, data["opponent_telegram_id"]


@router.message(F.chat.type == "private", F.text.regexp(r"^(?!/).+"))
async def relay_text(message: Message):
    target = await _relay_target(message)
    if target is None:
        return
    data, opponent_id = target
    sender = escape(_sender_name(data, message.from_user.id))
    text = escape(message.text or "")
    try:
        await message.bot.send_message(
            opponent_id,
            f"⚔️ <b>№{data['match']['id']} MATCH</b>\n"
            f"🎮 <b>{sender}:</b>\n\n{text}",
        )
        await message.answer("✅ Xabar raqibga yuborildi.")
    except Exception:
        await message.answer(
            "❌ Xabar raqibga yetkazilmadi. Raqib avval botda /start bosishi kerak."
        )


@router.message(
    F.chat.type == "private",
    F.photo,
)
async def submit_result_screenshot(message: Message):
    if not ARENA_ADMIN_CHANNEL_ID:
        await message.answer("❌ Arena natijalar kanali sozlanmagan.")
        return
    photo = message.photo[-1]
    try:
        prepared = await prepare_submission(
            message.from_user.id, photo.file_id, message.message_id
        )
    except Exception:
        return
    if not prepared.get("should_deliver"):
        await message.answer("✅ Bu screenshot avval yuborilgan.")
        return

    match = prepared["match"]
    player_a = match["player_a"]
    player_b = match["player_b"]
    sender = prepared["submitted_by"]

    def telegram_name(player: dict) -> str:
        username = player.get("telegram_username")
        return f"@{escape(username)}" if username else "username yo‘q"

    caption = (
        f"⚔️ <b>ARENA — №{match['id']} MATCH</b>\n\n"
        "<b>Player A:</b>\n"
        f"🎮 {escape(player_a['efootball_username'])}\n"
        f"📱 {telegram_name(player_a)}\n\n"
        "<b>VS</b>\n\n"
        "<b>Player B:</b>\n"
        f"🎮 {escape(player_b['efootball_username'])}\n"
        f"📱 {telegram_name(player_b)}\n\n"
        "📸 <b>Match natijasi</b>\n\n"
        f"Yubordi: {telegram_name(sender)}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="⚽ Natijani yozish",
            callback_data=f"arv4:m:start:{match['id']}",
        ),
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data=f"arv4:m:cancel:{match['id']}",
        ),
    ]])
    try:
        copied = await message.bot.copy_message(
            chat_id=ARENA_ADMIN_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            caption=caption,
            reply_markup=keyboard,
        )
        await complete_submission(
            prepared["submission_id"], copied.message_id
        )
    except Exception as error:
        try:
            await fail_submission(
                prepared["submission_id"], type(error).__name__
            )
        except Exception:
            pass
        await message.answer(
            "❌ Screenshot natijalar kanaliga yuborilmadi. Qayta urinib ko‘ring."
        )
        return
    await message.answer(
        "✅ Screenshot adminga yuborildi. Natija tasdiqlanishini kuting."
    )


@router.message(
    F.chat.type == "private",
    F.video | F.document | F.animation | F.voice | F.audio,
)
async def relay_media(message: Message):
    target = await _relay_target(message)
    if target is None:
        return
    data, opponent_id = target
    sender = escape(_sender_name(data, message.from_user.id))
    try:
        await message.bot.send_message(
            opponent_id,
            f"⚔️ <b>№{data['match']['id']} MATCH</b>\n"
            f"🎮 <b>{sender}</b> media yubordi:",
        )
        await message.bot.copy_message(
            chat_id=opponent_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await message.answer("✅ Media raqibga yuborildi.")
    except Exception:
        await message.answer("❌ Media raqibga yetkazilmadi.")
