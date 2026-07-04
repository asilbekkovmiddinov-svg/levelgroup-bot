from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text == "💰 Hamyon")
async def wallet(message: Message):
    await message.answer(
        "💰 Sizning hamyoningiz\n\n"
        "🪙 EFC: 0\n"
        "💵 UZS: 0 so'm"
    )
