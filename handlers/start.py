import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from services.api import register_internal_user

router = Router()
logger = logging.getLogger(__name__)


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Hamyon"),
                KeyboardButton(text="🛒 Coin sotib olish"),
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
    try:
        result = await register_internal_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    except Exception:
        logger.warning("Internal user registration is unavailable")
        await message.answer(
            "⚠️ Profilingizni sinxronlash vaqtincha amalga oshmadi. "
            "Hamyon uchun keyinroq qayta urinib ko‘ring."
        )
    else:
        if not result.get("success"):
            status_code = result.get("status_code")
            if status_code == 403:
                logger.warning("Internal API key is invalid or not configured")
            else:
                logger.warning("Internal user registration failed (status=%s)", status_code)
            await message.answer(
                "⚠️ Profilingizni sinxronlash vaqtincha amalga oshmadi. "
                "Hamyon uchun keyinroq qayta urinib ko‘ring."
            )

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "LEVEL_GROUP ga xush kelibsiz! 🚀\n\n"
        "Kerakli bo‘limni tanlang.",
        reply_markup=main_keyboard(),
    )
