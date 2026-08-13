from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove, WebAppInfo

from config import MINIAPP_URL, REQUIRED_CHANNELS
from services.api import register_internal_user
from services.referral import referral_code_from_start

router = Router()


async def missing_channels(bot: Bot, user_id: int) -> list[dict]:
    missing = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel["chat_id"], user_id)
            if member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
                missing.append(channel)
        except Exception:
            # Fail closed: never bypass a required subscription when Telegram
            # cannot verify membership (for example, bot lost channel access).
            missing.append(channel)
    return missing


def subscription_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"➕ {channel['title']}", url=channel["url"])]
        for channel in channels
    ]
    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_required_channels")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def miniapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🚀 LEVEL_GROUP’ni ochish",
                web_app=WebAppInfo(url=MINIAPP_URL),
            )
        ]]
    )


async def send_subscription_gate(message: Message, bot: Bot) -> bool:
    missing = await missing_channels(bot, message.from_user.id)
    if not missing:
        return False
    await message.answer(
        "🔒 LEVEL_GROUP’dan foydalanish uchun quyidagi kanallarga obuna bo‘ling.\n\n"
        "Obuna bo‘lgach, «✅ Tekshirish» tugmasini bosing.",
        reply_markup=subscription_keyboard(missing),
    )
    return True


@router.message(CommandStart())
async def start_command(message: Message, bot: Bot):
    referral_code = referral_code_from_start(message.text)
    try:
        await register_internal_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referral_code=referral_code,
        )
    except Exception:
        pass

    await message.answer(
        "👋 Assalomu alaykum!\n\nLEVEL_GROUP ga xush kelibsiz! 🚀",
        reply_markup=ReplyKeyboardRemove(),
    )

    if await send_subscription_gate(message, bot):
        return

    if MINIAPP_URL:
        await message.answer(
            "LEVEL_GROUP MiniApp’ni ochish uchun quyidagi tugmani bosing.",
            reply_markup=miniapp_keyboard(),
        )


@router.callback_query(F.data == "check_required_channels")
async def check_required_channels(callback: CallbackQuery, bot: Bot):
    missing = await missing_channels(bot, callback.from_user.id)
    if missing:
        await callback.answer("❌ Hali barcha kanallarga obuna bo‘lmagansiz.", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=subscription_keyboard(missing))
        return

    await callback.answer("✅ Obuna tasdiqlandi!")
    if MINIAPP_URL:
        await callback.message.edit_text(
            "✅ Barcha kanallarga obuna tasdiqlandi.\n\nLEVEL_GROUP’ni ochishingiz mumkin.",
            reply_markup=miniapp_keyboard(),
        )
    else:
        await callback.message.edit_text("✅ Barcha kanallarga obuna tasdiqlandi.")
