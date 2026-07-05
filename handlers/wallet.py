from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from services.api import get_wallet

router = Router()


@router.message(F.text == "💰 Hamyon")
async def wallet(message: Message):
    data = await get_wallet(message.from_user.id)

    if not data:
        await message.answer(
            "❌ Hamyon topilmadi.\n\n"
            "Iltimos, avval /start buyrug'ini bosing."
        )
        return

    efc = data.get("efc_balance", data.get("efc", 0))
    uzs = data.get("uzs_balance", data.get("uzs", 0))
    locked_efc = data.get("locked_efc", 0)
    locked_uzs = data.get("locked_uzs", 0)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ UZS to'ldirish",
                    callback_data="deposit_start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💸 Pul yechish",
                    callback_data="withdraw_start",
                )
            ],
        ]
    )

    await message.answer(
        "💰 <b>Sizning hamyoningiz</b>\n\n"
        f"🪙 EFC: <b>{efc}</b>\n"
        f"🔒 Band EFC: <b>{locked_efc}</b>\n\n"
        f"💵 UZS: <b>{uzs}</b> so'm\n"
        f"🔒 Band UZS: <b>{locked_uzs}</b> so'm\n\n"
        "👇 Quyidagi amallardan birini tanlang:",
        reply_markup=keyboard,
    )
