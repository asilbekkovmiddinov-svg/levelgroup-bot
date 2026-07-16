from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import NEW_ORDERS_CHANNEL_ID
from services.api import create_deposit

router = Router()

MIN_DEPOSIT_AMOUNT = 15000


class DepositState(StatesGroup):
    amount = State()
    receipt = State()


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

    await state.update_data(amount=amount)
    await state.set_state(DepositState.receipt)

    await message.answer(
        "💳 To‘lov rekvizitlari\n\n"
        "🏦 Bank: HUMO / Uzcard\n"
        "💳 Karta: 0000 0000 0000 0000\n"
        "👤 Qabul qiluvchi: LEVEL GROUP\n\n"
        f"💵 Summa: {amount:,} so‘m\n\n"
        "✅ To‘lov qilganingizdan keyin chek rasmini yuboring."
    )
@router.message(DepositState.receipt, F.photo)
async def deposit_receipt(message: Message, state: FSMContext):
    data = await state.get_data()

    amount = data["amount"]
    receipt_photo = message.photo[-1].file_id

    result = await create_deposit(
        telegram_id=message.from_user.id,
        amount=amount,
        idempotency_key=f"bot-deposit:{message.chat.id}:{message.message_id}",
    )

    if result.get("message") != "Deposit request created":
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        await state.clear()
        return

    order_id = (
        result.get("id")
        or result.get("deposit_id")
        or result.get("order_id")
        or "-"
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else message.from_user.first_name
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🙋 Qabul qilish",
                    callback_data=f"claim_deposit_{order_id}"
                )
            ]
        ]
    )

    await message.bot.send_photo(
        chat_id=NEW_ORDERS_CHANNEL_ID,
        photo=receipt_photo,
        caption=(
            "🆕 YANGI DEPOZIT\n\n"
            f"🆔 Buyurtma: #{order_id}\n\n"
            f"👤 Mijoz: {username}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n\n"
            "🎮 Xizmat: UZS to'ldirish\n"
            f"💵 Summa: {amount:,} so'm\n\n"
            "📌 Status: PENDING\n\n"
            "👇 Adminlardan biri qabul qilsin."
        ),
        reply_markup=keyboard
    )

    await state.clear()

    await message.answer(
        "✅ Chek qabul qilindi!\n\n"
        f"🆔 Buyurtma: #{order_id}\n"
        f"💵 Summa: {amount:,} so'm\n\n"
        "⏳ Admin tekshirayotganidan so'ng balansingiz to'ldiriladi."
    )


@router.message(DepositState.receipt)
async def receipt_not_photo(message: Message):
    await message.answer(
        "❌ Iltimos, chekni rasm sifatida yuboring."
    )
