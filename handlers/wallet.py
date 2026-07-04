from aiogram import Router, F
from aiogram.types import Message

from services.api import get_wallet

router = Router()


@router.message(F.text == "💰 Hamyon")
async def wallet(message: Message):
    data = await get_wallet(message.from_user.id)

    if not data:
        await message.answer("❌ Hamyon topilmadi. Avval /start bosing.")
        return

    await message.answer(
        "💰 Sizning hamyoningiz\n\n"
        f"🪙 EFC: {data['efc_balance']}\n"
        f"💵 UZS: {data['uzs_balance']} so'm"
    )
