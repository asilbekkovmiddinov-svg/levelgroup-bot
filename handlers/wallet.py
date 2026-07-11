from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from services.api import get_wallet

router = Router()


def format_efc(value):
    try:
        return f"{float(value):,.2f} EFC"
    except Exception:
        return "0.00 EFC"


def format_uzs(value):
    try:
        return f"{float(value):,.2f} so'm"
    except Exception:
        return "0.00 so'm"


@router.message(F.text == "💰 Hamyon")
async def wallet(message: Message):
    data = await get_wallet(message.from_user.id)

    if not data or data.get("success") is False:
        error_text = (data or {}).get("message", "Hamyon topilmadi.")
        await message.answer(
            f"❌ {error_text}\n\n"
            "Iltimos, keyinroq qayta urinib ko‘ring."
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

        f"🪙 EFC: <b>{format_efc(efc)}</b>\n"
        f"🔒 Band EFC: <b>{format_efc(locked_efc)}</b>\n\n"

        f"💵 UZS: <b>{format_uzs(uzs)}</b>\n"
        f"🔒 Band UZS: <b>{format_uzs(locked_uzs)}</b>\n\n"

        "👇 Quyidagi amallardan birini tanlang:",
        reply_markup=keyboard,
    )
