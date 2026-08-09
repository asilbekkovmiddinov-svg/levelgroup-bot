from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from config import MINIAPP_URL
from services.api import register_internal_user
from services.referral import referral_code_from_start

router = Router()



@router.message(CommandStart())
async def start_command(message: Message):
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
        # Registration failure must not expose secrets or block the welcome UX.
        pass

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "LEVEL_GROUP ga xush kelibsiz! 🚀\n\n"
        "Kerakli bo‘limni tanlang.",
        reply_markup=ReplyKeyboardRemove(),
    )

    if MINIAPP_URL:
        await message.answer(
            "LEVEL_GROUP MiniApp’ni ochish uchun quyidagi tugmani bosing.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🚀 LEVEL_GROUP’ni ochish",
                        web_app=WebAppInfo(url=MINIAPP_URL),
                    )
                ]]
            ),
        )
