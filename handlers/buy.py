from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🛒 Coin sotib olish")
async def buy_coins(message: Message):
    await message.answer(
        "🛒 Coin sotib olish\n\n"
        "Hozircha bu bo'lim ishlab chiqilmoqda.\n"
        "Tez orada UZS orqali EFC sotib olishingiz mumkin bo'ladi. 🚀"
    )
