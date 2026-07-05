from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import NEW_ORDERS_CHANNEL_ID
from services.api import create_withdraw

router = Router()

MIN_WITHDRAW_AMOUNT = 15000


class WithdrawState(StatesGroup):
    card = State()
    amount = State()


@router.callback_query(F.data == "withdraw_start")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(WithdrawState.card)

    await callback.message.answer(
        "💸 UZS yechish\n\n"
        "Pul yuboriladigan karta raqamini kiriting.\n\n"
        "Masalan:\n"
        "8600 0000 0000 0000"
    )

    await callback.answer()


@router.message(WithdrawState.card)
async def withdraw_card(message: Message, state: FSMContext):
    card = message.text.replace(" ", "")

    if not card.isdigit():
        await message.answer(
            "❌ Karta raqam faqat raqamlardan iborat bo‘lishi kerak."
        )
        return

    if len(card) != 16:
        await message.answer(
            "❌ Karta raqam 16 ta raqamdan iborat bo‘lishi kerak."
        )
        return

    await state.update_data(card=card)
    await state.set_state(WithdrawState.amount)

    await message.answer(
        "💵 Yechib olmoqchi bo‘lgan summani kiriting.\n\n"
        f"Minimal summa: {MIN_WITHDRAW_AMOUNT:,} so‘m\n\n"
        "Masalan: 50000"
    )


@router.message(WithdrawState.amount)
async def withdraw_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting. Masalan: 50000")
        return

    amount = int(message.text)

    if amount < MIN_WITHDRAW_AMOUNT:
        await message.answer(
            f"❌ Minimal yechish summasi {MIN_WITHDRAW_AMOUNT:,} so‘m.\n\n"
            f"Iltimos, {MIN_WITHDRAW_AMOUNT:,} yoki undan yuqori summa kiriting."
        )
        return
        data = await state.get_data()
    card = data["card"]

    result = await create_withdraw(
        telegram_id=message.from_user.id,
        amount=amount,
    )

    if result.get("message") == "Balans yetarli emas":
        await message.answer(
            "❌ Balansingiz yetarli emas.\n\n"
            f"💵 So‘ralgan summa: {amount:,} so‘m"
        )
        await state.clear()
        return

    if "withdraw_id" not in result:
        await message.answer(
            "❌ Xatolik yuz berdi. Qayta urinib ko‘ring."
        )
        await state.clear()
        return

    withdraw_id = result["withdraw_id"]

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else message.from_user.first_name
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"approve_withdraw_{withdraw_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"reject_withdraw_{withdraw_id}",
                ),
            ]
        ]
    )

    await message.bot.send_message(
        chat_id=NEW_ORDERS_CHANNEL_ID,
        text=(
            "💸 YANGI WITHDRAW\n\n"
            f"🆔 Buyurtma: #{withdraw_id}\n\n"
            f"👤 Mijoz: {username}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n\n"
            "🎮 Xizmat: UZS yechish\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"💳 Karta: {card}\n\n"
            "⏳ Muddat: 24 soatgacha\n"
            "📌 Status: PENDING\n\n"
            "👇 Admin tasdiqlashi yoki rad etishi kerak."
        ),
        reply_markup=keyboard,
    )

    await state.clear()

    await message.answer(
        "✅ Pul yechish so‘rovingiz qabul qilindi!\n\n"
        f"🆔 Buyurtma: #{withdraw_id}\n"
        f"💵 Summa: {amount:,} so‘m\n"
        f"💳 Karta: {card}\n\n"
        "⏳ To‘lov 24 soat ichida kartangizga yuboriladi."
    )
