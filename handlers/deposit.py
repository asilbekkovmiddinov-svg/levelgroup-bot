from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from services.api import create_deposit

router = Router()

MIN_DEPOSIT_AMOUNT = 15000


class DepositState(StatesGroup):
    amount = State()


@router.callback_query(F.data == "deposit_start")
async def deposit_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DepositState.amount)

    await callback.message.answer(
        "➕ UZS to‘ldirish\n\n"
        "To‘ldirmoqchi bo‘lgan summani kiriting.\n"
        f"Minimal summa: {MIN_DEPOSIT_AMOUNT:,} so‘m\n\n"
        "Masalan: 50000"
    )

    await callback.answer()


@router.message(DepositState.amount)
async def deposit_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting. Masalan: 50000")
        return

    amount = int(message.text)

    if amount < MIN_DEPOSIT_AMOUNT:
        await message.answer(
            f"❌ Minimal to‘ldirish summasi {MIN_DEPOSIT_AMOUNT:,} so‘m.\n\n"
            f"Iltimos, {MIN_DEPOSIT_AMOUNT:,} yoki undan yuqori summa kiriting."
        )
        return

    result = await create_deposit(
        telegram_id=message.from_user.id,
        amount=amount
    )

    await state.clear()

    if result.get("message") == "Deposit request created":
        order_id = (
            result.get("id")
            or result.get("deposit_id")
            or result.get("order_id")
            or "-"
        )

        status = result.get("status", "PENDING")

        await message.answer(
            "✅ To‘ldirish so‘rovi yaratildi!\n\n"
            f"🆔 Buyurtma: #{order_id}\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"📌 Status: {status}\n\n"
            "Admin tasdiqlagandan so‘ng balansingizga tushadi."
        )
        return

    await message.answer("❌ So‘rov yaratishda xatolik yuz berdi.")
