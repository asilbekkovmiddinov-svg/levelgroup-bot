from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

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
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "LEVEL_GROUP ga xush kelibsiz! 🚀\n\n"
        "Kerakli bo‘limni tanlang.",
        reply_markup=main_keyboard(),
    )
