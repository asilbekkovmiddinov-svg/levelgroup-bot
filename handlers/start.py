from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from services.api import register_internal_user
from services.referral import referral_code_from_start

router = Router()


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Hamyon"),
            ],
            [
                KeyboardButton(text="🤝 P2P Market"),
                KeyboardButton(text="🎰 Baraban"),
            ],
            [
                KeyboardButton(text="👤 Profil"),
                KeyboardButton(text="⚙️ Sozlamalar"),
            ],
        ],
        resize_keyboard=True,
    )


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
        reply_markup=main_keyboard(),
    )
