from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from services.api import get_wallet

router = Router()


@router.message(F.text == "💰 Hamyon")
async def wallet(message: Message):
    data = await get_wallet(message.from_user.id)

    if not data:
        await message.answer("❌ Hamyon topilmadi. Avval /start bosing.")
        return

    efc = data.get("efc_balance", data.get("efc", 0))
    uzs = data.get("uzs_balance", data.get("uzs", 0))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ UZS to‘ldirish",
                    callback_data="deposit_start"
                )
            ]
        ]
    )

    await message.answer(
        "💰 Sizning hamyoningiz\n\n"
        f"🪙 EFC: {efc}\n"
        f"💵 UZS: {uzs} so'm",
        reply_markup=keyboard
    )
