from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_USER_IDS, MINIAPP_URL

router = Router()


@router.message(Command("gamepost"))
async def publish_game_post(message: Message) -> None:
    """Publish a channel post with a button that opens LEVEL_GROUP.

    Usage: /gamepost @channel_username
    The bot must be an administrator of the target channel with permission
    to post messages. Pin the resulting post in Telegram to surface its
    action in the pinned-message area.
    """
    if not message.from_user or message.from_user.id not in ADMIN_USER_IDS:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].strip():
        await message.answer("Foydalanish: <code>/gamepost @kanal_username</code>")
        return

    if not MINIAPP_URL:
        await message.answer("❌ MINIAPP_URL sozlanmagan.")
        return

    target_chat = parts[1].strip()
    text = (
        "🎮 <b>LEVEL_GROUP</b>\n\n"
        "eFootball Arena, Penalty Duel va boshqa imkoniyatlardan foydalaning.\n\n"
        "👇 O‘yinni boshlash uchun tugmani bosing."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 O‘ynash", url=MINIAPP_URL)]
        ]
    )

    try:
        sent = await message.bot.send_message(
            chat_id=target_chat,
            text=text,
            reply_markup=keyboard,
        )
    except Exception as exc:
        await message.answer(
            "❌ Kanalga post yuborilmadi. Bot kanal admini va xabar yuborish "
            f"huquqiga ega ekanini tekshiring.\n<code>{type(exc).__name__}</code>"
        )
        return

    await message.answer(
        "✅ Post kanalga yuborildi.\n"
        f"Message ID: <code>{sent.message_id}</code>\n\n"
        "Endi kanalda shu postni qadalgan xabar (Pin) qiling."
    )
