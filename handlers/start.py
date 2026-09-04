from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove, WebAppInfo

from config import MINIAPP_URL
from services.api import get_subscription_channels, register_internal_user
from services.referral import referral_code_from_start
from handlers.arena_relay import arena_token_from_start, send_match_context

router = Router()


class SubscriptionConfigUnavailable(RuntimeError):
    pass


async def missing_channels(
    bot: Bot, user_id: int, channels: list[dict] | None = None
) -> list[dict]:
    if channels is None:
        try:
            channels = await get_subscription_channels()
        except Exception as error:
            raise SubscriptionConfigUnavailable from error
    missing = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel["chat_id"], user_id)
            if (
                member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
                or (
                    member.status == ChatMemberStatus.RESTRICTED
                    and not getattr(member, "is_member", False)
                )
            ):
                missing.append(channel)
        except Exception:
            # Fail closed: never bypass a required subscription when Telegram
            # cannot verify membership (for example, bot lost channel access).
            missing.append(channel)
    return missing


def subscription_keyboard(
    channels: list[dict], arena_token: str | None = None
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"➕ {channel['title']}", url=channel["url"])]
        for channel in channels
    ]
    callback_data = "check_required_channels"
    if arena_token:
        callback_data = f"{callback_data}:arena_{arena_token}"
    rows.append([InlineKeyboardButton(
        text="✅ Tekshirish", callback_data=callback_data
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def miniapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 LEVEL_GROUP’ni ochish",
                    web_app=WebAppInfo(url=MINIAPP_URL),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛍 Magazin",
                    callback_data="shop:open",
                )
            ],
        ]
    )


async def send_subscription_gate(
    message: Message, bot: Bot, arena_token: str | None = None
) -> bool:
    try:
        missing = await missing_channels(bot, message.from_user.id)
    except SubscriptionConfigUnavailable:
        await message.answer(
            "⚠️ Majburiy obunani tekshirish xizmati vaqtincha ishlamayapti.\n\n"
            "Birozdan keyin «🔄 Qayta tekshirish» tugmasini bosing.",
            reply_markup=subscription_keyboard([], arena_token),
        )
        return True
    if not missing:
        return False
    await message.answer(
        "🔒 LEVEL_GROUP’dan foydalanish uchun quyidagi kanallarga obuna bo‘ling.\n\n"
        "Obuna bo‘lgach, «✅ Tekshirish» tugmasini bosing.",
        reply_markup=subscription_keyboard(missing, arena_token),
    )
    return True


@router.message(CommandStart())
async def start_command(message: Message, bot: Bot):
    arena_token = arena_token_from_start(message.text)
    referral_code = None if arena_token else referral_code_from_start(message.text)
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

    if await send_subscription_gate(message, bot, arena_token):
        return

    if arena_token:
        await send_match_context(message, arena_token)
        return

    if MINIAPP_URL:
        await message.answer(
            "LEVEL_GROUP MiniApp’ni ochish uchun quyidagi tugmani bosing.",
            reply_markup=miniapp_keyboard(),
        )


@router.callback_query(F.data.startswith("check_required_channels"))
async def check_required_channels(callback: CallbackQuery, bot: Bot):
    payload = (callback.data or "").partition(":")[2]
    arena_token = arena_token_from_start(
        f"/start {payload}"
    ) if payload else None
    try:
        missing = await missing_channels(bot, callback.from_user.id)
    except SubscriptionConfigUnavailable:
        await callback.answer(
            "Tekshiruv xizmati vaqtincha ishlamayapti. Qayta urinib ko‘ring.",
            show_alert=True,
        )
        return
    if missing:
        await callback.answer("❌ Hali barcha kanallarga obuna bo‘lmagansiz.", show_alert=True)
        await callback.message.edit_reply_markup(
            reply_markup=subscription_keyboard(missing, arena_token)
        )
        return

    await callback.answer("✅ Obuna tasdiqlandi!")
    if arena_token:
        await callback.message.edit_text("✅ Obuna tasdiqlandi.")
        await send_match_context(
            callback.message,
            arena_token,
            telegram_id=callback.from_user.id,
        )
        return
    if MINIAPP_URL:
        await callback.message.edit_text(
            "✅ Barcha kanallarga obuna tasdiqlandi.\n\nLEVEL_GROUP’ni ochishingiz mumkin.",
            reply_markup=miniapp_keyboard(),
        )
    else:
        await callback.message.edit_text("✅ Barcha kanallarga obuna tasdiqlandi.")
