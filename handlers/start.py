from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
import aiohttp

from config import BACKEND_URL

router = Router()


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
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(
                f"{BACKEND_URL}/user/register",
                json={
                    "telegram_id": message.from_user.id,
                    "first_name": message.from_user.first_name,
                    "username": message.from_user.username or "",
                    "language": "uz",
                },
            )
        except Exception as e:
            print(e)

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "LEVEL_GROUP ga xush kelibsiz! 🚀\n\n"
        "Kerakli bo‘limni tanlang.",
        reply_markup=main_keyboard(),
    )
